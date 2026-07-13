import asyncio
import httpx
from app.core.security import create_access_token
from app.config import settings

async def main():
    # 1. create token for user 1 (assuming user 1 exists)
    token = create_access_token(
        subject=1,
        user_type="normal",
        expires_delta=None
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(base_url="http://localhost:3600") as client:
        # Get tours
        res = await client.get("/api/v1/tours", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get("items"):
                tour = data["items"][0]
                print("Tour ID:", tour["id"])
                print("Share URL:", tour.get("share_url"))
                print("Embed Code:", tour.get("embed_code"))
            else:
                print("No tours found for this user.")
        else:
            print("Failed to fetch tours:", res.status_code, res.text)

if __name__ == "__main__":
    asyncio.run(main())
