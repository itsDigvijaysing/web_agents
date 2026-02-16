import os
from typing import TYPE_CHECKING

from web_agent.logging_config import setup_logging

# Only set up logging if not in MCP mode or if explicitly requested
if os.environ.get('web_agent_SETUP_LOGGING', 'true').lower() != 'false':
	from web_agent.config import CONFIG

	# Get log file paths from config/environment
	debug_log_file = getattr(CONFIG, 'web_agent_DEBUG_LOG_FILE', None)
	info_log_file = getattr(CONFIG, 'web_agent_INFO_LOG_FILE', None)

	# Set up logging with file handlers if specified
	logger = setup_logging(debug_log_file=debug_log_file, info_log_file=info_log_file)
else:
	import logging

	logger = logging.getLogger('web_agent')

# Monkeypatch BaseSubprocessTransport.__del__ to handle closed event loops gracefully
from asyncio import base_subprocess

_original_del = base_subprocess.BaseSubprocessTransport.__del__


def _patched_del(self):
	"""Patched __del__ that handles closed event loops without throwing noisy red-herring errors like RuntimeError: Event loop is closed"""
	try:
		# Check if the event loop is closed before calling the original
		if hasattr(self, '_loop') and self._loop and self._loop.is_closed():
			# Event loop is closed, skip cleanup that requires the loop
			return
		_original_del(self)
	except RuntimeError as e:
		if 'Event loop is closed' in str(e):
			# Silently ignore this specific error
			pass
		else:
			raise


base_subprocess.BaseSubprocessTransport.__del__ = _patched_del


# Type stubs for lazy imports - fixes linter warnings
if TYPE_CHECKING:
	from web_agent.agent.prompts import SystemPrompt
	from web_agent.agent.service import Agent

	# from web_agent.agent.service import Agent
	from web_agent.agent.views import ActionModel, ActionResult, AgentHistoryList
	from web_agent.browser import BrowserProfile, BrowserSession
	from web_agent.browser import BrowserSession as Browser
	from web_agent.code_use.service import CodeAgent
	from web_agent.dom.service import DomService
	from web_agent.llm import models
	from web_agent.llm.anthropic.chat import ChatAnthropic
	from web_agent.llm.azure.chat import ChatAzureOpenAI
	from web_agent.llm.web_agent.chat import Chatwebagent
	from web_agent.llm.google.chat import ChatGoogle
	from web_agent.llm.groq.chat import ChatGroq
	from web_agent.llm.mistral.chat import ChatMistral
	from web_agent.llm.oci_raw.chat import ChatOCIRaw
	from web_agent.llm.ollama.chat import ChatOllama
	from web_agent.llm.openai.chat import ChatOpenAI
	from web_agent.llm.vercel.chat import ChatVercel
	from web_agent.sandbox import sandbox
	from web_agent.tools.service import Controller, Tools

	# Lazy imports mapping - only import when actually accessed
_LAZY_IMPORTS = {
	# Agent service (heavy due to dependencies)
	# 'Agent': ('web_agent.agent.service', 'Agent'),
	# Code-use agent (Jupyter notebook-like execution)
	'CodeAgent': ('web_agent.code_use.service', 'CodeAgent'),
	'Agent': ('web_agent.agent.service', 'Agent'),
	# System prompt (moderate weight due to agent.views imports)
	'SystemPrompt': ('web_agent.agent.prompts', 'SystemPrompt'),
	# Agent views (very heavy - over 1 second!)
	'ActionModel': ('web_agent.agent.views', 'ActionModel'),
	'ActionResult': ('web_agent.agent.views', 'ActionResult'),
	'AgentHistoryList': ('web_agent.agent.views', 'AgentHistoryList'),
	'BrowserSession': ('web_agent.browser', 'BrowserSession'),
	'Browser': ('web_agent.browser', 'BrowserSession'),  # Alias for BrowserSession
	'BrowserProfile': ('web_agent.browser', 'BrowserProfile'),
	# Tools (moderate weight)
	'Tools': ('web_agent.tools.service', 'Tools'),
	'Controller': ('web_agent.tools.service', 'Controller'),  # alias
	# DOM service (moderate weight)
	'DomService': ('web_agent.dom.service', 'DomService'),
	# Chat models (very heavy imports)
	'ChatOpenAI': ('web_agent.llm.openai.chat', 'ChatOpenAI'),
	'ChatGoogle': ('web_agent.llm.google.chat', 'ChatGoogle'),
	'ChatAnthropic': ('web_agent.llm.anthropic.chat', 'ChatAnthropic'),
	'Chatwebagent': ('web_agent.llm.web_agent.chat', 'Chatwebagent'),
	'ChatGroq': ('web_agent.llm.groq.chat', 'ChatGroq'),
	'ChatMistral': ('web_agent.llm.mistral.chat', 'ChatMistral'),
	'ChatAzureOpenAI': ('web_agent.llm.azure.chat', 'ChatAzureOpenAI'),
	'ChatOCIRaw': ('web_agent.llm.oci_raw.chat', 'ChatOCIRaw'),
	'ChatOllama': ('web_agent.llm.ollama.chat', 'ChatOllama'),
	'ChatVercel': ('web_agent.llm.vercel.chat', 'ChatVercel'),
	# LLM models module
	'models': ('web_agent.llm.models', None),
	# Sandbox execution
	'sandbox': ('web_agent.sandbox', 'sandbox'),
}


def __getattr__(name: str):
	"""Lazy import mechanism - only import modules when they're actually accessed."""
	if name in _LAZY_IMPORTS:
		module_path, attr_name = _LAZY_IMPORTS[name]
		try:
			from importlib import import_module

			module = import_module(module_path)
			if attr_name is None:
				# For modules like 'models', return the module itself
				attr = module
			else:
				attr = getattr(module, attr_name)
			# Cache the imported attribute in the module's globals
			globals()[name] = attr
			return attr
		except ImportError as e:
			raise ImportError(f'Failed to import {name} from {module_path}: {e}') from e

	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
	'Agent',
	'CodeAgent',
	# 'CodeAgent',
	'BrowserSession',
	'Browser',  # Alias for BrowserSession
	'BrowserProfile',
	'Controller',
	'DomService',
	'SystemPrompt',
	'ActionResult',
	'ActionModel',
	'AgentHistoryList',
	# Chat models
	'ChatOpenAI',
	'ChatGoogle',
	'ChatAnthropic',
	'Chatwebagent',
	'ChatGroq',
	'ChatMistral',
	'ChatAzureOpenAI',
	'ChatOCIRaw',
	'ChatOllama',
	'ChatVercel',
	'Tools',
	'Controller',
	# LLM models module
	'models',
	# Sandbox execution
	'sandbox',
]
