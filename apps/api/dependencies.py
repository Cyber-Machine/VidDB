from collections.abc import Iterator

from sqlalchemy.orm import Session

from apps.persistence.database import create_database_engine, create_session_factory

engine = create_database_engine()
SessionFactory = create_session_factory(engine)


def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session
