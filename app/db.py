from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings


class Base(DeclarativeBase):
	pass


engine = create_engine(settings.database_url, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
	from app import models  # noqa: F401  Ensure models are imported
	Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
	session: Session = SessionLocal()
	try:
		yield session
		session.commit()
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()


