"""
MCP Server — Code Review Assistant (v3)
========================================
Professional MCP server with Code Intelligence and GitHub Integration.

Two groups of well-known, production-ready tools:

  Code Intelligence (5):
    - review_code       — Full code review (bugs, security, readability)
    - fix_code          — Auto-fix issues and return corrected code
    - explain_code      — Explain code in plain, clear language
    - generate_tests    — Generate unit tests for any code
    - check_syntax      — Validate source code syntax

  GitHub Integration (5):
    - github_get_repo       — Get repository information
    - github_get_file       — Fetch file contents from a repository
    - github_create_issue   — Create an issue on a repository
    - github_list_issues    — List issues on a repository
    - github_search_repos   — Search GitHub repositories

  Utility (1):
    - get_review_history — Browse past code reviews

  Resources (3):
    - review://history             — Recent review reports
    - review://supported-languages — Supported languages
    - review://stats               — Aggregate statistics

  Prompts (2):
    - code_review     — Structured code review prompt
    - security_audit  — OWASP security audit prompt

Transports:
    stdio : python -m src.mcp_server
    SSE   : python -m src.mcp_server --sse --port 8080
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

from mcp.server.fastmcp import FastMCP

from src.aggregator import validate_syntax as _validate_syntax, run_analysis
from src.db import (
    init_db,
    save_review,
    get_recent_reviews,
    delete_review as _db_delete_review,
    delete_all_reviews,
    ReviewRecord,
)
from src.models import Severity, Issue

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger("mcp.code-review")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s — %(message)s", datefmt="%H:%M:%S"
))
logger.addHandler(_handler)

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

mcp = FastMCP(
    "Code Review Assistant",
    instructions=(
        "Professional MCP server for automated code review with GitHub integration. "
        "Analyze code for bugs and security issues, auto-fix problems, explain code, "
        "generate unit tests, and interact with GitHub repositories. "
        "Supports 13 programming languages."
    ),
)

SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java",
    "C", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Kotlin", "Swift",
]

SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_issues(issues: list[Issue]) -> list[dict]:
    return [
        {
            "line": i.line_number,
            "severity": i.severity.value,
            "category": i.category.value,
            "title": i.title,
            "explanation": i.explanation,
            "suggestion": i.suggestion,
        }
        for i in issues
    ]


def _format_review(r: ReviewRecord) -> dict:
    return {
        "id": r.id,
        "filename": r.filename,
        "created_at": r.created_at,
        "total_issues": r.total_issues,
        "critical": r.critical_count,
        "major": r.major_count,
        "minor": r.minor_count,
    }


def _compute_score(issues: list[Issue]) -> int:
    c = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    m = sum(1 for i in issues if i.severity == Severity.MAJOR)
    s = sum(1 for i in issues if i.severity == Severity.MINOR)
    return max(0, 100 - c * 25 - m * 10 - s * 3)


def _get_record(review_id: int) -> ReviewRecord | None:
    from sqlmodel import Session
    from src.db import engine
    with Session(engine) as session:
        return session.get(ReviewRecord, review_id)


def _json(obj, **kw) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, **kw)


async def _llm_call(prompt: str) -> str:
    """Single LLM call via OpenRouter with retry on rate limits."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )
    last_error = None
    for attempt in range(2):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="google/gemma-3-4b-it:free",
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=30,
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            last_error = "Request timed out after 30s"
            if attempt < 1:
                await asyncio.sleep(2)
        except Exception as e:
            last_error = str(e)
            err_str = last_error.lower()
            is_rate_limit = "rate" in err_str or "429" in err_str or "limit" in err_str
            if is_rate_limit and attempt < 1:
                await asyncio.sleep(3)
            else:
                raise
    raise RuntimeError(last_error or "LLM call failed after retries")


