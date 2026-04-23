-- VineGuard V1 Database Initialisation
-- Runs once against a fresh TimescaleDB / PostgreSQL container.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ──────────────────────────────────────────────
-- Roles
-- ──────────────────────────────────────────────
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

-- ──────────────────────────────────────────────
-- Domain model — static / relational tables
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vineyards (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL,
    region       TEXT        NOT NULL DEFAULT '',
    owner_name   TEXT        NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blocks (
    id                  UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    vineyard_id         UUID             NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    name                TEXT             NOT NULL,
    variety             TEXT             NOT NULL DEFAULT '',
    area_ha             DOUBLE PRECISION,
    row_spacing_m       DOUBLE PRECISION,
    reference_lux_peak  DOUBLE PRECISION,        -- expected peak-hour lux for canopy ratio rule
    notes               TEXT             DEFAULT '',
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blocks_vineyard ON blocks(vineyard_id);

CREATE TABLE IF NOT EXISTS nodes (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id         UUID             NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    device_id        VARCHAR(64)      NOT NULL UNIQUE,
    name             TEXT             NOT NULL,
    tier             VARCHAR(16)      NOT NULL DEFAULT 'basic'
                         CHECK (tier IN ('basic', 'precision_plus')),
    lat              DOUBLE PRECISION,
    lon              DOUBLE PRECISION,
    installed_at     TIMESTAMPTZ      NOT NULL DEFAULT now(),
    firmware_version VARCHAR(32)      DEFAULT '0.0.0',
    last_seen_at     TIMESTAMPTZ,
    battery_voltage  DOUBLE PRECISION,
    battery_pct      INTEGER,
    rssi_last        INTEGER,
    status           VARCHAR(16)      NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active', 'stale', 'inactive'))
);

CREATE INDEX IF NOT EXISTS idx_nodes_block  ON nodes(block_id);
CREATE INDEX IF NOT EXISTS idx_nodes_device ON nodes(device_id);

CREATE TABLE IF NOT EXISTS gateways (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    vineyard_id      UUID        NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    device_id        VARCHAR(64) NOT NULL UNIQUE,
    last_seen_at     TIMESTAMPTZ,
    firmware_version VARCHAR(32) DEFAULT '0.0.0',
    status           VARCHAR(16) NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active', 'stale', 'inactive'))
);

CREATE TABLE IF NOT EXISTS users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(16)  NOT NULL DEFAULT 'viewer'
                        CHECK (role IN ('admin', 'operator', 'viewer')),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ──────────────────────────────────────────────
-- Time-series tables
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS telemetry_readings (
    id                UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id         VARCHAR(64)      NOT NULL,
    node_id           UUID             REFERENCES nodes(id) ON DELETE SET NULL,
    soil_moisture     DOUBLE PRECISION NOT NULL,
    soil_temp_c       DOUBLE PRECISION NOT NULL,
    ambient_temp_c    DOUBLE PRECISION NOT NULL,
    ambient_humidity  DOUBLE PRECISION NOT NULL,
    light_lux         DOUBLE PRECISION NOT NULL,
    battery_voltage   DOUBLE PRECISION NOT NULL,
    leaf_wetness_pct  DOUBLE PRECISION,           -- Precision+ only
    pressure_hpa      DOUBLE PRECISION,
    schema_version    VARCHAR(8)       DEFAULT '1.0',
    recorded_at       TIMESTAMPTZ      NOT NULL DEFAULT now()
);

SELECT create_hypertable('telemetry_readings', 'recorded_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_telemetry_device  ON telemetry_readings(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_node    ON telemetry_readings(node_id, recorded_at DESC);

-- ──────────────────────────────────────────────
-- Alerts & recommendations
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id        UUID        REFERENCES nodes(id) ON DELETE SET NULL,
    block_id       UUID        REFERENCES blocks(id) ON DELETE SET NULL,
    vineyard_id    UUID        NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    rule_key       VARCHAR(64) NOT NULL,
    severity       VARCHAR(16) NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title          VARCHAR(128) NOT NULL,
    message        TEXT        NOT NULL,
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    triggered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at    TIMESTAMPTZ,
    cooldown_until TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_vineyard ON alerts(vineyard_id);
CREATE INDEX IF NOT EXISTS idx_alerts_block    ON alerts(block_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active   ON alerts(is_active, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_rule     ON alerts(rule_key, node_id, is_active);

CREATE TABLE IF NOT EXISTS recommendations (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id         UUID        REFERENCES alerts(id) ON DELETE SET NULL,
    block_id         UUID        REFERENCES blocks(id) ON DELETE SET NULL,
    vineyard_id      UUID        NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    action_text      TEXT        NOT NULL,
    priority         INTEGER     NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
    due_by           TIMESTAMPTZ,
    is_acknowledged  BOOLEAN     NOT NULL DEFAULT FALSE,
    acknowledged_at  TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rec_vineyard ON recommendations(vineyard_id);
CREATE INDEX IF NOT EXISTS idx_rec_block    ON recommendations(block_id);
CREATE INDEX IF NOT EXISTS idx_rec_unack    ON recommendations(is_acknowledged, created_at DESC);

-- ──────────────────────────────────────────────
-- GDD accumulation (per vineyard, per day)
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gdd_accumulation (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    vineyard_id      UUID             NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    date             DATE             NOT NULL,
    gdd_daily        DOUBLE PRECISION NOT NULL DEFAULT 0,
    gdd_season_total DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT now(),
    UNIQUE (vineyard_id, date)
);

CREATE INDEX IF NOT EXISTS idx_gdd_vineyard ON gdd_accumulation(vineyard_id, date DESC);

-- Analytics signals (legacy, kept for compatibility)
CREATE TABLE IF NOT EXISTS analytics_signals (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   VARCHAR(64) NOT NULL,
    signal_type VARCHAR(32) NOT NULL,
    severity    VARCHAR(16) NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_device ON analytics_signals(device_id, created_at DESC);

-- ──────────────────────────────────────────────
-- Grants
-- ──────────────────────────────────────────────

-- API: read everything, write recommendations/alerts (resolve/ack via routes)
GRANT SELECT ON
    vineyards, blocks, nodes, gateways, users,
    telemetry_readings, analytics_signals,
    alerts, recommendations, gdd_accumulation
TO vineguard_api;
GRANT UPDATE (is_active, resolved_at) ON alerts TO vineguard_api;
GRANT UPDATE (is_acknowledged, acknowledged_at) ON recommendations TO vineguard_api;
GRANT INSERT ON users TO vineguard_api;

-- Ingestor: insert telemetry, upsert node health
GRANT INSERT ON telemetry_readings TO vineguard_ingestor;
GRANT SELECT, UPDATE (last_seen_at, battery_voltage, battery_pct, rssi_last, status) ON nodes TO vineguard_ingestor;

-- Analytics: read domain model, write alerts/recommendations/gdd
GRANT SELECT ON
    vineyards, blocks, nodes, telemetry_readings, alerts, recommendations
TO vineguard_analytics;
GRANT INSERT, SELECT ON
    alerts, recommendations, gdd_accumulation, analytics_signals
TO vineguard_analytics;
GRANT UPDATE (is_active, resolved_at, cooldown_until) ON alerts TO vineguard_analytics;
