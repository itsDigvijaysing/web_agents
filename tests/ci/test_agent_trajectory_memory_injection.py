"""Integration test for the Day-4 seams: Agent wiring of trajectory memory injection (read
side, _inject_trajectory_memory via _prepare_context) and recording (write side,
_maybe_record_trajectory_memory via run()'s finally).

Real Agent + real browser_session + mock LLM + pytest-httpserver, per this repo's TDD
conventions (mocks only for the LLM). The embedding API call itself is faked (EmbeddingClient.embed
monkeypatched to a fixed vector) rather than hitting a real provider - only the resolution
(env var -> provider choice) needs to be real to prove the wiring actually works end-to-end.

Critical isolation rule (confirmed footgun in tests/ci/conftest.py's setup_test_environment,
which deliberately leaves web_agent_CONFIG_DIR unset to preserve real extension caching):
every test here passes an explicit memory_dir=tmp_path, never the default path.
"""

import pytest
from pytest_httpserver import HTTPServer

from tests.ci.conftest import create_mock_llm
from web_agent.agent.service import Agent
from web_agent.llm.messages import UserMessage
from web_agent.memory.embeddings import EmbeddingClient
from web_agent.memory.store import TrajectoryStore
from web_agent.memory.views import TrajectoryRecord

FAKE_VECTOR = [1.0, 0.0, 0.0]


def _get_context_messages(agent: Agent) -> list[str]:
	msgs = agent._message_manager.state.history.context_messages
	return [m.content for m in msgs if isinstance(m, UserMessage) and isinstance(m.content, str)]


@pytest.fixture(autouse=True)
def fake_embedding_api(monkeypatch):
	"""Fake the actual network call; keep real env-var-based provider resolution."""

	async def fake_embed(self, text: str) -> list[float]:
		return FAKE_VECTOR

	monkeypatch.setattr(EmbeddingClient, 'embed', fake_embed)


def _seed_store(memory_dir, task: str, summary: str) -> None:
	store = TrajectoryStore(path=memory_dir / 'trajectories.jsonl')
	store.append(
		TrajectoryRecord(
			created_at='2026-07-13T00:00:00',
			task=task,
			success=True,
			final_result='done',
			summary=summary,
			number_of_steps=3,
			duration_seconds=2.0,
			embedding=FAKE_VECTOR,
			embedding_model='openai/text-embedding-3-small',
		)
	)


async def test_injects_matching_trajectory_at_step_zero(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	_seed_store(tmp_path, task='Buy a red umbrella', summary='Use the search bar directly.')

	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')

	agent = Agent(
		task='Buy a red umbrella online',
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=True,
		memory_dir=tmp_path,
	)
	await agent.run(max_steps=3)

	messages = _get_context_messages(agent)
	joined = '\n'.join(messages)
	assert 'RELEVANT PAST EXPERIENCE' in joined
	assert 'Use the search bar directly.' in joined


async def test_injection_fires_when_task_contains_url(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	"""Regression: a task containing a URL triggers an auto initial-navigate action, which appends
	a history item BEFORE step 0. The injection guard must not skip on that (real-scenario bug -
	the earlier guard used len(history)==0, which is false once an initial action has run)."""
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	_seed_store(tmp_path, task='Find the total on the page', summary='Read the revenue span directly.')

	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')
	url = httpserver.url_for('/')

	agent = Agent(
		task=f'Go to {url} and tell me the total',  # URL in task -> initial navigate action runs
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=True,
		memory_dir=tmp_path,
	)
	assert agent.initial_actions, 'task with a URL should have produced an initial navigate action'
	await agent.run(max_steps=3)

	assert 'RELEVANT PAST EXPERIENCE' in '\n'.join(_get_context_messages(agent))


async def test_no_injection_when_memory_disabled(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	_seed_store(tmp_path, task='Buy a red umbrella', summary='Use the search bar directly.')

	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')

	agent = Agent(
		task='Buy a red umbrella online',
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=False,  # explicit default
		memory_dir=tmp_path,
	)
	await agent.run(max_steps=3)

	assert 'RELEVANT PAST EXPERIENCE' not in '\n'.join(_get_context_messages(agent))


async def test_no_injection_when_store_is_empty(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')

	agent = Agent(
		task='Buy a red umbrella online',
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=True,
		memory_dir=tmp_path,
	)
	await agent.run(max_steps=3)

	assert 'RELEVANT PAST EXPERIENCE' not in '\n'.join(_get_context_messages(agent))


async def test_run_records_a_new_trajectory(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')

	agent = Agent(
		task='Find the weather forecast',
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=True,
		memory_dir=tmp_path,
	)
	await agent.run(max_steps=3)

	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	records = store.load_all()
	assert len(records) == 1
	assert records[0].task == 'Find the weather forecast'


async def test_no_recording_when_memory_disabled(browser_session, httpserver: HTTPServer, tmp_path, monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
	httpserver.expect_request('/').respond_with_data('<html><body>Home</body></html>', content_type='text/html')

	agent = Agent(
		task='Find the weather forecast',
		llm=create_mock_llm(actions=None),
		browser_session=browser_session,
		enable_memory=False,
		memory_dir=tmp_path,
	)
	await agent.run(max_steps=3)

	assert not (tmp_path / 'trajectories.jsonl').exists()
