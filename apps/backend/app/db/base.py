from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models here so Base.metadata is complete for create_all in tests and local scripts.
from app import models  # noqa: E402,F401
