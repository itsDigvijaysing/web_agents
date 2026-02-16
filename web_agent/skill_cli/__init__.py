"""web-agent CLI package.

This package provides a fast command-line interface for browser automation.
The CLI uses a session server architecture for persistent browser sessions.

Usage:
    web-agent open https://example.com
    web-agent click 5
    web-agent type "Hello World"
    web-agent python "print(browser.url)"
    web-agent run "Fill the contact form"
    web-agent close
"""

__all__ = ['main']


def __getattr__(name: str):
	"""Lazy import to avoid runpy warnings when running as module."""
	if name == 'main':
		from web_agent.skill_cli.main import main

		return main
	raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
