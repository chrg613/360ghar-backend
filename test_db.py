import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.users import User

async def main():
    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.id == 1))
        user = res.scalar_one_or_none()
        if user:
            print(f"User 1 supabase_user_id: {user.supabase_user_id}")
        else:
            print("User 1 not found")

asyncio.run(main())
