import asyncio
import ast
import json
import os
from openai import AsyncOpenAI
from src.analyzers import extract_json, llm_call_with_retry
from src.models import Issue, Severity, AnalysisResult

# ── Combined prompt — 1 API call instead of 3 ────────────────────────────────

_COMBINED_PROMPT = """Tu es un expert en revue de code. Analyse le code suivant sur TROIS axes :

1. **Bugs** : logique incorrecte, cas non geres, erreurs de type, index hors limites, variables non initialisees
2. **Securite** : injections, credentials hardcodes, entrees non validees, failles exploitables
3. **Lisibilite** : nommage peu clair, fonctions trop longues, code duplique, magic numbers, non-respect des conventions

Niveaux de severite :
- critique : crash en production / faille exploitable / code incomprehensible
- majeur   : bug probable / risque significatif / gene la comprehension
- mineur   : bug potentiel faible / mauvaise pratique / amelioration cosmetique

Reponds avec UNIQUEMENT un objet JSON (sans texte avant ni apres) :
{json_example}

Valeurs valides pour severity: "critique", "majeur", "mineur"
Valeurs valides pour category: "bug", "securite", "lisibilite"
Si aucun probleme : {{"issues": [], "summary": "Aucun probleme detecte."}}"""

_JSON_EXAMPLE = '''{
  "issues": [
    {
      "line_number": 5,
      "severity": "majeur",
      "category": "bug",
      "title": "Titre court",
      "explanation": "Explication du probleme.",
      "suggestion": "code_corrige()"
    }
  ],
  "summary": "Resume global en une phrase."
}'''


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


async def run_analysis(code: str, language: str = "Python", progress_callback=None) -> list[Issue]:
    """Analyse complete en UN SEUL appel API (bugs + securite + lisibilite)."""
    client = _make_client()

    if progress_callback:
        progress_callback("Sending code for analysis…")

    prompt = (
        _COMBINED_PROMPT.format(json_example=_JSON_EXAMPLE) + "\n\n"
        f"Code {language} a analyser :\n```{language.lower()}\n{code}\n```"
    )

    raw = await llm_call_with_retry(client, prompt)

    if progress_callback:
        progress_callback("Parsing results…")

    try:
        result = AnalysisResult.model_validate_json(extract_json(raw))
        all_issues = result.issues
    except Exception:
        all_issues = []

    severity_order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}
    all_issues.sort(key=lambda i: severity_order[i.severity])

    return all_issues

