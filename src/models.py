from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    MINOR = "mineur"
    MAJOR = "majeur"
    CRITICAL = "critique"


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "securite"
    STYLE = "lisibilite"


class Issue(BaseModel):
    line_number: Optional[int] = None   # None si le probleme est global
    severity: Severity
    category: Category
    title: str                          # Titre court (<= 60 chars)
    explanation: str                    # Explication pedagogique
    suggestion: str                     # Code corrige fonctionnel


class AnalysisResult(BaseModel):
    issues: list[Issue]
    summary: str                        # Resume en 1 phrase
