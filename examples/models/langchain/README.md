# Langchain Models (legacy)

This directory contains example of how to still use Langchain models with the new web agent chat models.

## How to use

```python
from langchain_openai import ChatOpenAI

from web_agent import Agent
from .chat import ChatLangchain

async def main():
	"""Basic example using ChatLangchain with OpenAI through LangChain."""

	# Create a LangChain model (OpenAI)
	langchain_model = ChatOpenAI(
		model='gpt-4.1-mini',
		temperature=0.1,
	)

	# Wrap it with ChatLangchain to make it compatible with web-agent
	llm = ChatLangchain(chat=langchain_model)

    agent = Agent(
        task="Go to google.com and search for 'browser automation with Python'",
        llm=llm,
    )

    history = await agent.run()

    print(history.history)
```
