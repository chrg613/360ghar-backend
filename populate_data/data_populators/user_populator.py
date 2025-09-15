"""User data populator that loads seed users from JSON."""
import json
import uuid
from datetime import date
from typing import Optional, List, Dict, Any
import sys
import os
from sqlalchemy import select, delete

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.models import User
from .base import BasePopulator

class UserPopulator(BasePopulator):
    """Populates test users in the database from JSON seed data."""

    def __init__(self):
        super().__init__()

    def _default_users_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "users.json")

    def _load_users_from_file(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load user definitions from JSON."""
        path = file_path or self._default_users_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"User JSON not found at: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("users.json must contain a list of user objects")
        return data

    def _prepare_user_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON payload into model friendly structure."""
        payload = dict(raw)

        supabase_id = payload.get("supabase_user_id")
        if not supabase_id:
            payload["supabase_user_id"] = str(uuid.uuid4())

        dob = payload.get("date_of_birth")
        if isinstance(dob, str):
            try:
                payload["date_of_birth"] = date.fromisoformat(dob)
            except ValueError:
                self.logger.warning(
                    f"Invalid date_of_birth '{dob}' for user {payload.get('email')}; using defaults"
                )
                payload["date_of_birth"] = date.today()
        elif not isinstance(dob, date):
            payload["date_of_birth"] = date.today()

        # Ensure JSON fields are dicts (None defaults to empty dict)
        for key in ("preferences", "notification_settings", "privacy_settings"):
            value = payload.get(key)
            if value is None:
                payload[key] = {}

        return payload

    async def populate(
        self,
        count: Optional[int] = None,
        file_path: Optional[str] = None,
    ) -> int:
        """
        Create test users (defaults to users defined in users.json).

        Args:
            count: Optional cap on number of users to create.
            file_path: Optional path to a custom users.json file.

        Returns:
            Number of users created.
        """
        users_data = self._load_users_from_file(file_path)

        if count is None:
            count = len(users_data)

        self.logger.info(f"Creating {count} users from JSON seed data...")

        created_count = 0

        async with await self.get_db_session() as session:
            try:
                for user_data in users_data[:count]:
                    try:
                        email = user_data.get("email")
                        if not email:
                            self.logger.warning("Skipping user without an email in JSON data")
                            continue

                        existing_user = await session.execute(
                            select(User).where(User.email == email)
                        )
                        if existing_user.scalar_one_or_none():
                            self.logger.info(f"User {email} already exists, skipping...")
                            continue

                        payload = self._prepare_user_payload(user_data)

                        user = User(**payload)
                        session.add(user)
                        await session.flush()
                        created_count += 1

                        self.logger.info(f"Created user: {payload.get('full_name')} ({email})")

                    except Exception as exc:
                        self.logger.error(f"Failed to create user {user_data.get('email', '<unknown>')}: {exc}")
                        continue

                await session.commit()
                self.logger.info(f"Successfully created {created_count} users")

            except Exception as exc:
                await session.rollback()
                self.logger.error(f"Failed to create users: {exc}")
                raise

        return created_count
    
    async def clear_all(self, file_path: Optional[str] = None) -> int:
        """Clear JSON-defined users from the database."""
        try:
            try:
                users_data = self._load_users_from_file(file_path)
                target_emails = [u["email"] for u in users_data if u.get("email")]
            except (FileNotFoundError, ValueError) as exc:
                self.logger.warning(f"Unable to load user seed data for cleanup: {exc}")
                target_emails = []

            if not target_emails:
                self.logger.info("No user emails found in JSON; skipping cleanup")
                return 0

            deleted_count = 0

            async with await self.get_db_session() as session:
                for email in target_emails:
                    result = await session.execute(
                        delete(User).where(User.email == email)
                    )
                    deleted_count += result.rowcount or 0

                await session.commit()

            self.logger.info(f"Deleted {deleted_count} users defined in JSON")
            return deleted_count

        except Exception as exc:
            self.logger.error(f"Failed to clear users: {exc}")
            return 0
