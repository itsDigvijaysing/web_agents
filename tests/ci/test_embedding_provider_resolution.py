"""Tests for embedding-provider auto-resolution, mirroring test_default_llm.py's shape.

Unlike resolve_default_llm() (which raises when no key is set, since an LLM is required),
resolve_default_embedding_client() returns None - trajectory-memory retrieval is an optional
enhancement, never load-bearing, so a Groq-only user degrades gracefully to storage-without-
retrieval rather than a crash.

Constructing an EmbeddingClient never touches the network - only .embed() does - so these
tests stay fast and fully offline.
"""

import pytest

from web_agent.memory.embeddings import EmbeddingClient, resolve_default_embedding_client


@pytest.fixture(autouse=True)
def clear_embedding_env(monkeypatch):
	for key in ['OPENAI_API_KEY', 'GOOGLE_API_KEY', 'WEB_AGENT_EMBEDDING_PROVIDER', 'WEB_AGENT_EMBEDDING_MODEL']:
		monkeypatch.delenv(key, raising=False)


def test_no_api_keys_returns_none():
	assert resolve_default_embedding_client() is None


def test_openai_api_key_resolves_to_openai_client(monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.provider == 'openai'
	assert client.model_id == f'openai/{client.model}'


def test_google_api_key_resolves_to_google_client(monkeypatch):
	monkeypatch.setenv('GOOGLE_API_KEY', 'test-google-key')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.provider == 'google'


def test_openai_takes_priority_over_google(monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
	monkeypatch.setenv('GOOGLE_API_KEY', 'test-google-key')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.provider == 'openai'


def test_explicit_provider_override(monkeypatch):
	monkeypatch.setenv('GOOGLE_API_KEY', 'test-google-key')
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_PROVIDER', 'google')
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_MODEL', 'custom-embedding-model')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.provider == 'google'
	assert client.model == 'custom-embedding-model'


def test_explicit_provider_override_without_matching_key_returns_none(monkeypatch):
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_PROVIDER', 'openai')
	# no OPENAI_API_KEY set
	assert resolve_default_embedding_client() is None


def test_unsupported_explicit_provider_raises(monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_PROVIDER', 'groq')
	with pytest.raises(ValueError, match='(?i)unsupported'):
		resolve_default_embedding_client()


def test_explicit_ollama_provider_needs_no_api_key(monkeypatch):
	"""Ollama runs locally with no API key - explicit selection should resolve regardless of keys."""
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_PROVIDER', 'ollama')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.provider == 'ollama'
	assert client.model == 'nomic-embed-text'  # sensible default
	assert client.model_id == 'ollama/nomic-embed-text'


def test_explicit_ollama_provider_with_custom_model(monkeypatch):
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_PROVIDER', 'ollama')
	monkeypatch.setenv('WEB_AGENT_EMBEDDING_MODEL', 'mxbai-embed-large')
	client = resolve_default_embedding_client()
	assert client is not None
	assert client.model == 'mxbai-embed-large'


def test_model_id_property_format():
	client = EmbeddingClient(provider='openai', model='text-embedding-3-small', api_key='k')
	assert client.model_id == 'openai/text-embedding-3-small'
