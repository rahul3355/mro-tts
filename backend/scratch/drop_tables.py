import asyncio
import sys
import os

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import engine

async def main() -> None:
    print("Connecting to database at:", settings.DATABASE_URL.split("@")[-1])

    try:
        print("Dropping legacy database tables...")
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("DROP TABLE IF EXISTS maintenance_records CASCADE;"))
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))

        print("SUCCESS: Neon PostgreSQL database tables dropped successfully!")

    except Exception as e:
        print("FAILURE: Drop tables failed:", e)
        sys.exit(1)

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
