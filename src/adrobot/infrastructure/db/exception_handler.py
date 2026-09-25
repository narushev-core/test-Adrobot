from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError

_UNIQUE_VIOLATION_RE = re.compile(
    r"Key \((?P<field>[^)]+)\)=\((?P<value>.*)\) already exists\.?",
    re.IGNORECASE,
)
_FK_VIOLATION_RE = re.compile(
    r'Key \((?P<field>[^)]+)\)=\((?P<value>[^)]+)\) is not present in table "(?P<table>[^"]+)"\.?',
    re.IGNORECASE,
)
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"


class DatabaseIntegrityError(Exception):
    def __init__(self, field: str | None, value: str | None, type: str, msg: str) -> None:
        self.field = field
        self.value = value
        self.type = type
        self.msg = msg
        super().__init__(msg)


def integrity_error_handler(exc: IntegrityError) -> Exception:
    origin = getattr(exc, "orig", None)
    sqlstate = getattr(origin, "sqlstate", None)
    origin_text = str(origin) if origin is not None else str(exc)

    if sqlstate == UNIQUE_VIOLATION:
        m = _UNIQUE_VIOLATION_RE.search(origin_text)
        return DatabaseIntegrityError(
            field=m.group("field") if m else None,
            value=m.group("value") if m else None,
            type="value_error.already_exists",
            msg="Duplicate value for field",
        )

    if sqlstate == FOREIGN_KEY_VIOLATION:
        m = _FK_VIOLATION_RE.search(origin_text)
        return DatabaseIntegrityError(
            field=m.group("field") if m else None,
            value=m.group("value") if m else None,
            type="value_error.not_found",
            msg="Related record not found",
        )

    return exc
