import asyncio
import httpx
import os, sys, time

async def main():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create job
        print("Creating job...")
        resp = await client.post("http://localhost:8000/api/v1/lab/jobs", json={
            "title": "E2E Test Splat",
            "is_360_video": True,
            "mask_people": False,
            "quality_preset": "balanced"
        })
        if resp.status_code != 201:
            print("Failed to create job", resp.text)
            return
        
        job_id = resp.json()["id"]
        print(f"Created job: {job_id}")

        # 2. Get upload URL
        print("Getting upload URL...")
        resp = await client.post(f"http://localhost:8000/api/v1/lab/jobs/{job_id}/upload-video")
        if resp.status_code != 200:
            print("Failed to get upload URL", resp.text)
            return
        
        upload_url = resp.json()["upload_url"]
        print("Got upload URL. Uploading video...")

        # 3. Upload video
        video_path = "/Users/chiragsingh/Desktop/360-tours/videoplayback (1).mp4"
        with open(video_path, "rb") as f:
            put_resp = await client.put(upload_url, content=f)
            if put_resp.status_code >= 400:
                print("Failed to upload video", put_resp.text)
                return
        print("Upload successful.")

        # 4. Start job
        print("Starting job...")
        resp = await client.post(f"http://localhost:8000/api/v1/lab/jobs/{job_id}/start")
        if resp.status_code != 200:
            print("Failed to start job", resp.text)
            return
        print("Job started successfully. Tracking progress...")

        # 5. Track progress
        while True:
            resp = await client.get(f"http://localhost:8000/api/v1/lab/jobs/{job_id}")
            data = resp.json()
            print(f"Status: {data['status']}, Progress: {data['progress']}%, Msg: {data['stage_message']}")
            if data['status'] in ("ready", "failed"):
                if data['status'] == "failed":
                    print("Error:", data.get('error_message'))
                break
            time.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
