-- VineGuard live-DB repair script
-- Apply to a partially-initialized database to create the missing tables.
-- Idempotent: safe to run multiple times.

-- ── Time-series ──────────────────────────────────────────────────────
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
    leaf_wetness_pct  DOUBLE PRECISION,
    pressure_hpa      DOUBLE PRECISION,
    schema_version    VARCHAR(8)       DEFAULT '1.0',
    recorded_at       TIMESTAMPTZ      NOT NULL DEFAULT now()
);

DO $$
BEGIN
    PERFORM create_hypertable('telemetry_readings', 'recorded_at', if_not_exists => TRUE);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'create_hypertable skipped: %', SQLERRM;
END$$;

CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry_readings(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_node   ON telemetry_readings(node_id, recorded_at DESC);

-- ── Alerts ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id        UUID         REFERENCES nodes(id) ON DELETE SET NULL,
    block_id       UUID         REFERENCES blocks(id) ON DELETE SET NULL,
    vineyard_id    UUID         NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    rule_key       VARCHAR(64)  NOT NULL,
    severity       VARCHAR(16)  NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title          VARCHAR(128) NOT NULL,
    message        TEXT         NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    triggered_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    resolved_at    TIMESTAMPTZ,
    cooldown_until TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_vineyard ON alerts(vineyard_id);
CREATE INDEX IF NOT EXISTS idx_alerts_block    ON alerts(block_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active   ON alerts(is_active, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_rule     ON alerts(rule_key, node_id, is_active);

-- ── Recommendations ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID        REFERENCES alerts(id) ON DELETE SET NULL,
    block_id        UUID        REFERENCES blocks(id) ON DELETE SET NULL,
    vineyard_id     UUID        NOT NULL REFERENCES vineyards(id) ON DELETE CASCADE,
    action_text     TEXT        NOT NULL,
    priority        INTEGER     NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
    due_by          TIMESTAMPTZ,
    is_acknowledged BOOLEAN     NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rec_vineyard ON recommendations(vineyard_id);
CREATE INDEX IF NOT EXISTS idx_rec_block    ON recommendations(block_id);
CREATE INDEX IF NOT EXISTS idx_rec_unack    ON recommendations(is_acknowledged, created_at DESC);

-- ── GDD accumulation ────────────────────────────────────────────────
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

-- ── Analytics signals ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_signals (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   VARCHAR(64)  NOT NULL,
    signal_type VARCHAR(32)  NOT NULL,
    severity    VARCHAR(16)  NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_device ON analytics_signals(device_id, created_at DESC);

-- ── Grants ──────────────────────────────────────────────────────────
-- Full grant set: covers tables created before the hypertable abort
-- as well as the tables re-created by this script. All GRANT statements
-- are idempotent — safe to run multiple times.

-- API role
GRANT SELECT ON
    vineyards, blocks, nodes, gateways, users,
    telemetry_readings, analytics_signals,
    alerts, recommendations, gdd_accumulation
TO vineguard_api;
GRANT INSERT ON users TO vineguard_api;
GRANT UPDATE (is_active, resolved_at)              ON alerts          TO vineguard_api;
GRANT UPDATE (is_acknowledged, acknowledged_at)    ON recommendations TO vineguard_api;

-- Ingestor role
-- NOTE: ingestor uses INSERT ... RETURNING *, which requires SELECT on
-- returned columns in PostgreSQL.
GRANT INSERT, SELECT ON telemetry_readings TO vineguard_ingestor;
GRANT SELECT ON nodes TO vineguard_ingestor;
GRANT UPDATE (last_seen_at, battery_voltage, battery_pct, rssi_last, status) ON nodes TO vineguard_ingestor;

-- Analytics role
GRANT SELECT ON
    vineyards, blocks, nodes,
    telemetry_readings, alerts, recommendations
TO vineguard_analytics;
GRANT INSERT ON alerts, recommendations, gdd_accumulation, analytics_signals TO vineguard_analytics;
GRANT UPDATE (is_active, resolved_at, cooldown_until) ON alerts TO vineguard_analytics;
