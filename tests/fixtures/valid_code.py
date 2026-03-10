def add(a: int, b: int) -> int:
    """Retourne la somme de a et b."""
    return a + b


def greet(name: str) -> str:
    """Retourne un message de salutation."""
    if not name:
        raise ValueError("Le nom ne peut pas etre vide.")
    return f"Bonjour, {name} !"
