import asyncio
from app.core.database import AsyncSessionLocal
from app.services.tour_ai import spatial_connect_existing_tour
from app.services.tour.tours import get_tour
from app.services.tour.scenes import get_scenes
from app.services.tour.hotspots import get_hotspots

async def main():
    tour_id = "dd6138be-ccf3-4c26-810c-25a564a940b2"
    user_id = 1
    async with AsyncSessionLocal() as db:
        print(f"Starting spatial connect for tour {tour_id} owned by {user_id}...")
        job = await spatial_connect_existing_tour(db=db, tour_id=tour_id, user_id=user_id)
        print(f"Job created: {job}")
        
        # We need to wait for the background job to finish. 
        # But spatial_connect_existing_tour runs in background via run_in_background.
        # So we can just sleep and poll the job status.
        from app.services.tour_ai.jobs import get_ai_job
        while True:
            j = await get_ai_job(db, job.id)
            print(f"Status: {j.status}, Progress: {j.progress}")
            if j.status in ['completed', 'failed', 'cancelled']:
                break
            await asyncio.sleep(5)
            
        print("\n--- RESULTS ---")
        scenes = await get_scenes(db, tour_id)
        for s in scenes:
            print(f"Scene: {s.title} ({s.room_type})")
            hotspots = await get_hotspots(db, scene_id=s.id)
            for h in hotspots:
                print(f"  -> Hotspot: {h.type} to {h.target_scene_id} at yaw={h.yaw}, pitch={h.pitch}")

if __name__ == "__main__":
    asyncio.run(main())
