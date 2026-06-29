"""add_sensors_and_device_sensors

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-06-29

Añade la tabla de catálogo de sensores de la plataforma (sensors) y la tabla
de asociación M2M device_sensors que vincula cada dispositivo a los sensores
que tiene registrados. Todos los devices comparten el mismo conjunto de sensores
(simula la compatibilidad de la plataforma con los 3 sensores físicos del nodo).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_uuid_default = sa.text('gen_random_uuid()')
_ts_default = sa.text('now()')


def upgrade() -> None:
    # ── sensors: catálogo de tipos de sensor de la plataforma ─────────────────
    op.create_table(
        'sensors',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=_uuid_default,
        ),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('sensor_type', sa.String(50), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=_ts_default,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=_ts_default,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── device_sensors: M2M entre devices y sensors ───────────────────────────
    op.create_table(
        'device_sensors',
        sa.Column(
            'device_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('devices.id', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            'sensor_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('sensors.id', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('device_id', 'sensor_id'),
    )

    # ── Seed: los 3 tipos de sensor del nodo ESP32 ────────────────────────────
    op.execute(
        """
        INSERT INTO sensors (id, name, sensor_type, unit, description)
        VALUES
          (gen_random_uuid(), 'DHT22', 'air_temperature',   '°C',  'Temperatura ambiente (DHT22)'),
          (gen_random_uuid(), 'DHT22', 'relative_humidity', '%',   'Humedad relativa ambiente (DHT22)'),
          (gen_random_uuid(), 'DS18B20', 'soil_temperature','°C',  'Temperatura del suelo (DS18B20)'),
          (gen_random_uuid(), 'SEN0193', 'soil_humidity',   '%',   'Humedad del suelo capacitiva (SEN0193)')
        """
    )


def downgrade() -> None:
    op.drop_table('device_sensors')
    op.drop_table('sensors')
