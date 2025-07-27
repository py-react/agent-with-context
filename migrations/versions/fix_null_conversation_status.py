"""fix_null_conversation_status

Revision ID: fix_null_conversation_status
Revises: 99921436bac3
Create Date: 2025-07-27 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_null_conversation_status'
down_revision: Union[str, Sequence[str], None] = '99921436bac3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix NULL conversation_status values."""
    # Update NULL conversation_status values to 'idle'
    op.execute("UPDATE sessions SET conversation_status = 'idle' WHERE conversation_status IS NULL")
    
    # Set default value for conversation_status column
    op.execute("ALTER TABLE sessions ALTER COLUMN conversation_status SET DEFAULT 'idle'")
    
    # Make conversation_status NOT NULL
    op.execute("ALTER TABLE sessions ALTER COLUMN conversation_status SET NOT NULL")


def downgrade() -> None:
    """Revert the changes."""
    # Allow NULL values again
    op.execute("ALTER TABLE sessions ALTER COLUMN conversation_status DROP NOT NULL")
    
    # Remove default value
    op.execute("ALTER TABLE sessions ALTER COLUMN conversation_status DROP DEFAULT") 