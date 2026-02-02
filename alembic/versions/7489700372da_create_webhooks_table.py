"""Create webhooks table.

Revision ID: 7489700372da
Revises: 1c877616caaa
Create Date: 2025-12-18 23:40:13.132455

"""  # noqa: INP001

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7489700372da"
down_revision: str | Sequence[str] | None = "1c877616caaa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            endpoint TEXT NOT NULL,
            service_type TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_webhook_active ON webhooks(is_active)
    """,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TABLE webhooks;
    """,
    )
    op.execute(
        """
    DROP INDEX IF EXISTS idx_webhook_active;
    """,
    )
