"""rename constraints to Base.metadata naming_convention

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = [
    ("keitaro_groups", "keitaro_groups_pkey", "pk_keitaro_groups"),
    ("campaigns", "campaigns_pkey", "pk_campaigns"),
    ("campaigns", "campaigns_alias_key", "uq_campaigns_alias"),
    ("operations", "operations_pkey", "pk_operations"),
    ("outbox", "outbox_pkey", "pk_outbox"),
    ("processed_events", "processed_events_pkey", "pk_processed_events"),
]


def _rename_if_exists(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = '"{table}"'::regclass AND conname = '{old}'
            ) THEN
                ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}";
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for table, old, new in _RENAMES:
        _rename_if_exists(table, old, new)


def downgrade() -> None:
    pass
