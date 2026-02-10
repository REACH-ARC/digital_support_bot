"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-02-10 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('user_type', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id'),
        sa.CheckConstraint("user_type IN ('customer', 'agent')", name='users_user_type_check')
    )
    op.create_index('ix_users_telegram_user_id', 'users', ['telegram_user_id'], unique=True)

    # 2. Agents Table
    op.create_table(
        'agents',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='agent', nullable=False),
        sa.Column('is_online', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.CheckConstraint("role IN ('admin', 'agent')", name='agents_role_check')
    )

    # 3. Conversations Table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('locked_by_agent', sa.UUID(), nullable=True),
        sa.Column('topic_id', sa.BigInteger(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['locked_by_agent'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('open', 'closed')", name='conversations_status_check')
    )
    op.create_index('ix_conversations_customer_id', 'conversations', ['customer_id'], unique=False)
    op.create_index('ix_conversations_status', 'conversations', ['status'], unique=False)
    op.create_index('ix_conversations_topic_id', 'conversations', ['topic_id'], unique=False)

    # 4. Messages Table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=True),
        sa.Column('sender_type', sa.String(length=10), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=True),
        sa.Column('message_type', sa.String(length=20), server_default='text', nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('telegram_message_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("sender_type IN ('customer', 'agent', 'bot')", name='messages_sender_type_check')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'], unique=False)
    op.create_index('ix_messages_created_at', 'messages', ['created_at'], unique=False)

    # 5. Conversation Events Table
    op.create_table(
        'conversation_events',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=30), nullable=True),
        sa.Column('event_by', sa.UUID(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['event_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('conversation_events')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('agents')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS pgcrypto')
