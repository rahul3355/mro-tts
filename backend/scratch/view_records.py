import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal, engine
from app.core.models import MaintenanceRecord
from sqlalchemy import select

async def main() -> None:
    print("Connecting to database and fetching maintenance records...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(MaintenanceRecord).order_by(MaintenanceRecord.created_at.desc()))
        records = result.scalars().all()
        
        print(f"\nFound {len(records)} records in the database:\n")
        for record in records[:5]:  # Display top 5 most recent records
            print("=" * 60)
            print(f"ID: {record.id}")
            print(f"Created At: {record.created_at}")
            print(f"Transcript: {record.transcript}")
            print(f"Part Name: {record.part_name}")
            print(f"Action: {record.action_performed}")
            print(f"Validation Status: {record.validation_status}")
            print(f"Validation Issues: {record.validation_issues}")
            print(f"Compliance Parameters: {repr(record.compliance_parameters)}")
            print(f"References: {len(record.references_used)}")
            print("=" * 60)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
