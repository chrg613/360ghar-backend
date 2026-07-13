import asyncio
from app.schemas.tour import Tour
from datetime import datetime

async def test():
    t = Tour.model_validate({
        "id": "123",
        "user_id": 1,
        "title": "Test Tour",
        "status": "draft",
        "visibility": "private",
        "view_count": 0,
        "like_count": 0,
        "share_count": 0,
        "is_featured": False,
        "is_public": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    })
    print(t.share_url)
    print(t.embed_code)
    
if __name__ == "__main__":
    asyncio.run(test())
