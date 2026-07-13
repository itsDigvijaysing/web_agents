"""Trajectory memory orchestrator: record a condensed "lesson" after each Agent.run(),
embed it, and retrieve relevant past lessons for future similar tasks.

Adapted from Agent-S's KnowledgeBase (gui_agents/s2/core/knowledge.py) - narrative-memory tier
only (no episodic/subtask tier, since web_agents' agent loop is flat, not hierarchical
manager/worker planning like Agent-S's).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from web_agent.llm.base import BaseChatModel
from web_agent.llm.messages import BaseMessage, UserMessage
from web_agent.memory.prompts import get_trajectory_summary_prompt
from web_agent.memory.store import TrajectoryStore
from web_agent.memory.views import TrajectoryRecord, TrajectorySummary

if TYPE_CHECKING:
	from web_agent.agent.views import AgentHistoryList

logger = logging.getLogger(__name__)


class SupportsEmbedding(Protocol):
	"""Structural type for EmbeddingClient - lets tests pass a fake without importing the real one."""

	model_id: str

	async def embed(self, text: str) -> list[float]: ...


class TrajectoryMemory:
	def __init__(
		self,
		store: TrajectoryStore,
		summary_llm: BaseChatModel,
		embedding_client: SupportsEmbedding | None,
		top_k: int = 3,
		min_score: float = 0.75,
	):
		self.store = store
		self.summary_llm = summary_llm
		self.embedding_client = embedding_client
		self.top_k = top_k
		self.min_score = min_score

	@classmethod
	def create(
		cls,
		memory_dir: str | Path,
		summary_llm: BaseChatModel,
		embedding_client: SupportsEmbedding | None,
		top_k: int = 3,
		min_score: float = 0.75,
	) -> 'TrajectoryMemory':
		store = TrajectoryStore(path=Path(memory_dir) / 'trajectories.jsonl')
		return cls(store=store, summary_llm=summary_llm, embedding_client=embedding_client, top_k=top_k, min_score=min_score)

	async def record_run(self, task: str, history: 'AgentHistoryList') -> TrajectoryRecord:
		"""Summarize a completed run and persist it. Embeds it too, if an embedding client is configured."""
		errors = [e for e in history.errors() if e]
		urls_visited = list(dict.fromkeys(u for u in history.urls() if u))  # dedup, order-preserving
		action_names = history.action_names()

		summary, key_steps = await self._summarize(
			task=task, success=history.is_successful(), final_result=history.final_result(), errors=errors, action_names=action_names
		)

		record = TrajectoryRecord(
			created_at=datetime.now(timezone.utc).isoformat(),
			task=task,
			success=history.is_successful(),
			final_result=history.final_result(),
			summary=summary,
			key_steps=key_steps,
			urls_visited=urls_visited,
			errors=errors,
			number_of_steps=history.number_of_steps(),
			duration_seconds=history.total_duration_seconds(),
		)

		if self.embedding_client is not None:
			try:
				record.embedding = await self.embedding_client.embed(f'{task}\n{summary}')
				record.embedding_model = self.embedding_client.model_id
			except Exception as e:
				logger.warning(f'Failed to embed trajectory record, storing without embedding: {e}')

		self.store.append(record)
		return record

	async def retrieve(self, task: str) -> list[tuple[TrajectoryRecord, float]]:
		"""Retrieve relevant past trajectories for a new task. Returns [] if no embedding client
		is configured (storage-only mode) rather than raising."""
		if self.embedding_client is None:
			return []
		try:
			query_embedding = await self.embedding_client.embed(task)
		except Exception as e:
			logger.warning(f'Failed to embed query for trajectory retrieval, skipping: {e}')
			return []
		return self.store.search(
			query_embedding=query_embedding,
			embedding_model=self.embedding_client.model_id,
			top_k=self.top_k,
			min_score=self.min_score,
		)

	async def _summarize(
		self, task: str, success: bool | None, final_result: str | None, errors: list[str], action_names: list[str]
	) -> tuple[str, list[str]]:
		prompt = get_trajectory_summary_prompt(
			task=task, success=success, final_result=final_result, errors=errors, action_names=action_names
		)
		messages: list[BaseMessage] = [UserMessage(content=prompt)]

		try:
			response = await self.summary_llm.ainvoke(messages, output_format=TrajectorySummary)
			parsed: TrajectorySummary = response.completion  # type: ignore[assignment]
			return parsed.lesson, parsed.key_steps
		except Exception as structured_error:
			logger.debug(f'Structured trajectory summary failed: {structured_error}, falling back to plain text')
			response = await self.summary_llm.ainvoke(messages, None)
			text = response.completion
			return (text if isinstance(text, str) else str(text)), []
