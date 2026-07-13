"""Embedding client + provider resolution for trajectory memory.

Not a BaseChatModel - the LLM Protocol (web_agent/llm/base.py) has no embedding method, so this
is a small dedicated client rather than a new LLM-provider integration. Both openai and
google-genai are already core dependencies with embedding support; Groq (this project's default
LLM provider) and Anthropic have no reachable embeddings endpoint, so they're excluded here.
"""

import os
from dataclasses import dataclass
from typing import Literal, cast


@dataclass
class EmbeddingClient:
	provider: Literal['openai', 'google', 'ollama']
	model: str
	api_key: str | None = None  # not needed for ollama (local)

	@property
	def model_id(self) -> str:
		"""Uniquely identifies the embedding space - stored on each TrajectoryRecord since
		embeddings from different models/providers aren't comparable to each other."""
		return f'{self.provider}/{self.model}'

	async def embed(self, text: str) -> list[float]:
		if self.provider == 'openai':
			from openai import AsyncOpenAI

			resp = await AsyncOpenAI(api_key=self.api_key).embeddings.create(model=self.model, input=text)
			return resp.data[0].embedding
		if self.provider == 'google':
			from google import genai

			resp = await genai.Client(api_key=self.api_key).aio.models.embed_content(model=self.model, contents=text)
			assert resp.embeddings, 'Google embed_content returned no embeddings'
			return list(resp.embeddings[0].values or [])
		if self.provider == 'ollama':
			from ollama import AsyncClient

			resp = await AsyncClient().embed(model=self.model, input=text)
			assert resp.embeddings, 'Ollama embed returned no embeddings'
			return list(resp.embeddings[0])
		raise ValueError(f'Unsupported embedding provider: {self.provider}')


_DEFAULT_EMBEDDING_RESOLUTION_ORDER: tuple[tuple[str, Literal['openai', 'google'], str], ...] = (
	('OPENAI_API_KEY', 'openai', 'text-embedding-3-small'),
	('GOOGLE_API_KEY', 'google', 'text-embedding-004'),
)


def resolve_default_embedding_client() -> EmbeddingClient | None:
	"""Resolve an embedding client from whichever provider API key is present.

	Mirrors resolve_default_llm()'s priority-list idiom (web_agent/llm/models.py), but returns
	None instead of raising when nothing is configured - trajectory-memory retrieval is an
	optional enhancement, never load-bearing, so a Groq-only user degrades gracefully to
	storage-without-retrieval rather than a crash.
	"""
	explicit_provider = os.getenv('WEB_AGENT_EMBEDDING_PROVIDER')
	explicit_model = os.getenv('WEB_AGENT_EMBEDDING_MODEL')

	if explicit_provider:
		# Ollama runs locally with no API key - opt-in only via explicit provider (not auto-detected,
		# since detecting a running local server would require a network call during resolution).
		if explicit_provider == 'ollama':
			return EmbeddingClient(provider='ollama', model=explicit_model or 'nomic-embed-text', api_key=None)
		key_by_provider: dict[str, str] = {'openai': 'OPENAI_API_KEY', 'google': 'GOOGLE_API_KEY'}
		if explicit_provider not in key_by_provider:
			raise ValueError(f'Unsupported embedding provider: {explicit_provider}. Must be one of: openai, google, ollama')
		api_key = os.getenv(key_by_provider[explicit_provider])
		if not api_key:
			return None
		provider = cast('Literal["openai", "google"]', explicit_provider)
		default_model = dict((p, m) for _, p, m in _DEFAULT_EMBEDDING_RESOLUTION_ORDER)[provider]
		return EmbeddingClient(provider=provider, model=explicit_model or default_model, api_key=api_key)

	for env_var, provider, default_model in _DEFAULT_EMBEDDING_RESOLUTION_ORDER:
		api_key = os.getenv(env_var)
		if api_key:
			return EmbeddingClient(provider=provider, model=explicit_model or default_model, api_key=api_key)

	return None
