"""add notification subscriptions table

Revision ID: 0003_notifications
Revises: 0002_phase2_rbac_and_lifecycle
Create Date: 2026-10-28 07:18:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_notifications'
down_revision: Union[str, Sequence[str], None] = '0002_phase2_rbac_and_lifecycle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if notification_subscriptions table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'notification_subscriptions' not in tables:
        op.create_table(
            'notification_subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.Text(), nullable=False),
            sa.Column('p256dh', sa.String(length=255), nullable=True),
            sa.Column('auth', sa.String(length=255), nullable=True),
            sa.Column('district_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_notification_subscriptions_id'), 'notification_subscriptions', ['id'], unique=False)
        op.create_index(op.f('ix_notification_subscriptions_endpoint'), 'notification_subscriptions', ['endpoint'], unique=True)
        op.create_index(op.f('ix_notification_subscriptions_district_id'), 'notification_subscriptions', ['district_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notification_subscriptions')
