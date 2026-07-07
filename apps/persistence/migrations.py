from sqlalchemy import Engine

from apps.persistence.models import Base


def run_migrations(engine: Engine) -> None:
    Base.metadata.create_all(engine)
