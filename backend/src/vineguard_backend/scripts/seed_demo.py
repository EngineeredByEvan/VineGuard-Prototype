from __future__ import annotations

import asyncio

from sqlalchemy import text

from ..auth.security import hash_password
from ..db import get_engine, session_scope
from ..models import Base, Node, Organization, Site, User, UserRole


async def init_schema() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # TimescaleDB hypertable creation (no-op if already created)
        try:
            await conn.execute(
                text("SELECT create_hypertable('telemetry_raw', 'ts', if_not_exists => TRUE);")
            )
        except Exception as exc:  # pragma: no cover - informational only
            print("Warning: could not create hypertable (ensure TimescaleDB extension is installed)")
            print(exc)


async def seed_demo_data() -> None:
    async with session_scope() as session:
        org = await session.get(Organization, "demo-org")
        if org is None:
            org = Organization(org_id="demo-org", name="Demo Organization")
            session.add(org)

        site = await session.get(Site, "niagara-01")
        if site is None:
            site = Site(site_id="niagara-01", name="Niagara Vineyard", org_id=org.org_id)
            session.add(site)

        node = await session.get(Node, "vg-node-0001")
        if node is None:
            node = Node(
                node_id="vg-node-0001",
                name="Row 1 Node",
                org_id=org.org_id,
                site_id=site.site_id,
                location="Block A",
            )
            session.add(node)

        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": "demo@vineguard.io"}
        )
        if result.first() is None:
            session.add(
                User(
                    email="demo@vineguard.io",
                    hashed_password=hash_password("ChangeMe123!"),
                    org_id=org.org_id,
                    role=UserRole.ADMIN,
                )
            )


async def main() -> None:
    await init_schema()
    await seed_demo_data()
    print("Seed data applied")


if __name__ == "__main__":
    asyncio.run(main())
