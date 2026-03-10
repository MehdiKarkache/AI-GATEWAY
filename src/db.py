from datetime import datetime
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
import json

DATABASE_URL = "sqlite:///./reviews.db"
engine = create_engine(DATABASE_URL)


class ReviewRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    issues_json: str        # JSON serialize de la liste d'issues
    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int


def init_db():
    SQLModel.metadata.create_all(engine)


def save_review(filename: str, issues: list) -> int:
    """Sauvegarde un rapport d'analyse et retourne son ID."""
    from src.models import Severity
    record = ReviewRecord(
        filename=filename,
        issues_json=json.dumps([i.model_dump() for i in issues]),
        total_issues=len(issues),
        critical_count=sum(1 for i in issues if i.severity == Severity.CRITICAL),
        major_count=sum(1 for i in issues if i.severity == Severity.MAJOR),
        minor_count=sum(1 for i in issues if i.severity == Severity.MINOR),
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


def get_recent_reviews(limit: int = 10) -> list[ReviewRecord]:
    """Retourne les derniers rapports enregistres."""
    with Session(engine) as session:
        statement = select(ReviewRecord).order_by(ReviewRecord.id.desc()).limit(limit)
        return session.exec(statement).all()


def delete_review(record_id: int) -> None:
    """Supprime un rapport par son ID."""
    with Session(engine) as session:
        record = session.get(ReviewRecord, record_id)
        if record:
            session.delete(record)
            session.commit()


def delete_all_reviews() -> None:
    """Supprime tous les rapports."""
    with Session(engine) as session:
        for record in session.exec(select(ReviewRecord)).all():
            session.delete(record)
        session.commit()
