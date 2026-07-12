"""Agent task command handler."""

import logging
import os
from typing import Any

from web_agent.skill_cli.api_key import APIKeyRequired, require_api_key
from web_agent.skill_cli.sessions import SessionInfo

logger = logging.getLogger(__name__)

# Cloud-only flags that only work in remote mode
CLOUD_ONLY_FLAGS = [
	'session_id',
	'proxy_country',
	'wait',
	'stream',
	'flash',
	'keep_alive',
	'thinking',
	'start_url',
	'metadata',
	'secret',
	'allowed_domain',
	'skill_id',
	'structured_output',
	'judge',
	'judge_ground_truth',
]


async def handle(session: SessionInfo, params: dict[str, Any]) -> Any:
	"""Handle agent run command.

	Routes based on browser mode:
	- Remote mode (--browser remote): Uses Cloud API with US proxy by default
	- Local mode (default): Uses local web-agent agent
	"""
	task = params.get('task')
	if not task:
		return {'success': False, 'error': 'No task provided'}

	# Route based on browser mode
	if session.browser_mode == 'remote':
		# Remote mode requires web-agent API key
		try:
			require_api_key('Cloud agent tasks')
		except APIKeyRequired as e:
			return {'success': False, 'error': str(e)}
		return await _handle_cloud_task(params)
	else:
		# Check if user tried to use cloud-only flags in local mode
		used_cloud_flags = [f for f in CLOUD_ONLY_FLAGS if params.get(f)]
		if used_cloud_flags:
			from web_agent.skill_cli.install_config import is_mode_available

			flags_str = ', '.join(f'--{f.replace("_", "-")}' for f in used_cloud_flags)

			if is_mode_available('remote'):
				# Remote is available, user just needs to use it
				return {
					'success': False,
					'error': f'Cloud-only flags used in local mode: {flags_str}\nUse --browser remote to enable cloud features.',
				}
			else:
				# Remote not installed (--local-only install)
				return {
					'success': False,
					'error': f'Cloud-only flags require remote mode: {flags_str}\n'
					f'Remote mode is not installed. Reinstall to enable:\n'
					f'  curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --remote-only\n'
					f'  curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --full',
				}
		return await _handle_local_task(session, params)


async def _handle_cloud_task(params: dict[str, Any]) -> Any:
	"""Cloud task execution has been removed. Use local mode (--browser local) instead."""
	return {
		'success': False,
		'error': 'Cloud task execution has been removed from this project. Use --browser local instead.',
		'task': params.get('task'),
	}


def _parse_key_value_list(items: list[str] | None) -> dict[str, str | None] | None:
	"""Parse a list of 'key=value' strings into a dict."""
	if not items:
		return None
	result: dict[str, str | None] = {}
	for item in items:
		if '=' in item:
			key, value = item.split('=', 1)
			result[key] = value
	return result if result else None


async def _handle_local_task(session: SessionInfo, params: dict[str, Any]) -> Any:
	"""Handle task execution locally with web-agent agent."""
	task = params['task']
	max_steps = params.get('max_steps')
	model = params.get('llm')  # Optional model override

	try:
		# Import agent and LLM
		from web_agent.agent.service import Agent

		# Try to get LLM from environment (with optional model override)
		llm = await get_llm(model=model)
		if llm is None:
			if model:
				return {
					'success': False,
					'error': f'Could not initialize model "{model}". '
					f'Make sure the appropriate API key is set (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY).',
				}
			return {
				'success': False,
				'error': 'No LLM configured. Set web_agent_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY',
			}

		# Create and run agent
		agent = Agent(
			task=task,
			llm=llm,
			browser_session=session.browser_session,
		)

		logger.info(f'Running local agent task: {task}')
		run_kwargs = {}
		if max_steps is not None:
			run_kwargs['max_steps'] = max_steps
		result = await agent.run(**run_kwargs)

		# Extract result info
		final_result = result.final_result() if result else None

		return {
			'success': True,
			'task': task,
			'steps': len(result) if result else 0,
			'result': str(final_result) if final_result else None,
			'done': result.is_done() if result else False,
		}

	except Exception as e:
		logger.exception(f'Local agent task failed: {e}')
		return {
			'success': False,
			'error': str(e),
			'task': task,
		}


def _get_verified_models() -> dict[str, set[str]]:
	"""Extract verified model names from SDK sources of truth."""
	import typing

	from anthropic.types.model_param import ModelParam
	from openai.types.shared.chat_model import ChatModel

	from web_agent.llm.google.chat import VerifiedGeminiModels

	# OpenAI: ChatModel is a Literal type
	openai_models = set(typing.get_args(ChatModel))

	# Anthropic: ModelParam is Union[Literal[...], str] - extract the Literal
	anthropic_literal = typing.get_args(ModelParam)[0]
	anthropic_models = set(typing.get_args(anthropic_literal))

	# Google: VerifiedGeminiModels Literal
	google_models = set(typing.get_args(VerifiedGeminiModels))

	# web-agent: cloud models
	web_agent_models = {'bu-latest', 'bu-1-0', 'bu-2-0'}

	return {
		'openai': openai_models,
		'anthropic': anthropic_models,
		'google': google_models,
		'web-agent': web_agent_models,
	}


_VERIFIED_MODELS: dict[str, set[str]] | None = None


def _get_provider_for_model(model: str) -> str | None:
	"""Determine the provider by checking SDK verified model lists."""
	global _VERIFIED_MODELS
	if _VERIFIED_MODELS is None:
		_VERIFIED_MODELS = _get_verified_models()

	for provider, models in _VERIFIED_MODELS.items():
		if model in models:
			return provider

	return None


def get_llm(model: str | None = None) -> Any:
	"""Get LLM instance from environment configuration.

	Args:
		model: Optional model name to use. If provided, will instantiate
		       the appropriate provider for that model. If not provided,
		       auto-detects from available API keys.

	Supported providers: OpenAI, Anthropic, Google, web-agent.
	Model names are validated against each SDK's verified model list.
	"""
	from web_agent.llm import ChatAnthropic, Chatwebagent, ChatGoogle, ChatOpenAI

	if model:
		provider = _get_provider_for_model(model)

		if provider == 'openai':
			return ChatOpenAI(model=model)
		elif provider == 'anthropic':
			return ChatAnthropic(model=model)
		elif provider == 'google':
			return ChatGoogle(model=model)
		elif provider == 'web-agent':
			return Chatwebagent(model=model)
		else:
			logger.warning(f'Unknown model: {model}. Not in any verified model list.')
			return None

	# No model specified - auto-detect from available API keys
	if os.environ.get('web_agent_API_KEY'):
		return Chatwebagent()

	if os.environ.get('OPENAI_API_KEY'):
		return ChatOpenAI(model='o3')

	if os.environ.get('ANTHROPIC_API_KEY'):
		return ChatAnthropic(model='claude-sonnet-4-0')

	if os.environ.get('GOOGLE_API_KEY'):
		return ChatGoogle(model='gemini-flash-latest')

	return None
