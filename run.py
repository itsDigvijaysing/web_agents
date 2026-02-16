"""
Run web-agent to perform browser tasks using Gemini.

Usage:
	.venv/bin/python run.py
	.venv/bin/python run.py "Search for latest AI news and summarize top 3 results"
	.venv/bin/python run.py --headless "Go to github.com and tell me the trending repos"
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from web_agent import Agent, BrowserProfile, BrowserSession
from web_agent.llm.google import ChatGoogle


async def main():
	# Get task from CLI args or use default
	if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
		task = sys.argv[1]
	else:
		task = "Go to google.com, search for 'web browser automation with AI', and tell me the top 3 results with their titles and brief descriptions"

	headless = '--headless' in sys.argv

	llm = ChatGoogle(model='gemini-2.0-flash')

	browser_session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=headless,
		)
	)

	agent = Agent(
		task=task,
		llm=llm,
		browser_session=browser_session,
	)

	print(f'Task: {task}')
	print(f'Mode: {"headless" if headless else "headed (browser visible)"}')
	print('---')

	result = await agent.run()

	print('---')
	print(f'Result: {result.final_result()}')


if __name__ == '__main__':
	asyncio.run(main())
