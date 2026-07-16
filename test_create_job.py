import asyncio
from httpx import AsyncClient
from app.main import app

async def test():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Wait, I need authentication. I can just hit the real server with curl, but I need a token.
        pass
