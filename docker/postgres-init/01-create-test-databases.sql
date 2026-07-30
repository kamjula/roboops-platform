-- Runs automatically ONLY when the postgres data volume is first created
-- (i.e. on the very first "docker compose up" against an empty volume).
-- If the volume already exists, these statements will NOT run again automatically -
-- see README.md for the safe manual commands to create these databases on an
-- existing volume.

CREATE DATABASE roboops_test_db;
CREATE DATABASE roboops_migration_test_db;
