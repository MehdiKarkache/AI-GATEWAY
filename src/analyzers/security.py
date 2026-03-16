from openai import AsyncOpenAI
from src.models import AnalysisResult
from src.analyzers import extract_json, llm_call_with_retry

SYSTEM_PROMPT = """
Tu es un expert en securite logicielle specialise dans la revue de code.
Tu analyses UNIQUEMENT les problemes de securite : injections (SQL, commandes),
credentials hardcodes, cles API exposees, entrees utilisateur non validees,
serialisation dangereuse, surface d'attaque excessive, etc.

Tu ne commentes PAS les bugs logiques ni le style. Ces aspects sont traites separement.

Niveaux de severite :
- critique : faille exploitable directement (injection SQL, credential expose...)
- majeur   : risque de securite significatif necessitant une correction rapide
- mineur   : mauvaise pratique de securite, risque faible dans le contexte actuel
"""

JSON_EXAMPLE = '''{
  "issues": [
    {
      "line_number": 5,
      "severity": "critique",
      "category": "securite",
      "title": "Titre court",
      "explanation": "Explication du probleme.",
      "suggestion": "code_corrige()"
    }
  ],
  "summary": "Resume en une phrase."
}'''


async def analyze_security(code: str, client: AsyncOpenAI, language: str = "Python") -> AnalysisResult:
    prompt = (
        f"{SYSTEM_PROMPT.strip()}\n\n"
        f"Code {language} a analyser :\n```{language.lower()}\n{code}\n```\n\n"
        f"Reponds avec UNIQUEMENT un objet JSON (sans texte avant ni apres) dans ce format :\n{JSON_EXAMPLE}\n\n"
        f"Valeurs valides pour severity: \"critique\", \"majeur\", \"mineur\"\n"
        f"Valeurs valides pour category: \"securite\"\n"
        f"Si aucun probleme : {{\"issues\": [], \"summary\": \"Aucun probleme de securite detecte.\"}}"
    )
    raw = await llm_call_with_retry(client, prompt)
    try:
        return AnalysisResult.model_validate_json(extract_json(raw))
    except Exception:
        return AnalysisResult(issues=[], summary="Erreur de parsing (securite).")

