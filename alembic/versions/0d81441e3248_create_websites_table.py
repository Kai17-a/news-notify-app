"""create websites table

Revision ID: 0d81441e3248
Revises: 7489700372da
Create Date: 2025-12-18 23:41:01.942264

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0d81441e3248"
down_revision: Union[str, Sequence[str], None] = "7489700372da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS websites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            url TEXT NOT NULL,
            avatar TEXT,
            selector TEXT,
            is_active BOOLEAN DEFAULT 1,
            needs_translation BOOLEAN DEFAULT 0,
            target_webhook_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_website_active ON websites(is_active)
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_website_type ON websites(type)
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TABLE webhooks;
    """
    )
