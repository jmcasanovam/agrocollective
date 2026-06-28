"""schema_v2_reforma_completa

Revision ID: c7d8e9f0a1b2
Revises: 6fc335ef3267
Create Date: 2026-06-27

Estado real v1 (tras las 8 migraciones previas):
  users    — id, email, password_hash, region (texto), is_active, created_at, updated_at
  farms    — id, user_id, name(255 NOT NULL), latitude, longitude, province, area_ha(NOT NULL), is_active, created_at, updated_at
  plots    — id, farm_id, crop_type(100 NOT NULL), soil_type(100 NOT NULL), area_ha(NOT NULL), depth_cm, province, name(100 NOT NULL), is_active, created_at, updated_at
  sensors  — id, plot_id, esp32_id(100), sensor_type(50), depth_cm, status(20 NOT NULL), battery_mv, last_reading, is_active, created_at, updated_at

Cambios v1→v2:
  - Crea: regions, crops, soils, irrigation_records, harvests
  - users: elimina region (texto)
  - farms: añade region_id FK, elimina province e is_active
  - plots: añade crop_id/soil_id FK, hash_plot, management_profile; elimina crop_type/soil_type/depth_cm/province/is_active
  - sensors→devices: renombra tabla; esp32_id→code; elimina sensor_type/depth_cm/status/battery_mv/last_reading
  NOTE: anomalies, recommendations, cluster_* excluidos (sprint posterior)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = '6fc335ef3267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_uuid_default = sa.text('gen_random_uuid()')
_ts_default = sa.text('now()')


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Nuevas tablas de catálogo: regions, crops, soils                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        'regions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=_uuid_default),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('siar_station_code', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_regions_code'),
    )

    op.create_table(
        'crops',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=_uuid_default),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_crops_name'),
    )

    op.create_table(
        'soils',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=_uuid_default),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_soils_name'),
    )

    # ------------------------------------------------------------------ #
    # 2. users: eliminar columna region (texto)                           #
    # ------------------------------------------------------------------ #
    op.drop_column('users', 'region')

    # ------------------------------------------------------------------ #
    # 3. farms: añadir region_id FK; eliminar province e is_active        #
    # ------------------------------------------------------------------ #
    op.add_column('farms', sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_farms_region_id', 'farms', 'regions', ['region_id'], ['id'])
    op.alter_column('farms', 'name', existing_type=sa.String(255), type_=sa.String(150), nullable=False)
    op.alter_column('farms', 'area_ha', existing_type=sa.Float(), nullable=True)
    op.drop_column('farms', 'province')
    op.drop_column('farms', 'is_active')

    # ------------------------------------------------------------------ #
    # 4. plots: añadir crop_id, soil_id, hash_plot, management_profile;  #
    #    eliminar crop_type, soil_type, depth_cm, province, is_active     #
    # ------------------------------------------------------------------ #
    op.add_column('plots', sa.Column('crop_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('plots', sa.Column('soil_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('plots', sa.Column('hash_plot', sa.String(64), nullable=True))
    op.add_column('plots', sa.Column('management_profile', sa.String(20), nullable=True))
    op.create_foreign_key('fk_plots_crop_id', 'plots', 'crops', ['crop_id'], ['id'])
    op.create_foreign_key('fk_plots_soil_id', 'plots', 'soils', ['soil_id'], ['id'])
    op.drop_column('plots', 'crop_type')
    op.drop_column('plots', 'soil_type')
    op.drop_column('plots', 'depth_cm')
    op.drop_column('plots', 'province')
    op.drop_column('plots', 'is_active')
    op.alter_column('plots', 'name', existing_type=sa.String(100), type_=sa.String(150), nullable=True)
    op.alter_column('plots', 'area_ha', existing_type=sa.Float(), nullable=True)

    # ------------------------------------------------------------------ #
    # 5. sensors → devices: renombra tabla y columnas; elimina campos     #
    # ------------------------------------------------------------------ #
    op.rename_table('sensors', 'devices')
    op.alter_column('devices', 'esp32_id', new_column_name='code')
    op.drop_column('devices', 'sensor_type')
    op.drop_column('devices', 'depth_cm')
    op.drop_column('devices', 'status')
    op.drop_column('devices', 'battery_mv')
    op.drop_column('devices', 'last_reading')
    # is_active permanece en devices

    # ------------------------------------------------------------------ #
    # 6. Nueva tabla irrigation_records                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        'irrigation_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=_uuid_default),
        sa.Column('plot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('irrigation_mm', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plot_id', 'week_start', name='uq_irrigation_plot_week'),
    )

    # ------------------------------------------------------------------ #
    # 7. Nueva tabla harvests                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        'harvests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=_uuid_default),
        sa.Column('plot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('harvest_date', sa.Date(), nullable=False),
        sa.Column('yield_kg_ha', sa.Float(), nullable=True),
        sa.Column('water_consumed_m3_ha', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_ts_default, nullable=False),
        sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    # harvests
    op.drop_table('harvests')

    # irrigation_records
    op.drop_table('irrigation_records')

    # devices → sensors
    op.add_column('devices', sa.Column('last_reading', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices', sa.Column('battery_mv', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('status', sa.String(20), nullable=False, server_default='inactive'))
    op.add_column('devices', sa.Column('depth_cm', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('sensor_type', sa.String(50), nullable=False, server_default='multi'))
    op.alter_column('devices', 'code', new_column_name='esp32_id')
    op.rename_table('devices', 'sensors')

    # plots
    op.alter_column('plots', 'area_ha', existing_type=sa.Float(), nullable=False)
    op.alter_column('plots', 'name', existing_type=sa.String(150), type_=sa.String(100), nullable=False)
    op.drop_constraint('fk_plots_soil_id', 'plots', type_='foreignkey')
    op.drop_constraint('fk_plots_crop_id', 'plots', type_='foreignkey')
    op.drop_column('plots', 'management_profile')
    op.drop_column('plots', 'hash_plot')
    op.drop_column('plots', 'soil_id')
    op.drop_column('plots', 'crop_id')
    op.add_column('plots', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('plots', sa.Column('province', sa.String(100), nullable=True))
    op.add_column('plots', sa.Column('depth_cm', sa.Integer(), nullable=True))
    op.add_column('plots', sa.Column('soil_type', sa.String(100), nullable=False, server_default='unknown'))
    op.add_column('plots', sa.Column('crop_type', sa.String(100), nullable=False, server_default='unknown'))

    # farms
    op.drop_constraint('fk_farms_region_id', 'farms', type_='foreignkey')
    op.drop_column('farms', 'region_id')
    op.alter_column('farms', 'area_ha', existing_type=sa.Float(), nullable=False)
    op.alter_column('farms', 'name', existing_type=sa.String(150), type_=sa.String(255), nullable=False)
    op.add_column('farms', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('farms', sa.Column('province', sa.String(100), nullable=True))

    # users
    op.add_column('users', sa.Column('region', sa.String(100), nullable=True))

    # drop new tables
    op.drop_table('soils')
    op.drop_table('crops')
    op.drop_table('regions')
