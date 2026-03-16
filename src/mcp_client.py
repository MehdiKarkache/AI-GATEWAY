"""
MCP Client — Code Review Assistant
===================================
Client Python pour appeler le serveur MCP en mode stdio ou SSE.
Utilisable de maniere programmatique ou depuis le CLI.

Usage programmatique :
    from src.mcp_client import MCPClient

    async with MCPClient() as client:
        result = await client.review_code("def f(): pass", "Python")
        print(result)
"""

import asyncio
import json
import sys
import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client


class MCPClient:
    """Client MCP haute-niveau pour le Code Review Assistant."""

    def __init__(self, transport: str = "stdio", sse_url: str = "http://127.0.0.1:8080/sse"):
        self._transport = transport
        self._sse_url = sse_url
        self._session: ClientSession | None = None
        self._cm_stack = []

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.disconnect()

    async def connect(self):
        """Etablit la connexion au serveur MCP."""
        if self._transport == "stdio":
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "src.mcp_server"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env={**os.environ},
            )
            self._stdio_cm = stdio_client(server_params)
            read_stream, write_stream = await self._stdio_cm.__aenter__()
            self._cm_stack.append(self._stdio_cm)
        else:
            self._sse_cm = sse_client(self._sse_url)
            read_stream, write_stream = await self._sse_cm.__aenter__()
            self._cm_stack.append(self._sse_cm)

        self._session_cm = ClientSession(read_stream, write_stream)
        self._session = await self._session_cm.__aenter__()
        self._cm_stack.append(self._session_cm)

        await self._session.initialize()

    async def disconnect(self):
        """Ferme la connexion."""
        for cm in reversed(self._cm_stack):
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._cm_stack.clear()
        self._session = None

    # ── Introspection ─────────────────────────────────────────────────────────

    async def list_tools(self) -> list[dict]:
        """Liste tous les tools disponibles sur le serveur."""
        result = await self._session.list_tools()
        return [
            {"name": t.name, "description": t.description}
            for t in result.tools
        ]

    async def list_resources(self) -> list[dict]:
        """Liste toutes les resources disponibles."""
        result = await self._session.list_resources()
        return [
            {"uri": str(r.uri), "name": r.name, "description": r.description}
            for r in result.resources
        ]

    async def list_prompts(self) -> list[dict]:
        """Liste tous les prompts disponibles."""
        result = await self._session.list_prompts()
        return [
            {"name": p.name, "description": p.description}
            for p in result.prompts
        ]

    # ── Tool calls ────────────────────────────────────────────────────────────

    async def call_tool(self, name: str, arguments: dict | None = None) -> str:
        """Appelle un tool MCP generique et retourne le texte de la reponse."""
        result = await self._session.call_tool(name, arguments or {})
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    async def review_code(self, code: str, language: str = "Python", filename: str = "untitled") -> dict:
        """Analyse du code — retourne le rapport parse."""
        raw = await self.call_tool("review_code", {
            "code": code,
            "language": language,
            "filename": filename,
        })
        return json.loads(raw)

    async def fix_code(self, code: str, language: str = "Python") -> dict:
        """Auto-fix code and return corrected version with changelog."""
        raw = await self.call_tool("fix_code", {
            "code": code,
            "language": language,
        })
        return json.loads(raw)

    async def explain_code(self, code: str, language: str = "Python", detail_level: str = "medium") -> dict:
        """Explain code in plain language."""
        raw = await self.call_tool("explain_code", {
            "code": code,
            "language": language,
            "detail_level": detail_level,
        })
        return json.loads(raw)

    async def generate_tests(self, code: str, language: str = "Python", framework: str = "auto") -> dict:
        """Generate unit tests for code."""
        raw = await self.call_tool("generate_tests", {
            "code": code,
            "language": language,
            "framework": framework,
        })
        return json.loads(raw)

    async def check_syntax(self, code: str, language: str = "Python") -> dict:
        """Validation syntaxe."""
        raw = await self.call_tool("check_syntax", {"code": code, "language": language})
        return json.loads(raw)

    async def get_history(self, limit: int = 10) -> dict:
        """Historique des analyses."""
        raw = await self.call_tool("get_review_history", {"limit": limit})
        return json.loads(raw)

    # ── GitHub tools ──────────────────────────────────────────────────────────

    async def github_get_repo(self, owner: str, repo: str) -> dict:
        """Get GitHub repository information."""
        raw = await self.call_tool("github_get_repo", {"owner": owner, "repo": repo})
        return json.loads(raw)

    async def github_get_file(self, owner: str, repo: str, path: str, branch: str = "") -> dict:
        """Get file contents from a GitHub repository."""
        args = {"owner": owner, "repo": repo, "path": path}
        if branch:
            args["branch"] = branch
        raw = await self.call_tool("github_get_file", args)
        return json.loads(raw)

    async def github_create_issue(self, owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None) -> dict:
        """Create a GitHub issue."""
        args = {"owner": owner, "repo": repo, "title": title, "body": body}
        if labels:
            args["labels"] = labels
        raw = await self.call_tool("github_create_issue", args)
        return json.loads(raw)

    async def github_list_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> dict:
        """List issues on a GitHub repository."""
        raw = await self.call_tool("github_list_issues", {
            "owner": owner, "repo": repo, "state": state, "limit": limit,
        })
        return json.loads(raw)

    async def github_search_repos(self, query: str, limit: int = 5) -> dict:
        """Search GitHub repositories."""
        raw = await self.call_tool("github_search_repos", {"query": query, "limit": limit})
        return json.loads(raw)

    # ── Resource reads ────────────────────────────────────────────────────────

    async def read_resource(self, uri: str) -> str:
        """Lit une resource MCP par son URI."""
        result = await self._session.read_resource(uri)
        parts = []
        for block in result.contents:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    async def get_stats(self) -> dict:
        """Stats globales."""
        raw = await self.read_resource("review://stats")
        return json.loads(raw)

    async def get_languages(self) -> list:
        """Langages supportes."""
        raw = await self.read_resource("review://supported-languages")
        return json.loads(raw)

    # ── Prompt generation ─────────────────────────────────────────────────────

    async def get_prompt(self, name: str, arguments: dict | None = None) -> str:
        """Genere un prompt MCP."""
        result = await self._session.get_prompt(name, arguments or {})
        parts = []
        for msg in result.messages:
            if hasattr(msg.content, "text"):
                parts.append(msg.content.text)
        return "\n".join(parts)
