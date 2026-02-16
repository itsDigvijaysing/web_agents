"""Test web agent model button click."""

from web_agent.llm.web_agent.chat import Chatwebagent
from tests.ci.models.model_test_helper import run_model_button_click_test


async def test_webagent_bu_latest(httpserver):
	"""Test web agent bu-latest can click a button."""
	await run_model_button_click_test(
		model_class=Chatwebagent,
		model_name='bu-latest',
		api_key_env='web_agent_API_KEY',
		extra_kwargs={},
		httpserver=httpserver,
	)
