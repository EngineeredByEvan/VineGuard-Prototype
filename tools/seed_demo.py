#!/usr/bin/env python3
"""
VineGuard Demo Seed Script
Provisions demo vineyard, block, node, gateway, and user data into PostgreSQL.
Uses psql via subprocess — no extra Python dependencies required.

Usage:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vineguard \
        python3 tools/seed_demo.py
"""
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
PSQL_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vineguard"
)

# ---------------------------------------------------------------------------
# Fixed UUIDs for idempotent seeding
# ---------------------------------------------------------------------------
VINEYARD_ID = "a1b2c3d4-0001-0001-0001-000000000001"
BLOCK_A_ID  = "a1b2c3d4-0002-0001-0001-000000000002"
BLOCK_B_ID  = "a1b2c3d4-0002-0002-0001-000000000003"
NODE_001_ID = "a1b2c3d4-0003-0001-0001-000000000004"
NODE_002_ID = "a1b2c3d4-0003-0002-0001-000000000005"
NODE_003_ID = "a1b2c3d4-0003-0003-0001-000000000006"
GW_001_ID   = "a1b2c3d4-0004-0001-0001-000000000007"
USER_ID     = "a1b2c3d4-0005-0001-0001-000000000008"

# bcrypt hash for "demo-password-2024" (cost factor 12)
DEMO_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TspleDVORBNWGvq1XhPgq1yXM5GK"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_sql(sql: str, label: str = "") -> None:
    result = subprocess.run(
        ["psql", PSQL_URL, "-c", sql],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  SQL error ({label}): {result.stderr.strip()}", file=sys.stderr)
        raise RuntimeError(f"psql failed for step '{label}' (rc={result.returncode})")


def step(label: str, sql: str) -> None:
    print(f"  {label}...", end=" ", flush=True)
    run_sql(sql, label)
    print("OK")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed() -> None:
    print("=" * 60)
    print("VineGuard Demo Seed")
    print(f"  Target: {PSQL_URL}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Vineyard  (id, name, region, owner_name, created_at)
    # ------------------------------------------------------------------
    print("\n[1/6] Vineyard")
    step(
        "Creating Copper Creek Vineyard",
        f"""
        INSERT INTO vineyards (id, name, region, owner_name, created_at)
        VALUES (
            '{VINEYARD_ID}',
            'Copper Creek Vineyard',
            'Napa Valley',
            'Jordan Hayes',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )

    # ------------------------------------------------------------------
    # 2. Blocks  (id, vineyard_id, name, variety, area_ha, reference_lux_peak, created_at)
    # ------------------------------------------------------------------
    print("\n[2/6] Blocks")
    step(
        "Creating Block A (Cabernet Block)",
        f"""
        INSERT INTO blocks (id, vineyard_id, name, variety, area_ha, reference_lux_peak, created_at)
        VALUES (
            '{BLOCK_A_ID}',
            '{VINEYARD_ID}',
            'Cabernet Block',
            'Cabernet Sauvignon',
            3.2,
            45000,
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )
    step(
        "Creating Block B (Pinot Block)",
        f"""
        INSERT INTO blocks (id, vineyard_id, name, variety, area_ha, reference_lux_peak, created_at)
        VALUES (
            '{BLOCK_B_ID}',
            '{VINEYARD_ID}',
            'Pinot Block',
            'Pinot Noir',
            1.8,
            40000,
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )

    # ------------------------------------------------------------------
    # 3. Nodes  (id, block_id, device_id, name, tier, status, installed_at)
    # ------------------------------------------------------------------
    print("\n[3/6] Nodes")
    step(
        "Creating Node vg-node-001 (Block A - North Row)",
        f"""
        INSERT INTO nodes (id, block_id, device_id, name, tier, status, installed_at)
        VALUES (
            '{NODE_001_ID}',
            '{BLOCK_A_ID}',
            'vg-node-001',
            'Block A - North Row',
            'basic',
            'active',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )
    step(
        "Creating Node vg-node-002 (Block A - South Row)",
        f"""
        INSERT INTO nodes (id, block_id, device_id, name, tier, status, installed_at)
        VALUES (
            '{NODE_002_ID}',
            '{BLOCK_A_ID}',
            'vg-node-002',
            'Block A - South Row',
            'basic',
            'active',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )
    step(
        "Creating Node vg-node-003 (Block B - Center)",
        f"""
        INSERT INTO nodes (id, block_id, device_id, name, tier, status, installed_at)
        VALUES (
            '{NODE_003_ID}',
            '{BLOCK_B_ID}',
            'vg-node-003',
            'Block B - Center',
            'precision_plus',
            'active',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )

    # ------------------------------------------------------------------
    # 4. Gateway  (id, vineyard_id, name, device_id, status)
    # ------------------------------------------------------------------
    print("\n[4/6] Gateway")
    step(
        "Creating Copper Creek Gateway (vg-gw-001)",
        f"""
        INSERT INTO gateways (id, vineyard_id, name, device_id, status)
        VALUES (
            '{GW_001_ID}',
            '{VINEYARD_ID}',
            'Copper Creek Gateway',
            'vg-gw-001',
            'active'
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )

    # ------------------------------------------------------------------
    # 5. Demo user  (id, email, hashed_password, role, is_active, created_at)
    # ------------------------------------------------------------------
    print("\n[5/6] Demo user")
    step(
        "Creating admin@vineguard.demo (role: admin)",
        f"""
        INSERT INTO users (id, email, hashed_password, role, is_active, created_at)
        VALUES (
            '{USER_ID}',
            'admin@vineguard.demo',
            '{DEMO_PASSWORD_HASH}',
            'admin',
            TRUE,
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
        """,
    )

    # ------------------------------------------------------------------
    # 6. Verification
    # ------------------------------------------------------------------
    print("\n[6/6] Verification")
    step(
        "Checking row counts",
        """
        SELECT
            (SELECT COUNT(*) FROM vineyards)    AS vineyards,
            (SELECT COUNT(*) FROM blocks)       AS blocks,
            (SELECT COUNT(*) FROM nodes)        AS nodes,
            (SELECT COUNT(*) FROM gateways)     AS gateways,
            (SELECT COUNT(*) FROM users)        AS users;
        """,
    )

    print()
    print("=" * 60)
    print("Demo data seeded successfully.")
    print()
    print("Credentials")
    print("  Email   : admin@vineguard.demo")
    print("  Password: demo-password-2024")
    print()
    print("Nodes")
    print("  vg-node-001  Block A - North Row  (healthy)")
    print("  vg-node-002  Block A - South Row  (dry-down -> low_moisture alert)")
    print("  vg-node-003  Block B - Center     (mildew risk alert)")
    print()
    print("Start the simulator:")
    print("  docker compose --profile demo up -d simulator")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        seed()
    except RuntimeError as exc:
        print(f"\nSeeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
