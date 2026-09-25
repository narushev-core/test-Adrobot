"""
Настройка логирования. `RedactSecretsFilter` вырезает API-ключ Keitaro из любых
сообщений и полей лога, чтобы он не попал в логи ни при каких обстоятельствах (NFR-13).
"""

from __future__ import annotations

import logging
from logging import LogRecord

_REDACTED = "***REDACTED***"


class RedactSecretsFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: LogRecord) -> bool:
        if not self._secrets:
            return True
        record.msg = self._redact(str(record.msg))
        if record.args:
            record.args = tuple(
                self._redact(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True

    def _redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, _REDACTED)
        return text


def configure_logging(level: str, secrets: list[str] | None = None) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    if secrets:
        handler.addFilter(RedactSecretsFilter(secrets))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
