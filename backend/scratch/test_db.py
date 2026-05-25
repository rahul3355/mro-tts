import asyncio
import sys
import os

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import engine, Base

# Import models to ensure they are registered on the Base metadata
from app.core.models import MaintenanceRecord


async def main() -> None:
    print("Connecting to database at:", settings.DATABASE_URL.split("@")[-1])

    try:
        # Create all tables registered on metadata
        print("Initializing database tables...")
        async with engine.begin() as conn:
            # Recreate tables asynchronously
            await conn.run_sync(Base.metadata.create_all)

        print("SUCCESS: Neon PostgreSQL database tables created successfully!")

    except Exception as e:
        print("FAILURE: Connection to Neon PostgreSQL failed:", e)
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
