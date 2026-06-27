"""schema_v2_reforma_completa

Revision ID: c7d8e9f0a1b2
Revises: 6fc335ef3267
Create Date: 2026-06-27

Cambios respecto a v1:
- Elimina: phenological_phases (y relacion en crops)
- regions: añade latitude, longitude; pasa a ser FK de farms (no de plots)
- users: elimina columna region (texto)
- farms: añade region_id FK, elimina province e is_active
- plots: elimina region_id, depth_cm, is_active; añade management_profile
- devices: renombra esp32_id→code, elimina status/battery_mv/last_reading
- irrigation_weekly→irrigation_records: renombra tabla y columna week_start_date→week_start, añade UNIQUE
- harvests: renombra/elimina columnas, cambia harvest_date a DATE
NOTE: anomalies, recommendations, cluster_assignments, cluster_statistics se implementan en sprint posterior
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = '6fc335ef3267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Eliminar tabla phenological_phases                               #
    # ------------------------------------------------------------------ #
    op.drop_table('phenological_phases')

    # ------------------------------------------------------------------ #
    # 2. regions: añadir latitude y longitude                             #
    # ------------------------------------------------------------------ #
    op.add_column('regions', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('regions', sa.Column('longitude', sa.Float(), nullable=True))
    # siar_station_code pasa a nullable (antes era NOT NULL)
    op.alter_column('regions', 'siar_station_code', existing_type=sa.String(10), nullable=True)

    # ------------------------------------------------------------------ #
    # 3. users: eliminar columna region (texto)                           #
    # ------------------------------------------------------------------ #
    op.drop_column('users', 'region')

    # ------------------------------------------------------------------ #
    # 4. farms: añadir region_id, eliminar province e is_active           #
    # ------------------------------------------------------------------ #
    op.add_column('farms', sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_farms_region_id', 'farms', 'regions', ['region_id'], ['id'])
    op.alter_column('farms', 'name', existing_type=sa.String(255), type_=sa.String(150), nullable=False)
    op.alter_column('farms', 'area_ha', existing_type=sa.Float(), nullable=True)
    op.drop_column('farms', 'province')
    op.drop_column('farms', 'is_active')

    # ------------------------------------------------------------------ #
    # 5. plots: eliminar region_id, depth_cm, is_active; añadir          #
    #    management_profile; name pasa a nullable                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint('plots_region_id_fkey', 'plots', type_='foreignkey')
    op.drop_column('plots', 'region_id')
    op.drop_column('plots', 'depth_cm')
    op.drop_column('plots', 'is_active')
    op.add_column('plots', sa.Column('management_profile', sa.String(20), nullable=True))
    op.alter_column('plots', 'name', existing_type=sa.String(100), type_=sa.String(150), nullable=True)
    op.alter_column('plots', 'area_ha', existing_type=sa.Float(), nullable=True)

    # ------------------------------------------------------------------ #
    # 6. devices: renombrar esp32_id→code, eliminar status/battery/etc.  #
    # ------------------------------------------------------------------ #
    op.alter_column('devices', 'esp32_id', new_column_name='code')
    op.drop_column('devices', 'status')
    op.drop_column('devices', 'battery_mv')
    op.drop_column('devices', 'last_reading')

    # ------------------------------------------------------------------ #
    # 7. irrigation_weekly → irrigation_records                           #
    # ------------------------------------------------------------------ #
    op.rename_table('irrigation_weekly', 'irrigation_records')
    op.alter_column('irrigation_records', 'week_start_date', new_column_name='week_start')
    op.create_unique_constraint('uq_irrigation_plot_week', 'irrigation_records', ['plot_id', 'week_start'])

    # ------------------------------------------------------------------ #
    # 8. harvests: renombrar columnas, eliminar campaign/production_kg,  #
    #    cambiar harvest_date de TIMESTAMP a DATE                         #
    # ------------------------------------------------------------------ #
    op.drop_column('harvests', 'campaign')
    op.drop_column('harvests', 'production_kg')
    op.alter_column('harvests', 'production_kg_ha', new_column_name='yield_kg_ha')
    op.alter_column('harvests', 'water_consumption_m3_ha', new_column_name='water_consumed_m3_ha')
    op.alter_column(
        'harvests', 'harvest_date',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        postgresql_using='harvest_date::date',
        nullable=False,
    )



def downgrade() -> None:
    # harvests: revertir
    op.alter_column('harvests', 'harvest_date', existing_type=sa.Date(), type_=sa.DateTime(timezone=True), nullable=False)
    op.alter_column('harvests', 'water_consumed_m3_ha', new_column_name='water_consumption_m3_ha')
    op.alter_column('harvests', 'yield_kg_ha', new_column_name='production_kg_ha')
    op.add_column('harvests', sa.Column('production_kg', sa.Float(), nullable=True))
    op.add_column('harvests', sa.Column('campaign', sa.String(50), nullable=True))

    # irrigation_records → irrigation_weekly
    op.drop_constraint('uq_irrigation_plot_week', 'irrigation_records', type_='unique')
    op.alter_column('irrigation_records', 'week_start', new_column_name='week_start_date')
    op.rename_table('irrigation_records', 'irrigation_weekly')

    # devices: revertir
    op.add_column('devices', sa.Column('last_reading', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices', sa.Column('battery_mv', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('status', sa.String(20), nullable=False, server_default='inactive'))
    op.alter_column('devices', 'code', new_column_name='esp32_id')

    # plots: revertir
    op.alter_column('plots', 'area_ha', existing_type=sa.Float(), nullable=False)
    op.alter_column('plots', 'name', existing_type=sa.String(150), type_=sa.String(100), nullable=False)
    op.drop_column('plots', 'management_profile')
    op.add_column('plots', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('plots', sa.Column('depth_cm', sa.Integer(), nullable=True))
    op.add_column('plots', sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key('plots_region_id_fkey', 'plots', 'regions', ['region_id'], ['id'])

    # farms: revertir
    op.add_column('farms', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('farms', sa.Column('province', sa.String(100), nullable=True))
    op.alter_column('farms', 'area_ha', existing_type=sa.Float(), nullable=False)
    op.alter_column('farms', 'name', existing_type=sa.String(150), type_=sa.String(255), nullable=False)
    op.drop_constraint('fk_farms_region_id', 'farms', type_='foreignkey')
    op.drop_column('farms', 'region_id')

    # users: revertir
    op.add_column('users', sa.Column('region', sa.String(100), nullable=True))

    # regions: revertir
    op.alter_column('regions', 'siar_station_code', existing_type=sa.String(10), nullable=False)
    op.drop_column('regions', 'longitude')
    op.drop_column('regions', 'latitude')

    # phenological_phases: recrear
    op.create_table(
        'phenological_phases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('crop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crops.id'), nullable=False),
        sa.Column('phase_name', sa.String(50), nullable=False),
        sa.Column('typical_start_month', sa.Integer(), nullable=False),
        sa.Column('typical_end_month', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
