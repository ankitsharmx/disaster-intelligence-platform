"""Initial database schema with PostGIS and Phase 1 models

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-27 08:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension on PostgreSQL if supported
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. States table
    op.create_table(
        'states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_states_id'), 'states', ['id'], unique=False)
    op.create_index(op.f('ix_states_name'), 'states', ['name'], unique=True)
    op.create_index(op.f('ix_states_code'), 'states', ['code'], unique=True)

    # 2. Districts table
    op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=True),
        sa.Column('boundary', Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=True), nullable=True),
        sa.Column('boundary_geojson', sa.JSON(), nullable=True),
        sa.Column('center_lat', sa.Float(), nullable=True),
        sa.Column('center_lon', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['state_id'], ['states.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_districts_id'), 'districts', ['id'], unique=False)
    op.create_index(op.f('ix_districts_name'), 'districts', ['name'], unique=False)
    op.create_index(op.f('ix_districts_code'), 'districts', ['code'], unique=False)
    op.create_index(op.f('ix_districts_state_id'), 'districts', ['state_id'], unique=False)

    # 3. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='citizen', nullable=False),
        sa.Column('assigned_district_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 4. Facilities table
    op.create_table(
        'facilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('coordinates', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('contact_number', sa.String(length=50), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_facilities_id'), 'facilities', ['id'], unique=False)
    op.create_index(op.f('ix_facilities_name'), 'facilities', ['name'], unique=False)
    op.create_index(op.f('ix_facilities_category'), 'facilities', ['category'], unique=False)
    op.create_index(op.f('ix_facilities_district_id'), 'facilities', ['district_id'], unique=False)

    # 5. Hazard observations
    op.create_table(
        'hazard_observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hazard_type', sa.String(length=50), nullable=False),
        sa.Column('values', sa.JSON(), nullable=False),
        sa.Column('observed_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('location', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hazard_observations_id'), 'hazard_observations', ['id'], unique=False)
    op.create_index(op.f('ix_hazard_observations_hazard_type'), 'hazard_observations', ['hazard_type'], unique=False)
    op.create_index(op.f('ix_hazard_observations_observed_time'), 'hazard_observations', ['observed_time'], unique=False)
    op.create_index(op.f('ix_hazard_observations_source'), 'hazard_observations', ['source'], unique=False)
    op.create_index(op.f('ix_hazard_observations_district_id'), 'hazard_observations', ['district_id'], unique=False)

    # 6. Data source runs
    op.create_table(
        'data_source_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('retrieval_time', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('records_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_source_runs_id'), 'data_source_runs', ['id'], unique=False)
    op.create_index(op.f('ix_data_source_runs_source'), 'data_source_runs', ['source'], unique=False)
    op.create_index(op.f('ix_data_source_runs_mode'), 'data_source_runs', ['mode'], unique=False)
    op.create_index(op.f('ix_data_source_runs_status'), 'data_source_runs', ['status'], unique=False)

    # 7. Alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('issuer', sa.String(length=100), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index(op.f('ix_alerts_type'), 'alerts', ['type'], unique=False)
    op.create_index(op.f('ix_alerts_severity'), 'alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_alerts_issuer'), 'alerts', ['issuer'], unique=False)
    op.create_index(op.f('ix_alerts_status'), 'alerts', ['status'], unique=False)
    op.create_index(op.f('ix_alerts_valid_from'), 'alerts', ['valid_from'], unique=False)
    op.create_index(op.f('ix_alerts_valid_to'), 'alerts', ['valid_to'], unique=False)

    # 8. Alert Areas
    op.create_table(
        'alert_areas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('boundary', Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
        sa.Column('boundary_geojson', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_areas_id'), 'alert_areas', ['id'], unique=False)
    op.create_index(op.f('ix_alert_areas_alert_id'), 'alert_areas', ['alert_id'], unique=False)
    op.create_index(op.f('ix_alert_areas_district_id'), 'alert_areas', ['district_id'], unique=False)

    # 9. Citizen Reports
    op.create_table(
        'citizen_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('location', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='submitted', nullable=False),
        sa.Column('confidence_score', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('is_duplicate', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_of_id'], ['citizen_reports.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_reports_id'), 'citizen_reports', ['id'], unique=False)
    op.create_index(op.f('ix_citizen_reports_type'), 'citizen_reports', ['type'], unique=False)
    op.create_index(op.f('ix_citizen_reports_status'), 'citizen_reports', ['status'], unique=False)
    op.create_index(op.f('ix_citizen_reports_user_id'), 'citizen_reports', ['user_id'], unique=False)
    op.create_index(op.f('ix_citizen_reports_district_id'), 'citizen_reports', ['district_id'], unique=False)
    op.create_index(op.f('ix_citizen_reports_created_at'), 'citizen_reports', ['created_at'], unique=False)

    # 10. Report Media
    op.create_table(
        'report_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['citizen_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_media_id'), 'report_media', ['id'], unique=False)
    op.create_index(op.f('ix_report_media_report_id'), 'report_media', ['report_id'], unique=False)

    # 11. Report Reviews
    op.create_table(
        'report_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['citizen_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_reviews_id'), 'report_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_report_reviews_report_id'), 'report_reviews', ['report_id'], unique=False)
    op.create_index(op.f('ix_report_reviews_reviewer_id'), 'report_reviews', ['reviewer_id'], unique=False)

    # 12. Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor', sa.String(length=150), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('affected_record', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_id'), 'audit_events', ['id'], unique=False)
    op.create_index(op.f('ix_audit_events_actor'), 'audit_events', ['actor'], unique=False)
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_audit_events_affected_record'), 'audit_events', ['affected_record'], unique=False)
    op.create_index(op.f('ix_audit_events_timestamp'), 'audit_events', ['timestamp'], unique=False)

    # 13. Awareness Content
    op.create_table(
        'awareness_contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hazard', sa.String(length=50), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=False),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('instructions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_awareness_contents_id'), 'awareness_contents', ['id'], unique=False)
    op.create_index(op.f('ix_awareness_contents_hazard'), 'awareness_contents', ['hazard'], unique=False)
    op.create_index(op.f('ix_awareness_contents_stage'), 'awareness_contents', ['stage'], unique=False)
    op.create_index(op.f('ix_awareness_contents_language'), 'awareness_contents', ['language'], unique=False)


def downgrade() -> None:
    op.drop_table('awareness_contents')
    op.drop_table('audit_events')
    op.drop_table('report_reviews')
    op.drop_table('report_media')
    op.drop_table('citizen_reports')
    op.drop_table('alert_areas')
    op.drop_table('alerts')
    op.drop_table('data_source_runs')
    op.drop_table('hazard_observations')
    op.drop_table('facilities')
    op.drop_table('users')
    op.drop_table('districts')
    op.drop_table('states')
