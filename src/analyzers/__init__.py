import asyncio
import re

from openai import AsyncOpenAI


async def llm_call_with_retry(client: AsyncOpenAI, prompt: str, max_retries: int = 2) -> str:
    """LLM call with short backoff on rate-limit (429) errors."""
    last_error = None
    for attempt in range(max_retries):
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
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
        except Exception as e:
            last_error = str(e)
            err_str = last_error.lower()
            is_rate_limit = "rate" in err_str or "429" in err_str or "limit" in err_str
            if is_rate_limit and attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                raise
    raise RuntimeError(last_error or "LLM call failed after retries")


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
