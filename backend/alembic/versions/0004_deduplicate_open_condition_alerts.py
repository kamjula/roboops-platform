"""Enforce one open telemetry-condition alert per robot.

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_alerts_open_telemetry_condition_robot",
        "alerts",
        ["robot_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL AND alert_type = 'telemetry_condition'"),
    )


def downgrade() -> None:
    op.drop_index("uq_alerts_open_telemetry_condition_robot", table_name="alerts")
