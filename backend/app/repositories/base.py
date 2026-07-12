"""Shared repository infrastructure."""

from sqlalchemy.orm import Session


class Repository:
    """Base repository that owns a database session."""

    def __init__(self, session: Session) -> None:
        self.session = session
