import asyncio
from dotenv import load_dotenv; load_dotenv(override=True)
import os
print("DAYTONA KEY:", os.getenv("DAYTONA_API_KEY"))

from app.services import lab_pipeline
from app.config.settings import settings
from supabase import create_client

async def peek():
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    jobs = sb.table("splat_jobs").select("*").order("created_at", desc=True).limit(1).execute()
    sandbox_id = jobs.data[0]["daytona_sandbox_id"]
    print("SANDBOX:", sandbox_id)
    res = await lab_pipeline.exec_in_sandbox(sandbox_id, "tail -n 25 /home/daytona/workspace/pipeline.log")
    print("OUTPUT:\n", res.get("result"))

asyncio.run(peek())
