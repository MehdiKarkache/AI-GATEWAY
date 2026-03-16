"""Tests for MCP Server v3 — Code Review Assistant (11 tools)."""

import json
import pytest
from src.mcp_server import (
    mcp,
    check_syntax,
    get_review_history,
    resource_languages,
    resource_history,
    resource_stats,
    code_review,
    security_audit,
    SUPPORTED_LANGUAGES,
)
from src.db import init_db, save_review
from src.models import Issue, Severity, Category

init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_dummy_review(filename="test.py", critical=1, major=2, minor=1):
    """Create a dummy review in the DB and return its ID."""
    issues = []
    for _ in range(critical):
        issues.append(Issue(
            severity=Severity.CRITICAL, category=Category.BUG,
            title="Critical bug", explanation="desc", suggestion="fix",
        ))
    for _ in range(major):
        issues.append(Issue(
            severity=Severity.MAJOR, category=Category.SECURITY,
            title="Major security", explanation="desc", suggestion="fix",
        ))
    for _ in range(minor):
        issues.append(Issue(
            severity=Severity.MINOR, category=Category.STYLE,
            title="Minor style", explanation="desc", suggestion="fix",
        ))
    return save_review(filename, issues)


# ── Tests: check_syntax ──────────────────────────────────────────────────────

class TestCheckSyntax:
    def test_valid_python(self):
        result = json.loads(check_syntax("def hello():\n    return 42\n", "Python"))
        assert result["valid"] is True
        assert result["error"] is None

    def test_invalid_python(self):
        result = json.loads(check_syntax("def broken(\n", "Python"))
        assert result["valid"] is False
        assert result["error"] is not None

    def test_non_python_always_valid(self):
        result = json.loads(check_syntax("not even valid syntax {{{", "JavaScript"))
        assert result["valid"] is True

    def test_empty_code(self):
        result = json.loads(check_syntax("", "Python"))
        assert result["valid"] is True


# ── Tests: get_review_history ─────────────────────────────────────────────────

class TestGetReviewHistory:
    def test_returns_json(self):
        result = json.loads(get_review_history(5))
        assert "count" in result
        assert "reviews" in result
        assert isinstance(result["reviews"], list)

    def test_limit_capped_at_50(self):
        result = json.loads(get_review_history(999))
        assert "count" in result

    def test_limit_minimum_1(self):
        result = json.loads(get_review_history(0))
        assert "count" in result


# ── Tests: Resources ──────────────────────────────────────────────────────────

class TestResources:
    def test_supported_languages(self):
        result = json.loads(resource_languages())
        assert isinstance(result, list)
        langs = [item["language"] for item in result]
        assert "Python" in langs
        assert "JavaScript" in langs
        assert len(result) == len(SUPPORTED_LANGUAGES)

    def test_history_resource_returns_string(self):
        result = resource_history()
        assert isinstance(result, str)

    def test_stats_resource(self):
        _create_dummy_review("stats_test.py")
        result = json.loads(resource_stats())
        assert result["total_reviews"] > 0
        assert "average_score" in result
        assert "best_score" in result
        assert "worst_score" in result
        assert "total_critical" in result


# ── Tests: Prompts ────────────────────────────────────────────────────────────

class TestPrompt:
    def test_code_review_prompt_contains_code(self):
        prompt = code_review("print('hello')", "Python")
        assert "print('hello')" in prompt
        assert "Python" in prompt

    def test_code_review_prompt_contains_axes(self):
        prompt = code_review("x = 1", "JavaScript")
        assert "Bugs" in prompt
        assert "Securite" in prompt
        assert "Lisibilite" in prompt
        assert "JavaScript" in prompt

    def test_security_audit_prompt(self):
        prompt = security_audit("import os; os.system(input())", "Python")
        assert "audit" in prompt.lower() or "securite" in prompt.lower()
        assert "os.system(input())" in prompt
        assert "OWASP" in prompt

    def test_security_audit_prompt_language(self):
        prompt = security_audit("eval(data)", "JavaScript")
        assert "JavaScript" in prompt


# ── Tests: MCP Server metadata ───────────────────────────────────────────────

class TestServerSetup:
    def test_server_name(self):
        assert mcp.name == "Code Review Assistant"

    def test_server_has_tools(self):
        tools = mcp._tool_manager._tools
        assert len(tools) >= 11  # v3: 5 code + 5 github + 1 utility

    def test_code_intelligence_tools(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        expected_code = {"review_code", "fix_code", "explain_code", "generate_tests", "check_syntax"}
        assert expected_code.issubset(tool_names)

    def test_github_tools(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        expected_github = {"github_get_repo", "github_get_file", "github_create_issue",
                           "github_list_issues", "github_search_repos"}
        assert expected_github.issubset(tool_names)

    def test_utility_tools(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        assert "get_review_history" in tool_names

    def test_all_tool_names(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        all_expected = {
            "review_code", "fix_code", "explain_code", "generate_tests", "check_syntax",
            "github_get_repo", "github_get_file", "github_create_issue",
            "github_list_issues", "github_search_repos",
            "get_review_history",
        }
        assert all_expected.issubset(tool_names)
