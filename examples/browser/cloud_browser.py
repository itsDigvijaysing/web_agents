"""
Examples of using web-agent cloud browser service.

Prerequisites:
1. Set web_agent_API_KEY environment variable
2. Active subscription at https://cloud.web-agent.com
"""

import asyncio

from dotenv import load_dotenv

from web_agent import Agent, Browser, Chatwebagent

load_dotenv()


async def basic():
	"""Simplest usage - just pass cloud params directly."""
	browser = Browser(use_cloud=True)

	agent = Agent(
		task='Go to github.com/web-agent/web-agent and tell me the star count',
		llm=Chatwebagent(model='bu-2-0'),
		browser=browser,
	)

	result = await agent.run()
	print(f'Result: {result}')


async def full_config():
	"""Full cloud configuration with specific profile."""
	browser = Browser(
		# cloud_profile_id='21182245-590f-4712-8888-9611651a024c',
		cloud_proxy_country_code='jp',
		cloud_timeout=60,
	)

	agent = Agent(
		task='go and check my ip address and the location',
		llm=Chatwebagent(model='bu-2-0'),
		browser=browser,
	)

	result = await agent.run()
	print(f'Result: {result}')


async def main():
	try:
		# await basic()
		await full_config()
	except Exception as e:
		print(f'Error: {e}')


if __name__ == '__main__':
	asyncio.run(main())
