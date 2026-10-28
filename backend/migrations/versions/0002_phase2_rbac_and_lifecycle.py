"""Phase 2 RBAC, alert official tag, and review lifecycle enhancements

Revision ID: 0002_phase2_rbac_and_lifecycle
Revises: 0001_initial_schema
Create Date: 2026-10-27 09:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_phase2_rbac_and_lifecycle'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Users: assigned_state_id
    op.add_column('users', sa.Column('assigned_state_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_state_id', 'users', 'states', ['assigned_state_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_users_assigned_state_id'), 'users', ['assigned_state_id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # 2. Alerts: is_official, created_by_user_id, updated_at
    op.add_column('alerts', sa.Column('is_official', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('alerts', sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    op.add_column('alerts', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_alerts_user_id', 'alerts', 'users', ['created_by_user_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_alerts_is_official'), 'alerts', ['is_official'], unique=False)
    op.create_index(op.f('ix_alerts_created_by_user_id'), 'alerts', ['created_by_user_id'], unique=False)

    # 3. Citizen Reports: assigned_officer_id, reopened_count, reopened_at
    op.add_column('citizen_reports', sa.Column('assigned_officer_id', sa.Integer(), nullable=True))
    op.add_column('citizen_reports', sa.Column('reopened_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('citizen_reports', sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_reports_assigned_officer', 'citizen_reports', 'users', ['assigned_officer_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_citizen_reports_assigned_officer_id'), 'citizen_reports', ['assigned_officer_id'], unique=False)

    # 4. Report Media: file_name, file_size_bytes
    op.add_column('report_media', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('report_media', sa.Column('file_size_bytes', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('report_media', 'file_size_bytes')
    op.drop_column('report_media', 'file_name')
    op.drop_constraint('fk_reports_assigned_officer', 'citizen_reports', type_='foreignkey')
    op.drop_column('citizen_reports', 'reopened_at')
    op.drop_column('citizen_reports', 'reopened_count')
    op.drop_column('citizen_reports', 'assigned_officer_id')
    op.drop_constraint('fk_alerts_user_id', 'alerts', type_='foreignkey')
    op.drop_column('alerts', 'updated_at')
    op.drop_column('alerts', 'created_by_user_id')
    op.drop_column('alerts', 'is_official')
    op.drop_constraint('fk_users_state_id', 'users', type_='foreignkey')
    op.drop_column('users', 'assigned_state_id')
