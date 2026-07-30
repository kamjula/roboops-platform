"""Initial RoboOps schema: sites, robot_models, robots, technicians, sensors, sensor_readings, maintenance_schedules, maintenance_records, alerts.

Revision ID: 0001
Revises: 
Create Date: 2026-07-30

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


robot_status_enum = postgresql.ENUM(
    "active", "idle", "maintenance", "offline", "decommissioned", name="robot_status", create_type=False
)
sensor_type_enum = postgresql.ENUM(
    "temperature", "battery", "vibration", "motor_load", "navigation_error", name="sensor_type", create_type=False
)
maintenance_status_enum = postgresql.ENUM(
    "scheduled", "in_progress", "completed", "cancelled", name="maintenance_status", create_type=False
)
alert_severity_enum = postgresql.ENUM(
    "info", "warning", "critical", name="alert_severity", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    robot_status_enum.create(bind, checkfirst=True)
    sensor_type_enum.create(bind, checkfirst=True)
    maintenance_status_enum.create(bind, checkfirst=True)
    alert_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("site_code"),
    )
    op.create_index("ix_sites_site_code", "sites", ["site_code"])

    op.create_table(
        "robot_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_code", sa.String(length=30), nullable=False),
        sa.Column("manufacturer", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("model_code"),
    )
    op.create_index("ix_robot_models_model_code", "robot_models", ["model_code"])

    op.create_table(
        "technicians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("technician_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("technician_code"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_technicians_technician_code", "technicians", ["technician_code"])

    op.create_table(
        "robots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("robot_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robot_models.id"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("status", robot_status_enum, nullable=False, server_default="active"),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("robot_code"),
        sa.UniqueConstraint("serial_number"),
    )
    op.create_index("ix_robots_robot_code", "robots", ["robot_code"])

    op.create_table(
        "sensors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("robot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robots.id"), nullable=False),
        sa.Column("sensor_code", sa.String(length=30), nullable=False),
        sa.Column("sensor_type", sensor_type_enum, nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("sensor_code"),
    )
    op.create_index("ix_sensors_sensor_code", "sensors", ["sensor_code"])

    op.create_table(
        "sensor_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("robot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robots.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sensor_readings_recorded_at", "sensor_readings", ["recorded_at"])

    op.create_table(
        "maintenance_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("robot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robots.id"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maintenance_type", sa.String(length=50), nullable=False),
        sa.Column("status", maintenance_status_enum, nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "maintenance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("robot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robots.id"), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("technicians.id"), nullable=False),
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maintenance_schedules.id"),
            nullable=True,
        ),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maintenance_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("robot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("robots.id"), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sensors.id"), nullable=True),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("maintenance_records")
    op.drop_table("maintenance_schedules")
    op.drop_table("sensor_readings")
    op.drop_table("sensors")
    op.drop_table("robots")
    op.drop_table("technicians")
    op.drop_table("robot_models")
    op.drop_table("sites")

    bind = op.get_bind()
    alert_severity_enum.drop(bind, checkfirst=True)
    maintenance_status_enum.drop(bind, checkfirst=True)
    sensor_type_enum.drop(bind, checkfirst=True)
    robot_status_enum.drop(bind, checkfirst=True)
