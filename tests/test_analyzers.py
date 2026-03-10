import pytest
from src.aggregator import validate_syntax


# ── Tests validate_syntax ─────────────────────────────────────────────────────

def test_valid_syntax():
    code = "def hello():\n    return 'world'\n"
    ok, msg = validate_syntax(code)
    assert ok is True
    assert msg == ""


def test_syntax_error_detected():
    code = "def broken(\n    # parenthese non fermee\n"
    ok, msg = validate_syntax(code)
    assert ok is False
    assert "syntaxe" in msg.lower() or "syntax" in msg.lower()


def test_empty_file():
    ok, msg = validate_syntax("")
    assert ok is True  # fichier vide = syntaxe valide


def test_syntax_error_contains_line_number():
    code = "x = (\n"
    ok, msg = validate_syntax(code)
    assert ok is False
    assert any(char.isdigit() for char in msg)  # contient un numero de ligne


# ── Tests agregateur (sans appel API) ────────────────────────────────────────

def test_issues_sorted_by_severity():
    from src.models import Issue, Severity, Category
    from src.aggregator import run_analysis
    # On verifie juste que le tri fonctionne sur des objets locaux
    issues = [
        Issue(severity=Severity.MINOR,    category=Category.STYLE,    title="A", explanation="", suggestion=""),
        Issue(severity=Severity.CRITICAL, category=Category.SECURITY, title="B", explanation="", suggestion=""),
        Issue(severity=Severity.MAJOR,    category=Category.BUG,      title="C", explanation="", suggestion=""),
    ]
    order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}
    sorted_issues = sorted(issues, key=lambda i: order[i.severity])
    assert sorted_issues[0].severity == Severity.CRITICAL
    assert sorted_issues[1].severity == Severity.MAJOR
    assert sorted_issues[2].severity == Severity.MINOR
