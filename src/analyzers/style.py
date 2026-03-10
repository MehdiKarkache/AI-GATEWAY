from openai import AsyncOpenAI
from src.models import AnalysisResult
from src.analyzers import extract_json

SYSTEM_PROMPT = """
Tu es un expert en qualite de code specialise dans la lisibilite et la maintenabilite.
Tu analyses UNIQUEMENT les problemes de lisibilite : nommage peu clair, fonctions trop longues,
absence de docstrings sur des fonctions publiques complexes, code duplique, magic numbers,
complexite excessive, non-respect des conventions PEP 8 importantes.

Tu ne commentes PAS les bugs ni la securite. Ces aspects sont traites separement.

Niveaux de severite :
- critique : code incomprehensible qui bloque la maintenance
- majeur   : probleme de lisibilite significatif qui gene la comprehension
- mineur   : amelioration cosmetique ou de style sans impact fonctionnel
"""

JSON_EXAMPLE = '''{
  "issues": [
    {
      "line_number": 5,
      "severity": "mineur",
      "category": "lisibilite",
      "title": "Titre court",
      "explanation": "Explication du probleme.",
      "suggestion": "code_corrige()"
    }
  ],
  "summary": "Resume en une phrase."
}'''


async def analyze_style(code: str, client: AsyncOpenAI, language: str = "Python") -> AnalysisResult:
    prompt = (
        f"{SYSTEM_PROMPT.strip()}\n\n"
        f"Code {language} a analyser :\n```{language.lower()}\n{code}\n```\n\n"
        f"Reponds avec UNIQUEMENT un objet JSON (sans texte avant ni apres) dans ce format :\n{JSON_EXAMPLE}\n\n"
        f"Valeurs valides pour severity: \"critique\", \"majeur\", \"mineur\"\n"
        f"Valeurs valides pour category: \"lisibilite\"\n"
        f"Si aucun probleme : {{\"issues\": [], \"summary\": \"Code lisible, aucun probleme majeur detecte.\"}}"
    )
    response = await client.chat.completions.create(
        model="google/gemma-3-4b-it:free",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content
    try:
        return AnalysisResult.model_validate_json(extract_json(raw))
    except Exception:
        return AnalysisResult(issues=[], summary="Erreur de parsing (style).")

