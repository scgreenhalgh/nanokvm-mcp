"""NanoKVM MCP Server - Control NanoKVM devices via Model Context Protocol."""

__version__ = "0.1.0"

from .client import NanoKVMClient
from .server import mcp

__all__ = ["NanoKVMClient", "mcp"]
