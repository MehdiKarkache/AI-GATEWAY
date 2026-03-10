import re


def extract_json(text: str) -> str:
    """Extrait le premier objet JSON complet d'une réponse LLM."""
    # Cherche d'abord un bloc ```json ... ```
    m = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if m:
        return m.group(1)
    # Sinon trouve le { ... } le plus externe en comptant les accolades
    start = text.find('{')
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]
