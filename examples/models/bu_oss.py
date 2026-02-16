"""
Setup:
1. Get your API key from https://cloud.web-agent.com/new-api-key
2. Set environment variable: export web_agent_API_KEY="your-key"
"""

from dotenv import load_dotenv

from web_agent import Agent, Chatwebagent

load_dotenv()

try:
	from lmnr import Laminar

	Laminar.initialize()
except ImportError:
	pass

# Point to local llm-use server for testing
llm = Chatwebagent(
	model='web-agent/bu-30b-a3b-preview',  # BU Open Source Model!!
)

agent = Agent(
	task='Find the number of stars of web-agent and stagehand. Tell me which one has more stars :)',
	llm=llm,
	flash_mode=True,
)
agent.run_sync()
