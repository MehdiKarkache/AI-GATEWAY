"""
CLI MCP — Code Review Assistant
================================
Command-line interface for the MCP server.

Code Intelligence:
  python -m src.mcp_cli review <file> [--lang Go]        # full code review
  python -m src.mcp_cli fix <file> [--lang Go]           # auto-fix code
  python -m src.mcp_cli explain <file> [--detail medium]  # explain code
  python -m src.mcp_cli generate-tests <file> [--framework pytest] # generate tests
  python -m src.mcp_cli syntax <file>                    # validate syntax

GitHub Integration:
  python -m src.mcp_cli github-repo <owner> <repo>       # get repo info
  python -m src.mcp_cli github-file <owner> <repo> <path> # get file
  python -m src.mcp_cli github-issues <owner> <repo>     # list issues
  python -m src.mcp_cli github-search <query>            # search repos

Utility:
  python -m src.mcp_cli tools                            # list MCP tools
  python -m src.mcp_cli resources                        # list MCP resources
  python -m src.mcp_cli prompts                          # list MCP prompts
  python -m src.mcp_cli history [--limit 5]              # review history
  python -m src.mcp_cli stats                            # global statistics
  python -m src.mcp_cli langs                            # supported languages
"""

import argparse
import asyncio
import json
import os
import sys

if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_client import MCPClient


EXT_TO_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
    ".c": "C", ".cpp": "C++", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".php": "PHP", ".rb": "Ruby", ".kt": "Kotlin", ".swift": "Swift",
}


