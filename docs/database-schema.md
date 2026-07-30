# RoboOps database schema (Phase 2)

This document describes the nine tables that make up the RoboOps Phase 2 database foundation. All tables live in the `public` schema of the PostgreSQL database and are managed exclusively through Alembic migrations (`backend/alembic/versions/0001_initial_schema.py`). Primary keys are UUIDs (PostgreSQL `uuid`), and every table has a `created_at` column with a server-side default of `now()`.

## sites

Physical locations/depots where robots are deployed.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| site_code | varchar(20) | unique, indexed |
| name | varchar(120) | |
| address | varchar(255) | nullable |
| timezone | varchar(50) | default `"UTC"` |
| created_at | timestamptz | server default `now()` |

## robot_models

Reference catalogue of robot models/types.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| model_code | varchar(30) | unique, indexed |
| manufacturer | varchar(120) | |
| name | varchar(120) | |
| category | varchar(50) | |
| created_at | timestamptz | server default `now()` |

## technicians

Maintenance staff who service robots.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| technician_code | varchar(20) | unique, indexed |
| name | varchar(120) | |
| email | varchar(255) | unique |
| phone | varchar(30) | nullable |
| created_at | timestamptz | server default `now()` |

## robots

The fleet itself.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| robot_code | varchar(20) | unique, indexed (e.g. `RBT-001`) |
| name | varchar(120) | |
| serial_number | varchar(100) | unique |
| model_id | uuid | foreign key -> `robot_models.id` |
| site_id | uuid | foreign key -> `sites.id` |
| status | enum `robot_status` | `active`, `idle`, `maintenance`, `offline`, `decommissioned`; default `active` |
| installed_at | timestamptz | |
| created_at | timestamptz | server default `now()` |
| updated_at | timestamptz | server default `now()`, updated on change |

## sensors

Sensors attached to a robot.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| robot_id | uuid | foreign key -> `robots.id` |
| sensor_code | varchar(30) | unique, indexed |
| sensor_type | enum `sensor_type` | `temperature`, `battery`, `vibration`, `motor_load`, `navigation_error` |
| unit | varchar(20) | e.g. `percent`, `celsius` |
| created_at | timestamptz | server default `now()` |

## sensor_readings

Time-series metric values recorded by a sensor.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| sensor_id | uuid | foreign key -> `sensors.id` |
| robot_id | uuid | foreign key -> `robots.id` (denormalized for query convenience) |
| recorded_at | timestamptz | indexed |
| value | float | |
| created_at | timestamptz | server default `now()` |

## maintenance_schedules

Planned/upcoming maintenance work for a robot.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| robot_id | uuid | foreign key -> `robots.id` |
| scheduled_for | timestamptz | |
| maintenance_type | varchar(50) | |
| status | enum `maintenance_status` | `scheduled`, `in_progress`, `completed`, `cancelled`; default `scheduled` |
| notes | varchar(500) | nullable |
| created_at | timestamptz | server default `now()` |

## maintenance_records

Completed maintenance history.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| robot_id | uuid | foreign key -> `robots.id` |
| technician_id | uuid | foreign key -> `technicians.id` |
| schedule_id | uuid | foreign key -> `maintenance_schedules.id`, nullable |
| performed_at | timestamptz | |
| maintenance_type | varchar(50) | |
| description | varchar(500) | nullable |
| cost_usd | float | nullable |
| created_at | timestamptz | server default `now()` |

## alerts

Predictive-maintenance/anomaly alerts raised for a robot.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | primary key |
| robot_id | uuid | foreign key -> `robots.id` |
| sensor_id | uuid | foreign key -> `sensors.id`, nullable |
| severity | enum `alert_severity` | `info`, `warning`, `critical` |
| alert_type | varchar(50) | |
| message | varchar(500) | |
| triggered_at | timestamptz | |
| resolved_at | timestamptz | nullable |
| created_at | timestamptz | server default `now()` |

## Relationships at a glance

```
sites ----------\
                 >-- robots --< sensors --< sensor_readings
robot_models ---/      |            \
                       |             >-- alerts
technicians --< maintenance_records  |
      \                              |
       >-- maintenance_records --< maintenance_schedules --< robots
```

Every robot belongs to exactly one site and one robot model. A robot may have many sensors, sensor readings, maintenance schedules, maintenance records, and alerts; deleting a robot cascades to all of these (`cascade="all, delete-orphan"` on the ORM relationships, matched by `ON DELETE` behavior enforced at the application layer via SQLAlchemy). Sites, robot models, and technicians are shared reference data and are not deleted when a robot is removed.

## Migrations

Run migrations with Alembic from the `backend` directory, with `DATABASE_URL` set to the target database:

```bash
export DATABASE_URL=postgresql+psycopg://roboops_user:roboops_pass@localhost:5433/roboops_db
alembic upgrade head
```

The single migration `0001_initial_schema` creates all nine tables above, their four enum types (`robot_status`, `sensor_type`, `maintenance_status`, `alert_severity`), and every index and foreign key. Its `downgrade()` drops all nine tables and all four enum types, fully reversing the upgrade.

## Deterministic seed data

`backend/scripts/seed.py` populates two sites, three robot models, four technicians, twelve robots (`RBT-001` through `RBT-012`), two sensors per robot, five readings per sensor, one maintenance schedule and one maintenance record per robot, and alerts for every other robot. All IDs are derived with `uuid.uuid5` from a fixed namespace and natural key, all timestamps are derived from a fixed reference time, and randomised sensor-reading jitter uses a fixed `random.seed()` - so re-running the script is fully reproducible and idempotent. See the "Deterministic seed behavior" section of the root `README.md` for the full list of guarantees.
