CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vineguard_api') THEN
      CREATE ROLE vineguard_api WITH LOGIN PASSWORD 'vineguard';
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vineguard_ingestor') THEN
      CREATE ROLE vineguard_ingestor WITH LOGIN PASSWORD 'vineguard';
   END IF;
   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vineguard_analytics') THEN
      CREATE ROLE vineguard_analytics WITH LOGIN PASSWORD 'vineguard';
   END IF;
END$$;

GRANT CONNECT ON DATABASE vineguard TO vineguard_api, vineguard_ingestor, vineguard_analytics;

\c vineguard

CREATE TABLE IF NOT EXISTS telemetry_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(64) NOT NULL,
    soil_moisture DOUBLE PRECISION NOT NULL,
    soil_temp_c DOUBLE PRECISION NOT NULL,
    ambient_temp_c DOUBLE PRECISION NOT NULL,
    ambient_humidity DOUBLE PRECISION NOT NULL,
    light_lux DOUBLE PRECISION NOT NULL,
    battery_voltage DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('telemetry_readings', 'recorded_at', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS analytics_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(64) NOT NULL,
    signal_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT ON telemetry_readings, analytics_signals TO vineguard_api;
GRANT INSERT ON telemetry_readings TO vineguard_ingestor;
GRANT INSERT, SELECT ON analytics_signals TO vineguard_analytics;