def _detect_language(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return EXT_TO_LANG.get(ext, "Python")


def _pretty(data) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


# ── Introspection ─────────────────────────────────────────────────────────────

async def cmd_tools(args):
    async with MCPClient() as c:
        tools = await c.list_tools()
        print(f"\n  {len(tools)} tool(s) available:\n")
        for t in tools:
            print(f"  - {t['name']:<25} {t['description'][:80]}")
        print()


async def cmd_resources(args):
    async with MCPClient() as c:
        resources = await c.list_resources()
        print(f"\n  {len(resources)} resource(s):\n")
        for r in resources:
            print(f"  - {r['uri']:<35} {r.get('description', '')[:60]}")
        print()


async def cmd_prompts(args):
    async with MCPClient() as c:
        prompts = await c.list_prompts()
        print(f"\n  {len(prompts)} prompt(s):\n")
        for p in prompts:
            print(f"  - {p['name']:<25} {p.get('description', '')[:60]}")
        print()


# ── Code Intelligence ─────────────────────────────────────────────────────────

async def cmd_review(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"  Error: file not found — {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    language = args.lang or _detect_language(filepath)
    filename = os.path.basename(filepath)

    print(f"\n  Reviewing {filename} ({language}, {len(code.splitlines())} lines)...")

    async with MCPClient() as c:
        result = await c.review_code(code, language, filename)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    score = result["score"]
    bar = "█" * (score // 5) + "░" * (20 - score // 5)
    print(f"\n  Score: {score}/100  [{bar}]")
    print(f"  Issues: {result['critical']} critical, {result['major']} major, {result['minor']} minor")
    print(f"  Report #: {result.get('review_id', '?')}\n")

    for idx, issue in enumerate(result.get("issues", []), 1):
        sev = issue["severity"].upper()
        line = issue.get("line") or "—"
        print(f"  [{sev:<9}] #{idx:02d}  L{line}  {issue['title']}")
    print()


async def cmd_fix(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"  Error: file not found — {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    language = args.lang or _detect_language(filepath)
    filename = os.path.basename(filepath)

    print(f"\n  Fixing {filename} ({language}, {len(code.splitlines())} lines)...")

    async with MCPClient() as c:
        result = await c.fix_code(code, language)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    before = result.get("original_score", "?")
    after = result.get("fixed_score", "?")
    changes = result.get("changes", [])
    print(f"\n  Score: {before} → {after}")
    print(f"  {len(changes)} fix(es) applied:\n")
    for idx, ch in enumerate(changes, 1):
        print(f"  {idx}. {ch}")

    fixed = result.get("fixed_code", "")
    if fixed:
        out_path = os.path.splitext(filepath)[0] + "_fixed" + os.path.splitext(filepath)[1]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fixed)
        print(f"\n  Fixed file written: {out_path}\n")


async def cmd_explain(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"  Error: file not found — {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    language = args.lang or _detect_language(filepath)
    detail = args.detail or "medium"

    print(f"\n  Explaining {os.path.basename(filepath)} ({language}, detail={detail})...\n")

    async with MCPClient() as c:
        result = await c.explain_code(code, language, detail)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"  SUMMARY:")
    print(f"  {result.get('summary', '')}\n")

    steps = result.get("step_by_step", [])
    if steps:
        print(f"  STEP BY STEP:")
        for idx, step in enumerate(steps, 1):
            print(f"  {idx}. {step}")
        print()

    complexity = result.get("complexity", "")
    if complexity:
        print(f"  Complexity: {complexity}")

    concepts = result.get("key_concepts", [])
    if concepts:
        print(f"  Key concepts: {', '.join(concepts)}")
    print()


async def cmd_generate_tests(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"  Error: file not found — {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    language = args.lang or _detect_language(filepath)
    framework = args.framework or "auto"

    print(f"\n  Generating tests for {os.path.basename(filepath)} ({language}, framework={framework})...")

    async with MCPClient() as c:
        result = await c.generate_tests(code, language, framework)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result.get('test_count', 0)} test(s) generated with {result.get('framework', 'auto')}")
    print(f"  Coverage: {result.get('coverage_summary', '')}\n")

    test_code = result.get("test_code", "")
    if test_code:
        ext = os.path.splitext(filepath)[1]
        out_path = os.path.splitext(filepath)[0] + "_test" + ext
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(test_code)
        print(f"  Test file written: {out_path}")
        print(f"\n--- Generated Tests ---\n{test_code}\n")


async def cmd_syntax(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"  Error: file not found — {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    language = args.lang or _detect_language(filepath)

    async with MCPClient() as c:
        result = await c.check_syntax(code, language)

    if result["valid"]:
        print(f"\n  Syntax OK ({language})")
    else:
        print(f"\n  Syntax error: {result['error']}")


# ── GitHub Integration ────────────────────────────────────────────────────────

async def cmd_github_repo(args):
    print(f"\n  Fetching {args.owner}/{args.repo}...")

    async with MCPClient() as c:
        result = await c.github_get_repo(args.owner, args.repo)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result.get('full_name', '')}")
    print(f"  {result.get('description', '')}\n")
    print(f"  {'Stars':<15}: {result.get('stars', 0):,}")
    print(f"  {'Forks':<15}: {result.get('forks', 0):,}")
    print(f"  {'Open issues':<15}: {result.get('open_issues', 0):,}")
    print(f"  {'Language':<15}: {result.get('language', '—')}")
    print(f"  {'License':<15}: {result.get('license', '—')}")
    print(f"  {'Default branch':<15}: {result.get('default_branch', '—')}")
    print(f"  {'Topics':<15}: {', '.join(result.get('topics', []))}")
    print(f"  {'URL':<15}: {result.get('html_url', '')}\n")


async def cmd_github_file(args):
    print(f"\n  Fetching {args.owner}/{args.repo}/{args.path}...")

    async with MCPClient() as c:
        result = await c.github_get_file(args.owner, args.repo, args.path)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result.get('filename', '')} ({result.get('size', 0)} bytes)")
    print(f"  SHA: {(result.get('sha', ''))[:7]}\n")
    print("--- File Contents ---")
    print(result.get("content", ""))


async def cmd_github_issues(args):
    state = args.state or "open"
    print(f"\n  Fetching {state} issues from {args.owner}/{args.repo}...")

    async with MCPClient() as c:
        result = await c.github_list_issues(args.owner, args.repo, state, args.limit)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result.get('count', 0)} issue(s):\n")
    for issue in result.get("issues", []):
        state_icon = "●" if issue.get("state") == "open" else "○"
        labels = ", ".join(issue.get("labels", []))
        labels_str = f" [{labels}]" if labels else ""
        print(f"  {state_icon} #{issue.get('number',''):<5} {issue.get('title', '')[:60]}{labels_str}")
    print()


async def cmd_github_search(args):
    query = " ".join(args.query)
    print(f"\n  Searching GitHub: {query}...")

    async with MCPClient() as c:
        result = await c.github_search_repos(query, 5)

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"\n  {result.get('total_count', 0):,} total results:\n")
    for r in result.get("repos", []):
        print(f"  ★ {r.get('stars',0):>6,}  {r.get('full_name',''):<40} {r.get('language', '')}")
        if r.get("description"):
            print(f"           {r['description'][:80]}")
    print()


# ── Utility ───────────────────────────────────────────────────────────────────

async def cmd_history(args):
    async with MCPClient() as c:
        result = await c.get_history(args.limit)

    if not result["reviews"]:
        print("\n  No reviews recorded.\n")
        return

    print(f"\n  {result['count']} report(s):\n")
    for r in result["reviews"]:
        score = max(0, 100 - r["critical"] * 25 - r["major"] * 10 - r["minor"] * 3)
        print(f"  #{r['id']:<4}  {r['filename']:<30}  score={score:>3}  "
              f"[{r['critical']}c {r['major']}m {r['minor']}s]  {r['created_at'][:16]}")
    print()


