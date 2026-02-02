"""Create articles table.

Revision ID: 1c877616caaa
Revises:
Create Date: 2025-12-18 23:38:59.561323

"""  # noqa: INP001

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c877616caaa"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            site_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hash ON articles(hash);
    """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_site_created ON articles(site_name, created_at)
    """,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TABLE articles;
    """,
    )
    op.execute(
        """
    DROP INDEX IF EXISTS idx_hash;
    """,
    )
    op.execute(
        """
    DROP INDEX IF EXISTS idx_site_created;
    """,
    )
