"""Add conversation messages and update sessions

Revision ID: 99921436bac3
Revises: 
Create Date: 2025-07-25 18:33:01.873818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99921436bac3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # Create sessions table first
    op.create_table('sessions',
    sa.Column('session_id', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('meta_data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_sessions_session_id'), 'sessions', ['session_id'], unique=False)
    
    op.create_table('conversation_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('message_metadata', sa.JSON(), nullable=True),
    sa.Column('message_order', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_messages_order', 'conversation_messages', ['session_id', 'message_order'], unique=False)
    op.create_index('idx_conversation_messages_session', 'conversation_messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_id'), 'conversation_messages', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_session_id'), 'conversation_messages', ['session_id'], unique=False)
    op.add_column('sessions', sa.Column('conversation_status', sa.String(length=50), nullable=True))
    op.add_column('sessions', sa.Column('message_count', sa.Integer(), nullable=True))
    op.add_column('sessions', sa.Column('last_message_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Dowrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sessions', 'last_message_at')
    op.drop_column('sessions', 'message_count')
    op.drop_column('sessions', 'conversation_status')
    op.drop_index(op.f('ix_conversation_messages_session_id'), table_name='conversation_messages')
    op.drop_index(op.f('ix_conversation_messages_id'), table_name='conversation_messages')
    op.drop_index('idx_conversation_messages_session', table_name='conversation_messages')
    op.drop_index('idx_conversation_messages_order', table_name='conversation_messages')
    op.drop_table('conversation_messages')
    op.drop_index(op.f('ix_sessions_session_id'), table_name='sessions')
    op.drop_table('sessions')
    # ### end Alembic commands ###