async def cmd_stats(args):
    async with MCPClient() as c:
        result = await c.get_stats()

    if result.get("total_reviews", 0) == 0:
        print("\n  No reviews recorded.\n")
        return

    print(f"\n  Global Statistics:")
    print(f"  {'Total reviews':<20}: {result['total_reviews']}")
    print(f"  {'Total issues':<20}: {result['total_issues']}")
    print(f"  {'Critical':<20}: {result['total_critical']}")
    print(f"  {'Major':<20}: {result['total_major']}")
    print(f"  {'Minor':<20}: {result['total_minor']}")
    print(f"  {'Average score':<20}: {result['average_score']}/100")
    print(f"  {'Best score':<20}: {result['best_score']}/100")
    print(f"  {'Worst score':<20}: {result['worst_score']}/100\n")


async def cmd_langs(args):
    async with MCPClient() as c:
        result = await c.get_languages()

    print(f"\n  {len(result)} supported language(s):\n")
    for item in result:
        print(f"  - {item['language']:<15} {item['extension']}")
    print()


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp_cli",
        description="CLI for Code Review Assistant MCP Server",
    )
    sub = parser.add_subparsers(dest="command", help="Command to execute")

    # Introspection
    sub.add_parser("tools", help="List MCP tools")
    sub.add_parser("resources", help="List MCP resources")
    sub.add_parser("prompts", help="List MCP prompts")

    # Code Intelligence
    p_review = sub.add_parser("review", help="Full code review")
    p_review.add_argument("file", help="Source file path")
    p_review.add_argument("--lang", help="Language (auto-detected if omitted)")

    p_fix = sub.add_parser("fix", help="Auto-fix code")
    p_fix.add_argument("file", help="Source file path")
    p_fix.add_argument("--lang", help="Language (auto-detected if omitted)")

    p_explain = sub.add_parser("explain", help="Explain code in plain language")
    p_explain.add_argument("file", help="Source file path")
    p_explain.add_argument("--lang", help="Language (auto-detected if omitted)")
    p_explain.add_argument("--detail", choices=["brief", "medium", "detailed"], default="medium", help="Detail level")

    p_gentests = sub.add_parser("generate-tests", help="Generate unit tests")
    p_gentests.add_argument("file", help="Source file path")
    p_gentests.add_argument("--lang", help="Language (auto-detected if omitted)")
    p_gentests.add_argument("--framework", default="auto", help="Test framework (auto, pytest, jest, junit, etc.)")

    p_syntax = sub.add_parser("syntax", help="Validate syntax")
    p_syntax.add_argument("file", help="Source file path")
    p_syntax.add_argument("--lang", help="Language")

    # GitHub Integration
    p_gh_repo = sub.add_parser("github-repo", help="Get GitHub repository info")
    p_gh_repo.add_argument("owner", help="Repository owner (e.g. facebook)")
    p_gh_repo.add_argument("repo", help="Repository name (e.g. react)")

    p_gh_file = sub.add_parser("github-file", help="Get file from GitHub repo")
    p_gh_file.add_argument("owner", help="Repository owner")
    p_gh_file.add_argument("repo", help="Repository name")
    p_gh_file.add_argument("path", help="File path (e.g. src/main.ts)")

    p_gh_issues = sub.add_parser("github-issues", help="List GitHub issues")
    p_gh_issues.add_argument("owner", help="Repository owner")
    p_gh_issues.add_argument("repo", help="Repository name")
    p_gh_issues.add_argument("--state", choices=["open", "closed", "all"], default="open")
    p_gh_issues.add_argument("--limit", type=int, default=10)

    p_gh_search = sub.add_parser("github-search", help="Search GitHub repositories")
    p_gh_search.add_argument("query", nargs="+", help="Search query")

    # Utility
    p_history = sub.add_parser("history", help="Review history")
    p_history.add_argument("--limit", type=int, default=10)

    sub.add_parser("stats", help="Global statistics")
    sub.add_parser("langs", help="Supported languages")

    return parser


COMMANDS = {
    "tools": cmd_tools,
    "resources": cmd_resources,
    "prompts": cmd_prompts,
    "review": cmd_review,
    "fix": cmd_fix,
    "explain": cmd_explain,
    "generate-tests": cmd_generate_tests,
    "syntax": cmd_syntax,
    "github-repo": cmd_github_repo,
    "github-file": cmd_github_file,
    "github-issues": cmd_github_issues,
    "github-search": cmd_github_search,
    "history": cmd_history,
    "stats": cmd_stats,
    "langs": cmd_langs,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handler = COMMANDS.get(args.command)
    if not handler:
        parser.print_help()
        return

    asyncio.run(handler(args))


if __name__ == "__main__":
    main()
