"""
Setup:
1. Get your API key from https://cloud.web-agent.com/new-api-key
2. Set environment variable: export web_agent_API_KEY="your-key"
"""

from dotenv import load_dotenv

from web_agent import Agent, Chatwebagent

load_dotenv()

agent = Agent(
	task='Find the number of stars of the following repos: web-agent, playwright, stagehand, react, nextjs',
	llm=Chatwebagent(model='bu-2-0'),
)
agent.run_sync()
