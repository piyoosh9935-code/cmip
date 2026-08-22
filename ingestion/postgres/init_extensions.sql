-- Mounted into postgres's /docker-entrypoint-initdb.d/ - runs once on first container
-- start against a fresh volume.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
