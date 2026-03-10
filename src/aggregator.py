import asyncio
import ast
import os
from openai import AsyncOpenAI
from src.analyzers.bugs import analyze_bugs
from src.analyzers.security import analyze_security
from src.analyzers.style import analyze_style
from src.models import Issue, Severity


def validate_syntax(code: str, language: str = "Python") -> tuple[bool, str]:
    """Valide la syntaxe. Seul Python est verifie via ast."""
    if language != "Python":
        return True, ""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Erreur de syntaxe ligne {e.lineno} : {e.msg}"


def _make_client() -> AsyncOpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY manquante. Verifie ton fichier .env.")
    return AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


async def run_analysis(code: str, language: str = "Python") -> list[Issue]:
    """Lance les 3 analyses et retourne les problemes tries par severite."""
    client = _make_client()

    bugs_result, security_result, style_result = await asyncio.gather(
        analyze_bugs(code, client, language),
        analyze_security(code, client, language),
        analyze_style(code, client, language),
    )

    all_issues: list[Issue] = (
        bugs_result.issues + security_result.issues + style_result.issues
    )

    severity_order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}
    all_issues.sort(key=lambda i: severity_order[i.severity])

    return all_issues

