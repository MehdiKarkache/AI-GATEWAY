from openai import AsyncOpenAI
from src.models import AnalysisResult
from src.analyzers import extract_json, llm_call_with_retry

SYSTEM_PROMPT = """
Tu es un expert en revue de code specialise dans la detection de BUGS.
Tu analyses UNIQUEMENT les bugs potentiels : logique incorrecte, cas non geres,
erreurs de type, acces a des variables non initialisees, index hors limites, etc.

Tu ne commentes PAS la securite ni le style. Ces aspects sont traites separement.

Niveaux de severite :
- critique : peut causer un crash en production ou une perte de donnees
- majeur   : bug probable qui affecte le comportement attendu
- mineur   : bug potentiel peu probable ou impact faible
"""

JSON_EXAMPLE = '''{
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
  "summary": "Resume en une phrase."
}'''


async def analyze_bugs(code: str, client: AsyncOpenAI, language: str = "Python") -> AnalysisResult:
    prompt = (
        f"{SYSTEM_PROMPT.strip()}\n\n"
        f"Code {language} a analyser :\n```{language.lower()}\n{code}\n```\n\n"
        f"Reponds avec UNIQUEMENT un objet JSON (sans texte avant ni apres) dans ce format :\n{JSON_EXAMPLE}\n\n"
        f"Valeurs valides pour severity: \"critique\", \"majeur\", \"mineur\"\n"
        f"Valeurs valides pour category: \"bug\"\n"
        f"Si aucun bug : {{\"issues\": [], \"summary\": \"Aucun bug detecte.\"}}"
    )
    raw = await llm_call_with_retry(client, prompt)
    try:
        return AnalysisResult.model_validate_json(extract_json(raw))
    except Exception:
        return AnalysisResult(issues=[], summary="Erreur de parsing (bugs).")