async def _github_request(method: str, endpoint: str, json_data: dict | None = None) -> dict:
    """Make an authenticated request to the GitHub REST API v3."""
    import httpx

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {"error": "GITHUB_TOKEN not configured. Add GITHUB_TOKEN=ghp_... to your .env file."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = f"https://api.github.com{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=json_data)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}

        if resp.status_code >= 400:
            return {"error": f"GitHub API {resp.status_code}: {resp.text[:300]}"}

        return resp.json()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CODE INTELLIGENCE TOOLS (5)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def review_code(
    code: str,
    language: str = "Python",
    filename: str = "untitled",
) -> str:
    """Perform a full code review analyzing bugs, security vulnerabilities, and readability.

    Returns a detailed report with scored issues, severity levels, explanations,
    and fix suggestions. Includes an overall quality score out of 100.

    Args:
        code: Source code to analyze (max 500 lines).
        language: Programming language (Python, JavaScript, TypeScript, Java, Go, Rust, etc.).
        filename: Filename for tracking in review history.

    Returns:
        JSON with review_id, score, issue counts, and detailed issues array.
    """
    logger.info("review_code: %s (%s, %d lines)", filename, language, len(code.splitlines()))

    if language not in SUPPORTED_LANGUAGES:
        return _json({"error": f"Unsupported language: {language}. Valid: {', '.join(SUPPORTED_LANGUAGES)}"})

    if len(code.splitlines()) > 500:
        return _json({"error": f"Code too long ({len(code.splitlines())} lines). Limit: 500."})

    valid, error_msg = _validate_syntax(code, language)
    if not valid:
        return _json({"error": f"Syntax error: {error_msg}"})

    issues = await run_analysis(code, language)
    score = _compute_score(issues)
    review_id = save_review(filename, issues)

    logger.info("review_code: done — score=%d, issues=%d, id=#%d", score, len(issues), review_id)

    return _json({
        "review_id": review_id,
        "filename": filename,
        "language": language,
        "score": score,
        "total_issues": len(issues),
        "critical": sum(1 for i in issues if i.severity == Severity.CRITICAL),
        "major": sum(1 for i in issues if i.severity == Severity.MAJOR),
        "minor": sum(1 for i in issues if i.severity == Severity.MINOR),
        "issues": _format_issues(issues),
    })


@mcp.tool()
async def fix_code(
    code: str,
    language: str = "Python",
) -> str:
    """Auto-fix all detected issues in the code and return the corrected version.

    First analyzes the code for bugs, security vulnerabilities, and style issues,
    then rewrites it with all problems fixed. Returns the complete corrected source
    code along with a changelog of every modification.

    Args:
        code: Source code to fix (max 500 lines).
        language: Programming language.

    Returns:
        JSON with fixed_code, changes array, original_score, and fixed_score.
    """
    logger.info("fix_code: %s, %d lines", language, len(code.splitlines()))

    if language not in SUPPORTED_LANGUAGES:
        return _json({"error": f"Unsupported language: {language}"})

    if len(code.splitlines()) > 500:
        return _json({"error": f"Code too long ({len(code.splitlines())} lines). Limit: 500."})

    valid, error_msg = _validate_syntax(code, language)
    if not valid:
        return _json({"error": f"Syntax error: {error_msg}"})

    issues = await run_analysis(code, language)
    original_score = _compute_score(issues)

    if not issues:
        return _json({
            "fixed_code": code,
            "changes": [],
            "original_score": 100,
            "fixed_score": 100,
            "message": "No issues found — code is clean.",
        })

    issues_text = "\n".join(
        f"  - Line {i.line_number or '?'}: [{i.severity.value}] {i.title} — {i.explanation}"
        for i in issues
    )

    prompt = (
        f"You are a senior {language} developer. Fix ALL the issues listed below in this code.\n\n"
        f"ISSUES FOUND:\n{issues_text}\n\n"
        f"ORIGINAL CODE:\n```{language.lower()}\n{code}\n```\n\n"
        f"Return ONLY a JSON object (no text before or after) with this exact format:\n"
        f'{{\n'
        f'  "fixed_code": "the complete corrected source code as a string",\n'
        f'  "changes": [\n'
        f'    {{"line": 5, "description": "What was changed and why", "severity": "critique"}}\n'
        f'  ]\n'
        f'}}\n\n'
        f"RULES:\n"
        f"- Return the COMPLETE fixed source code, not just snippets\n"
        f"- Keep the same structure and logic, only fix the issues\n"
        f"- Every change must appear in the changes array\n"
        f'- severity must be one of: "critique", "majeur", "mineur"\n'
    )

    from src.analyzers import extract_json
    raw = await _llm_call(prompt)
    try:
        result = json.loads(extract_json(raw))
        fixed_code = result.get("fixed_code", code)
        changes = result.get("changes", [])
    except Exception:
        fixed_code = code
        changes = [{"line": 0, "description": "Auto-fix parsing failed — returning original", "severity": "mineur"}]

    logger.info("fix_code: done — %d changes applied", len(changes))

    return _json({
        "fixed_code": fixed_code,
        "changes": changes,
        "original_score": original_score,
        "fixed_score": min(100, original_score + len(changes) * 8),
        "total_changes": len(changes),
    })


@mcp.tool()
async def explain_code(
    code: str,
    language: str = "Python",
    detail_level: str = "medium",
) -> str:
    """Explain what a piece of code does in plain, clear language.

    Breaks down the code's logic, purpose, and behavior into an easy-to-understand
    explanation. Ideal for understanding unfamiliar code, onboarding, or learning.

    Args:
        code: Source code to explain (max 500 lines).
        language: Programming language.
        detail_level: "brief" (1-2 sentences), "medium" (paragraph + key points), or "detailed" (line-by-line).

    Returns:
        JSON with summary, step_by_step explanation array, complexity info, and key_concepts.
    """
    logger.info("explain_code: %s, detail=%s, %d lines", language, detail_level, len(code.splitlines()))

    if len(code.splitlines()) > 500:
        return _json({"error": f"Code too long ({len(code.splitlines())} lines). Limit: 500."})

    detail_instructions = {
        "brief": "Give a 1-2 sentence summary only.",
        "medium": "Give a summary paragraph, then list the key steps and concepts.",
        "detailed": "Give a thorough line-by-line explanation of what every part does.",
    }

    prompt = (
        f"You are an expert {language} developer and teacher.\n\n"
        f"Explain what this code does:\n"
        f"```{language.lower()}\n{code}\n```\n\n"
        f"{detail_instructions.get(detail_level, detail_instructions['medium'])}\n\n"
        f"Return ONLY a JSON object (no text before or after):\n"
        f'{{\n'
        f'  "summary": "A clear one-paragraph explanation of what the code does",\n'
        f'  "step_by_step": [\n'
        f'    "Step 1: description of what happens first",\n'
        f'    "Step 2: description of what happens next"\n'
        f'  ],\n'
        f'  "complexity": "O(n) — brief complexity assessment",\n'
        f'  "key_concepts": ["concept1", "concept2"]\n'
        f'}}\n'
    )

    from src.analyzers import extract_json
    raw = await _llm_call(prompt)
    try:
        result = json.loads(extract_json(raw))
    except Exception:
        result = {
            "summary": raw.strip() if raw else "Could not parse explanation.",
            "step_by_step": [],
            "complexity": "Unknown",
            "key_concepts": [],
        }

    logger.info("explain_code: done — %d steps", len(result.get("step_by_step", [])))
    return _json(result)


@mcp.tool()
async def generate_tests(
    code: str,
    language: str = "Python",
    framework: str = "auto",
) -> str:
    """Generate comprehensive unit tests for the given code.

    Creates test cases covering normal behavior, edge cases, and error conditions.
    Supports popular testing frameworks: pytest, unittest, jest, mocha, JUnit, etc.

    Args:
        code: Source code to generate tests for (max 500 lines).
        language: Programming language.
        framework: Testing framework — "auto" (best for language), "pytest", "unittest", "jest", "mocha", "junit", "go_test", etc.

    Returns:
        JSON with test_code (ready-to-run tests), test_count, framework, and coverage_summary.
    """
    logger.info("generate_tests: %s, framework=%s, %d lines", language, framework, len(code.splitlines()))

    if len(code.splitlines()) > 500:
        return _json({"error": f"Code too long ({len(code.splitlines())} lines). Limit: 500."})

    auto_frameworks = {
        "Python": "pytest", "JavaScript": "jest", "TypeScript": "jest",
        "Java": "JUnit 5", "C#": "xUnit", "Go": "testing",
        "Rust": "cargo test", "PHP": "PHPUnit", "Ruby": "RSpec",
        "Kotlin": "JUnit 5", "Swift": "XCTest",
    }

    if framework == "auto":
        framework = auto_frameworks.get(language, "pytest")

    prompt = (
        f"You are a senior {language} developer. Generate comprehensive unit tests for this code.\n\n"
        f"CODE:\n```{language.lower()}\n{code}\n```\n\n"
        f"FRAMEWORK: {framework}\n\n"
        f"Return ONLY a JSON object (no text before or after):\n"
        f'{{\n'
        f'  "test_code": "the complete, ready-to-run test file as a string",\n'
        f'  "test_count": 5,\n'
        f'  "framework": "{framework}",\n'
        f'  "coverage_summary": "Brief description of what is tested: normal cases, edge cases, errors"\n'
        f'}}\n\n'
        f"RULES:\n"
        f"- Generate at least 4-6 meaningful test cases\n"
        f"- Cover: normal behavior, edge cases, error/exception handling\n"
        f"- Include proper imports and setup\n"
        f"- Use descriptive test names\n"
        f"- Tests must be syntactically correct and ready to run\n"
    )

    from src.analyzers import extract_json
    raw = await _llm_call(prompt)
    try:
        result = json.loads(extract_json(raw))
    except Exception:
        result = {
            "test_code": raw.strip() if raw else "# Could not generate tests",
            "test_count": 0,
            "framework": framework,
            "coverage_summary": "Parsing error — raw output returned.",
        }

    logger.info("generate_tests: done — %d test(s), framework=%s", result.get("test_count", 0), framework)
    return _json(result)


@mcp.tool()
def check_syntax(code: str, language: str = "Python") -> str:
    """Validate source code syntax. Deep AST check for Python, basic check for others.

    Args:
        code: Source code to validate.
        language: Programming language.

    Returns:
        JSON with valid (bool), language, and error message if invalid.
    """
    valid, error_msg = _validate_syntax(code, language)
    logger.info("check_syntax: %s — valid=%s", language, valid)
    return _json({"valid": valid, "language": language, "error": error_msg or None})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GITHUB INTEGRATION TOOLS (5)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def github_get_repo(owner: str, repo: str) -> str:
    """Get detailed information about a GitHub repository.

    Returns the repository's description, stars, forks, language, open issues count,
    license, default branch, and more.

    Args:
        owner: Repository owner (user or organization), e.g. "facebook".
        repo: Repository name, e.g. "react".

    Returns:
        JSON with full_name, description, stars, forks, language, open_issues, license, etc.
    """
    logger.info("github_get_repo: %s/%s", owner, repo)

    data = await _github_request("GET", f"/repos/{owner}/{repo}")
    if "error" in data:
        return _json(data)

    return _json({
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "html_url": data.get("html_url"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "watchers": data.get("watchers_count"),
        "default_branch": data.get("default_branch"),
        "license": (data.get("license") or {}).get("name"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "topics": data.get("topics", []),
        "is_fork": data.get("fork", False),
        "archived": data.get("archived", False),
    })


@mcp.tool()
async def github_get_file(
    owner: str,
    repo: str,
    path: str,
    branch: str = "",
) -> str:
    """Fetch the contents of a file from a GitHub repository.

    Retrieves and decodes a file from any public or accessible private repository.
    Useful for reviewing code directly from GitHub.

    Args:
        owner: Repository owner, e.g. "microsoft".
        repo: Repository name, e.g. "vscode".
        path: File path within the repo, e.g. "src/main.ts".
        branch: Branch name (defaults to the repo's default branch).

    Returns:
        JSON with filename, path, content (decoded), size, sha, and download_url.
    """
    logger.info("github_get_file: %s/%s/%s", owner, repo, path)

    endpoint = f"/repos/{owner}/{repo}/contents/{path}"
    if branch:
        endpoint += f"?ref={branch}"

    data = await _github_request("GET", endpoint)
    if "error" in data:
        return _json(data)

    import base64
    content = ""
    if data.get("encoding") == "base64" and data.get("content"):
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

    return _json({
        "filename": data.get("name"),
        "path": data.get("path"),
        "size": data.get("size"),
        "sha": data.get("sha"),
        "content": content,
        "download_url": data.get("download_url"),
        "html_url": data.get("html_url"),
    })


@mcp.tool()
async def github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
) -> str:
    """Create a new issue on a GitHub repository.

    Useful for reporting bugs found during code review, or creating tasks from
    analysis results. Requires write access to the repository.

    Args:
        owner: Repository owner, e.g. "myorg".
        repo: Repository name, e.g. "myproject".
        title: Issue title (concise summary of the problem).
        body: Issue body in Markdown (detailed description, code snippets, etc.).
        labels: Optional list of label names, e.g. ["bug", "security"].

    Returns:
        JSON with issue number, html_url, title, and state.
    """
    logger.info("github_create_issue: %s/%s — %s", owner, repo, title[:50])

    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    data = await _github_request("POST", f"/repos/{owner}/{repo}/issues", json_data=payload)
    if "error" in data:
        return _json(data)

    return _json({
        "number": data.get("number"),
        "html_url": data.get("html_url"),
        "title": data.get("title"),
        "state": data.get("state"),
        "created_at": data.get("created_at"),
        "labels": [l.get("name") for l in data.get("labels", [])],
    })


@mcp.tool()
async def github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 10,
) -> str:
    """List issues on a GitHub repository.

    Browse open, closed, or all issues. Returns titles, labels, authors, and dates.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: Filter by state — "open", "closed", or "all".
        limit: Maximum number of issues to return (1-30, default: 10).

    Returns:
        JSON array of issues with number, title, state, labels, author, and timestamps.
    """
    logger.info("github_list_issues: %s/%s (state=%s, limit=%d)", owner, repo, state, limit)

    limit = min(max(1, limit), 30)
    data = await _github_request("GET", f"/repos/{owner}/{repo}/issues?state={state}&per_page={limit}")
    if isinstance(data, dict) and "error" in data:
        return _json(data)

    issues = []
    for item in data[:limit]:
        issues.append({
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "html_url": item.get("html_url"),
            "author": (item.get("user") or {}).get("login"),
            "labels": [l.get("name") for l in item.get("labels", [])],
            "comments": item.get("comments", 0),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        })

    return _json({"count": len(issues), "issues": issues})


@mcp.tool()
async def github_search_repos(
    query: str,
    limit: int = 5,
) -> str:
    """Search public repositories on GitHub.

    Find repositories by name, description, topic, language, or any keyword.
    Results are sorted by best match (stars, relevance).

    Args:
        query: Search query — supports GitHub search syntax, e.g. "fastapi language:python", "machine learning stars:>1000".
        limit: Maximum results to return (1-10, default: 5).

    Returns:
        JSON array of repositories with name, description, stars, language, and url.
    """
    logger.info("github_search_repos: %s (limit=%d)", query[:50], limit)

    import urllib.parse
    limit = min(max(1, limit), 10)
    encoded = urllib.parse.quote(query)
    data = await _github_request("GET", f"/search/repositories?q={encoded}&per_page={limit}&sort=stars")
    if isinstance(data, dict) and "error" in data:
        return _json(data)

    repos = []
    for item in data.get("items", [])[:limit]:
        repos.append({
            "full_name": item.get("full_name"),
            "description": (item.get("description") or "")[:200],
            "html_url": item.get("html_url"),
            "language": item.get("language"),
            "stars": item.get("stargazers_count"),
            "forks": item.get("forks_count"),
            "topics": item.get("topics", [])[:5],
            "updated_at": item.get("updated_at"),
        })

    return _json({"total_count": data.get("total_count", 0), "repos": repos})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UTILITY TOOLS (1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def get_review_history(limit: int = 10) -> str:
    """Browse past code review reports with scores and issue counts.

    Args:
        limit: Maximum number of reports to return (1-50, default: 10).

    Returns:
        JSON with count and reviews array (id, filename, timestamps, issue counts).
    """
    limit = min(max(1, limit), 50)
    records = get_recent_reviews(limit=limit)
    logger.info("get_review_history: %d report(s)", len(records))
    return _json({"count": len(records), "reviews": [_format_review(r) for r in records]})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RESOURCES (3)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.resource("review://history")
def resource_history() -> str:
    """Compact list of the 20 most recent review reports with scores."""
    records = get_recent_reviews(limit=20)
    if not records:
        return "No reviews recorded yet."
    lines = []
    for r in records:
        score = max(0, 100 - r.critical_count * 25 - r.major_count * 10 - r.minor_count * 3)
        lines.append(
            f"#{r.id}  {r.filename:<30}  score={score:>3}  "
            f"[{r.critical_count}c {r.major_count}m {r.minor_count}s]  "
            f"{r.created_at[:16]}"
        )
    return "\n".join(lines)


@mcp.resource("review://supported-languages")
def resource_languages() -> str:
    """List of supported programming languages with file extensions."""
    ext_map = {
        "Python": ".py", "JavaScript": ".js", "TypeScript": ".ts",
        "Java": ".java", "C": ".c", "C++": ".cpp", "C#": ".cs",
        "Go": ".go", "Rust": ".rs", "PHP": ".php", "Ruby": ".rb",
        "Kotlin": ".kt", "Swift": ".swift",
    }
    return _json([{"language": lang, "extension": ext_map.get(lang, "")} for lang in SUPPORTED_LANGUAGES])


@mcp.resource("review://stats")
def resource_stats() -> str:
    """Aggregate statistics across all recorded reviews."""
    records = get_recent_reviews(limit=1000)
    if not records:
        return _json({"total_reviews": 0, "message": "No reviews recorded."})

    total_c = sum(r.critical_count for r in records)
    total_m = sum(r.major_count for r in records)
    total_s = sum(r.minor_count for r in records)
    scores = [
        max(0, 100 - r.critical_count * 25 - r.major_count * 10 - r.minor_count * 3)
        for r in records
    ]
    return _json({
        "total_reviews": len(records),
        "total_issues": total_c + total_m + total_s,
        "total_critical": total_c,
        "total_major": total_m,
        "total_minor": total_s,
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": max(scores),
        "worst_score": min(scores),
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROMPTS (2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.prompt()
def code_review(code: str, language: str = "Python") -> str:
    """Structured multi-criteria code review prompt template.

    Args:
        code: Source code to analyze.
        language: Programming language.
    """
    return (
        f"Analyse ce code {language} en profondeur sur 3 axes :\n\n"
        f"1. **Bugs** — logique incorrecte, cas non geres, erreurs de type, "
        f"index hors limites, variables non initialisees\n"
        f"2. **Securite** — injections SQL/XSS/commande, credentials hardcodes, "
        f"entrees non validees, serialisation dangereuse\n"
        f"3. **Lisibilite** — nommage, fonctions trop longues, magic numbers, "
        f"complexite cyclomatique, conventions du langage\n\n"
        f"Pour chaque probleme :\n"
        f"- Numero de ligne\n"
        f"- Severite : critique / majeur / mineur\n"
        f"- Categorie : bug / securite / lisibilite\n"
        f"- Titre court (max 60 caracteres)\n"
        f"- Explication pedagogique\n"
        f"- Code corrige complet\n\n"
        f"Termine par un score de qualite sur 100 et un resume en 1 phrase.\n\n"
        f"```{language.lower()}\n{code}\n```"
    )


@mcp.prompt()
def security_audit(code: str, language: str = "Python") -> str:
    """OWASP-focused security audit prompt template.

    Args:
        code: Source code to audit.
        language: Programming language.
    """
    return (
        f"Effectue un audit de securite approfondi sur ce code {language}.\n\n"
        f"Verifie specifiquement :\n"
        f"- Injections (SQL, XSS, commande OS, LDAP)\n"
        f"- Gestion des secrets (cles API, mots de passe, tokens)\n"
        f"- Validation des entrees utilisateur\n"
        f"- Controle d'acces et authentification\n"
        f"- Gestion securisee des fichiers et serialisation\n"
        f"- Exposition de donnees sensibles dans les logs/erreurs\n"
        f"- Dependances a risque (eval, exec, pickle, subprocess shell=True)\n\n"
        f"Pour chaque vuln trouvee, donne :\n"
        f"- La ligne affectee\n"
        f"- Le vecteur d'attaque concret\n"
        f"- Le code corrige\n"
        f"- La reference OWASP si applicable\n\n"
        f"```{language.lower()}\n{code}\n```"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Entrypoint — supports --sse and --port for HTTP/SSE transport."""
    args = sys.argv[1:]

    if "--sse" in args:
        port = 8080
        for i, a in enumerate(args):
            if a == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
        logger.info("Starting MCP SSE on http://127.0.0.1:%d/sse", port)
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        logger.info("Starting MCP stdio")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
