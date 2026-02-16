"""MCP (Model Context Protocol) support for web-agent.

This module provides integration with MCP servers and clients for browser automation.
"""

from web_agent.mcp.client import MCPClient
from web_agent.mcp.controller import MCPToolWrapper

__all__ = ['MCPClient', 'MCPToolWrapper', 'webagentServer']  # type: ignore


def __getattr__(name):
	"""Lazy import to avoid importing server module when only client is needed."""
	if name == 'webagentServer':
		from web_agent.mcp.server import webagentServer

		return webagentServer
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
