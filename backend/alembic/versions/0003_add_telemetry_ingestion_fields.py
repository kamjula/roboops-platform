"""Add telemetry idempotency and query indexes.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sensor_readings", sa.Column("source_event_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "uq_sensor_readings_sensor_source_event",
        "sensor_readings",
        ["sensor_id", "source_event_id"],
    )
    op.create_index("ix_sensors_robot_id", "sensors", ["robot_id"])
    op.create_index(
        "ix_sensor_readings_sensor_recorded_id",
        "sensor_readings",
        ["sensor_id", sa.text("recorded_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_sensor_readings_sensor_recorded_id", table_name="sensor_readings")
    op.drop_index("ix_sensors_robot_id", table_name="sensors")
    op.drop_constraint("uq_sensor_readings_sensor_source_event", "sensor_readings", type_="unique")
    op.drop_column("sensor_readings", "source_event_id")