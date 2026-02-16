import asyncio

from web_agent import Agent, Chatwebagent


async def main() -> None:
	agent = Agent(
		task='Please find the latest commit on web-agent/web-agent repo and tell me the commit message. Please summarize what it is about.',
		llm=Chatwebagent(model='bu-2-0'),
		demo_mode=True,
	)
	await agent.run(max_steps=5)


if __name__ == '__main__':
	asyncio.run(main())
