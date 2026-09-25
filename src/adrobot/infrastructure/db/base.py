from __future__ import annotations

import re
from typing import Any

from sqlalchemy import MetaData, inspect
from sqlalchemy.orm import DeclarativeBase, declared_attr

from adrobot.infrastructure.db.mixins import CRUDMixin


def camel_case_to_snake_case(name: str) -> str:
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name).lower()


class Base(CRUDMixin, DeclarativeBase):
    __abstract__ = True

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return camel_case_to_snake_case(cls.__name__)

    @classmethod
    def get_entity_name(cls) -> str:
        return cls.__tablename__.capitalize()

    def model_to_dict(self) -> dict[str, Any]:
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
