from pydantic import BaseModel, ConfigDict, Field
from uuid_extensions import uuid7str


class TrajectoryRecord(BaseModel):
	"""A condensed record of one completed Agent.run(), for cross-run experience retrieval.

	Adapted from Agent-S's narrative-memory concept (gui_agents/s2/core/knowledge.py) - the
	`summary` field is the embedded text (an LLM-condensed "lesson learned"), not the raw
	step-by-step history, which is too large/noisy to embed usefully.
	"""

	model_config = ConfigDict(extra='forbid')

	id: str = Field(default_factory=uuid7str)
	created_at: str
	task: str
	success: bool | None
	final_result: str | None
	summary: str
	key_steps: list[str] = Field(default_factory=list)
	urls_visited: list[str] = Field(default_factory=list)
	errors: list[str] = Field(default_factory=list)
	number_of_steps: int
	duration_seconds: float
	embedding: list[float] | None = None
	embedding_model: str | None = None


class TrajectorySummary(BaseModel):
	"""Structured output for the LLM-based trajectory summarization step."""

	model_config = ConfigDict(extra='forbid')

	lesson: str = Field(description='1-3 sentences: what worked, or what to avoid/change next time')
	key_steps: list[str] = Field(default_factory=list, max_length=6, description='Short bullets of the major actions taken')
