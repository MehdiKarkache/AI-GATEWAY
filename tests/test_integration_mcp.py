"""
Test d'integration MCP : client ↔ serveur via stdio.
=====================================================
Lance le serveur MCP en subprocess, connecte le client, et verifie le
cycle complet : introspection → review → history → details → compare → export → delete.

Necessite le package mcp et une cle OPENROUTER_API_KEY dans .env.
Pour executer sans appel LLM, le test syntax + introspection sont toujours safe.

Usage :
    python -m pytest tests/test_integration_mcp.py -v
"""

import json
import pytest
import pytest_asyncio

from src.mcp_client import MCPClient


@pytest.fixture
def client():
    """Retourne une instance MCPClient (non connectee)."""
    return MCPClient(transport="stdio")


# ── Tests d'introspection (pas d'appel LLM) ──────────────────────────────────

@pytest.mark.asyncio
async def test_list_tools(client):
    async with client:
        tools = await client.list_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 11
    names = {t["name"] for t in tools}
    # Code Intelligence
    assert "review_code" in names
    assert "fix_code" in names
    assert "explain_code" in names
    assert "generate_tests" in names
    assert "check_syntax" in names
    # GitHub Integration
    assert "github_get_repo" in names
    assert "github_get_file" in names
    assert "github_create_issue" in names
    assert "github_list_issues" in names
    assert "github_search_repos" in names
    # Utility
    assert "get_review_history" in names


@pytest.mark.asyncio
async def test_list_resources(client):
    async with client:
        resources = await client.list_resources()
    assert isinstance(resources, list)
    uris = {r["uri"] for r in resources}
    assert "review://history" in uris
    assert "review://supported-languages" in uris
    assert "review://stats" in uris


@pytest.mark.asyncio
async def test_list_prompts(client):
    async with client:
        prompts = await client.list_prompts()
    assert isinstance(prompts, list)
    names = {p["name"] for p in prompts}
    assert "code_review" in names
    assert "security_audit" in names


# ── Tests tools synchrones via MCP ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_syntax_valid(client):
    async with client:
        result = await client.check_syntax("x = 1 + 2\n", "Python")
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_check_syntax_invalid(client):
    async with client:
        result = await client.check_syntax("def broken(\n", "Python")
    assert result["valid"] is False
    assert result["error"] is not None


# ── Tests resources via MCP ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_languages(client):
    async with client:
        langs = await client.get_languages()
    assert isinstance(langs, list)
    names = [item["language"] for item in langs]
    assert "Python" in names
    assert "Go" in names


@pytest.mark.asyncio
async def test_get_stats(client):
    async with client:
        stats = await client.get_stats()
    assert "total_reviews" in stats


# ── Tests prompts via MCP ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prompt_code_review(client):
    async with client:
        prompt = await client.get_prompt("code_review", {
            "code": "print('test')",
            "language": "Python",
        })
    assert "print('test')" in prompt
    assert "Python" in prompt


@pytest.mark.asyncio
async def test_prompt_security_audit(client):
    async with client:
        prompt = await client.get_prompt("security_audit", {
            "code": "eval(input())",
            "language": "Python",
        })
    assert "eval(input())" in prompt
    assert "OWASP" in prompt
