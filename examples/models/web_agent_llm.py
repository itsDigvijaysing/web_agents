"""
Example of the fastest + smartest LLM for browser automation.

Setup:
1. Get your API key from https://cloud.web-agent.com/new-api-key
2. Set environment variable: export web_agent_API_KEY="your-key"
"""

import asyncio
import os

from dotenv import load_dotenv

from web_agent import Agent, Chatwebagent

load_dotenv()

if not os.getenv('web_agent_API_KEY'):
	raise ValueError('web_agent_API_KEY is not set')


async def main():
	agent = Agent(
		task='Find the number of stars of the web-agent repo',
		llm=Chatwebagent(model='bu-2-0'),
	)

	# Run the agent
	await agent.run()


if __name__ == '__main__':
	asyncio.run(main())
