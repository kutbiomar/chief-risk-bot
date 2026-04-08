from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.database import get_db_session


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_current_user() -> None:
    raise NotImplementedError("Authentication dependencies are not implemented yet.")
