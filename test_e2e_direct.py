import asyncio
import os
import uuid
import datetime
from supabase import create_client
from app.config.settings import settings
from app.services import lab_pipeline
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    
    # 1. Create Job
    job_id = str(uuid.uuid4())
    row = {
        "id": job_id,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "E2E Test Splat",
        "status": "pending",
        "progress": 0,
        "stage_message": "Job queued",
        "is_360_video": True,
        "mask_people": False,
        "quality_preset": "balanced",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    sb.table("splat_jobs").insert(row).execute()
    print(f"Created job: {job_id}")

    # 2. Get upload URL
    storage_path = f"00000000-0000-0000-0000-000000000000/{job_id}/video.mp4"
    bucket = settings.SPLAT_BUCKET_NAME or "splat-jobs"
    signed = sb.storage.from_(bucket).create_signed_upload_url(storage_path)
    upload_url = signed.get("signedURL") or signed.get("signed_url") or signed.get("url")

    # 3. Upload file
    video_path = "/Users/chiragsingh/Desktop/360-tours/videoplayback_compressed.mp4"
    import httpx
    with open(video_path, "rb") as f:
        resp = httpx.put(upload_url, content=f.read(), timeout=600.0)
        if resp.status_code >= 400:
            print("Failed to upload video", resp.text)
            return
    print("Video uploaded.")

    # 4. Mark job as uploading
    sb.table("splat_jobs").update({"status": "uploading", "video_path": storage_path}).eq("id", job_id).execute()

    # 4.5 Reload row
    row = sb.table("splat_jobs").select("*").eq("id", job_id).execute().data[0]

    # 5. Run pipeline
    print("Starting pipeline...")
    await lab_pipeline.run_pipeline(job_id, row)

if __name__ == "__main__":
    asyncio.run(main())
