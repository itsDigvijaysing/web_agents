"""Tests for automatic default LLM resolution when Agent(llm=None).

Replaces the removed Chatwebagent cloud-proxy default: the agent should resolve
a real provider from whichever API key env var is present, prioritizing Groq
(this project's primary provider), or raise a clear error if none are set.
"""

import pytest

from web_agent.agent.service import Agent
from web_agent.llm.anthropic.chat import ChatAnthropic
from web_agent.llm.google.chat import ChatGoogle
from web_agent.llm.groq.chat import ChatGroq
from web_agent.llm.openai.chat import ChatOpenAI


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
	"""Ensure no provider API keys leak in from the real environment."""
	for key in ['GROQ_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'DEFAULT_LLM']:
		monkeypatch.delenv(key, raising=False)


def test_no_api_keys_raises_clear_error():
	with pytest.raises(ValueError, match='(?i)no llm'):
		Agent(task='Test task', llm=None)


def test_groq_api_key_resolves_to_chat_groq(monkeypatch):
	monkeypatch.setenv('GROQ_API_KEY', 'test-groq-key')
	agent = Agent(task='Test task', llm=None)
	assert isinstance(agent.llm, ChatGroq)
	assert agent.llm.model == 'openai/gpt-oss-20b'


def test_groq_takes_priority_over_openai(monkeypatch):
	monkeypatch.setenv('GROQ_API_KEY', 'test-groq-key')
	monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
	agent = Agent(task='Test task', llm=None)
	assert isinstance(agent.llm, ChatGroq)


def test_openai_api_key_resolves_to_chat_openai(monkeypatch):
	monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
	agent = Agent(task='Test task', llm=None)
	assert isinstance(agent.llm, ChatOpenAI)


def test_anthropic_api_key_resolves_to_chat_anthropic(monkeypatch):
	monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')
	agent = Agent(task='Test task', llm=None)
	assert isinstance(agent.llm, ChatAnthropic)


def test_google_api_key_resolves_to_chat_google(monkeypatch):
	monkeypatch.setenv('GOOGLE_API_KEY', 'test-google-key')
	agent = Agent(task='Test task', llm=None)
	assert isinstance(agent.llm, ChatGoogle)


def test_explicit_llm_overrides_env_resolution(monkeypatch):
	monkeypatch.setenv('GROQ_API_KEY', 'test-groq-key')
	explicit = ChatOpenAI(model='gpt-4.1-mini', api_key='explicit-key')
	agent = Agent(task='Test task', llm=explicit)
	assert agent.llm is explicit
