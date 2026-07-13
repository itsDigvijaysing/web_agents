"""Tests for LLM-based trajectory summarization + record_run(), adapted from Agent-S's
summarize_narrative (gui_agents/s2/core/knowledge.py) - a text-only reflection on the action
log producing a "lesson learned", not a visual judgment call.

Uses hand-built real AgentHistoryList/AgentHistory/ActionResult/BrowserStateHistory objects
(no mocks) plus create_mock_llm, which already supports arbitrary structured output_format.
"""

import json
from unittest.mock import AsyncMock

from web_agent.agent.views import ActionResult, AgentHistory, AgentHistoryList, AgentOutput
from web_agent.browser.views import BrowserStateHistory
from web_agent.llm import BaseChatModel
from web_agent.llm.views import ChatInvokeCompletion
from web_agent.memory.service import TrajectoryMemory
from web_agent.memory.store import TrajectoryStore
from web_agent.tools.service import Tools


def create_mock_llm(actions: list[str] | None = None) -> BaseChatModel:
	"""Local copy of conftest.py's create_mock_llm helper (no test in this repo imports it
	across test modules - each file that needs custom actions keeps its own copy)."""
	tools = Tools()
	ActionModel = tools.registry.create_action_model()
	AgentOutputWithActions = AgentOutput.type_with_custom_actions(ActionModel)

	llm = AsyncMock(spec=BaseChatModel)
	llm.model = 'mock-llm'
	llm._verified_api_keys = True
	llm.provider = 'mock'
	llm.name = 'mock-llm'
	llm.model_name = 'mock-llm'

	default_done_action = json.dumps(
		{
			'thinking': 'null',
			'evaluation_previous_goal': 'Successfully completed the task',
			'memory': 'Task completed',
			'next_goal': 'Task completed',
			'action': [{'done': {'text': 'Task completed successfully', 'success': True}}],
		}
	)

	action_index = 0

	def get_next_action() -> str:
		nonlocal action_index
		if actions is not None and action_index < len(actions):
			action = actions[action_index]
			action_index += 1
			return action
		return default_done_action

	async def mock_ainvoke(*args, **kwargs):
		output_format = args[1] if len(args) >= 2 else kwargs.get('output_format')
		action_json = get_next_action()
		if output_format is None:
			return ChatInvokeCompletion(completion=action_json, usage=None)
		if output_format == AgentOutputWithActions:
			parsed = AgentOutputWithActions.model_validate_json(action_json)
		else:
			parsed = output_format.model_validate_json(action_json)
		return ChatInvokeCompletion(completion=parsed, usage=None)

	llm.ainvoke.side_effect = mock_ainvoke
	return llm


def make_history(success: bool, extracted_content: str = 'Task finished', error: str | None = None) -> AgentHistoryList:
	state = BrowserStateHistory(url='https://example.com/result', title='Result', tabs=[], interacted_element=[])
	results = []
	if error:
		results.append(ActionResult(error=error))
	results.append(ActionResult(is_done=True, success=success, extracted_content=extracted_content))
	history_item = AgentHistory(model_output=None, result=results, state=state)
	return AgentHistoryList(history=[history_item])


def summary_json(lesson: str, key_steps: list[str] | None = None) -> str:
	return json.dumps({'lesson': lesson, 'key_steps': key_steps or []})


async def test_record_run_stores_summary_and_outcome(tmp_path):
	llm = create_mock_llm(actions=[summary_json('Use the search bar directly instead of browsing categories.')])
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	memory = TrajectoryMemory(store=store, summary_llm=llm, embedding_client=None, top_k=3, min_score=0.75)

	history = make_history(success=True, extracted_content='Found the product and added to cart')
	record = await memory.record_run(task='Buy a red umbrella', history=history)

	assert record.task == 'Buy a red umbrella'
	assert record.success is True
	assert record.summary == 'Use the search bar directly instead of browsing categories.'
	assert record.embedding is None, 'no embedding_client provided, should skip embedding gracefully'

	loaded = store.load_all()
	assert len(loaded) == 1
	assert loaded[0].id == record.id


async def test_record_run_captures_failure_outcome(tmp_path):
	llm = create_mock_llm(actions=[summary_json('The checkout button requires scrolling into view first.')])
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	memory = TrajectoryMemory(store=store, summary_llm=llm, embedding_client=None, top_k=3, min_score=0.75)

	history = make_history(success=False, extracted_content='Could not complete checkout', error='Element not clickable')
	record = await memory.record_run(task='Buy a red umbrella', history=history)

	assert record.success is False
	assert 'Element not clickable' in record.errors


async def test_record_run_embeds_when_embedding_client_provided(tmp_path):
	llm = create_mock_llm(actions=[summary_json('Worked fine.')])
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')

	class FakeEmbeddingClient:
		model_id = 'fake/fake-model'

		async def embed(self, text: str) -> list[float]:
			return [1.0, 0.0, 0.0]

	memory = TrajectoryMemory(store=store, summary_llm=llm, embedding_client=FakeEmbeddingClient(), top_k=3, min_score=0.75)

	history = make_history(success=True)
	record = await memory.record_run(task='Buy a red umbrella', history=history)

	assert record.embedding == [1.0, 0.0, 0.0]
	assert record.embedding_model == 'fake/fake-model'


async def test_retrieve_returns_empty_without_embedding_client(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	memory = TrajectoryMemory(store=store, summary_llm=create_mock_llm(), embedding_client=None, top_k=3, min_score=0.75)

	assert await memory.retrieve('Buy a red umbrella') == []


async def test_retrieve_finds_similar_past_trajectory(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')

	class FakeEmbeddingClient:
		model_id = 'fake/fake-model'

		async def embed(self, text: str) -> list[float]:
			return [1.0, 0.0, 0.0]

	embedding_client = FakeEmbeddingClient()
	memory = TrajectoryMemory(store=store, summary_llm=create_mock_llm(), embedding_client=embedding_client, top_k=3, min_score=0.5)

	llm = create_mock_llm(actions=[summary_json('Use the search bar.')])
	memory_for_recording = TrajectoryMemory(store=store, summary_llm=llm, embedding_client=embedding_client, top_k=3, min_score=0.5)
	await memory_for_recording.record_run(task='Buy a red umbrella', history=make_history(success=True))

	results = await memory.retrieve('Buy a blue umbrella')

	assert len(results) == 1
	assert results[0][0].task == 'Buy a red umbrella'


async def test_summarization_falls_back_to_plain_text_on_structured_output_failure(tmp_path):
	"""Mirrors Agent.run()'s _generate_rerun_summary fallback pattern: if structured output
	fails, fall back to a plain-text ainvoke call and wrap it into the schema manually."""
	from unittest.mock import AsyncMock

	from web_agent.llm.views import ChatInvokeCompletion

	llm = AsyncMock()
	llm.model = 'mock-llm'

	call_count = 0

	async def flaky_ainvoke(*args, **kwargs):
		nonlocal call_count
		call_count += 1
		if kwargs.get('output_format') is not None:
			raise ValueError('structured output not supported')
		return ChatInvokeCompletion(completion='Plain text lesson learned.', usage=None)

	llm.ainvoke.side_effect = flaky_ainvoke

	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	memory = TrajectoryMemory(store=store, summary_llm=llm, embedding_client=None, top_k=3, min_score=0.75)

	record = await memory.record_run(task='Buy a red umbrella', history=make_history(success=True))

	assert record.summary == 'Plain text lesson learned.'
	assert call_count == 2
