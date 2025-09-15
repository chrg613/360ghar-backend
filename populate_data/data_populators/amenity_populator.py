"""Amenity data populator that loads predefined amenities from JSON."""
import json
from typing import Optional, List, Dict, Any
import sys
import os
from sqlalchemy import select, delete

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.models import Amenity
from .base import BasePopulator

class AmenityPopulator(BasePopulator):
    """Populates predefined amenities in the database from JSON seed data."""

    def __init__(self):
        super().__init__()

    def _default_amenities_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "amenities.json")

    def _load_amenities_from_file(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load amenity definitions from JSON."""
        path = file_path or self._default_amenities_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"Amenity JSON not found at: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("amenities.json must contain a list of amenity objects")
        return data

    async def populate(
        self,
        count: Optional[int] = None,
        file_path: Optional[str] = None,
    ) -> int:
        """Create predefined amenities from JSON data."""
        amenities_data = self._load_amenities_from_file(file_path)

        if count is None:
            count = len(amenities_data)

        self.logger.info(f"Creating up to {count} amenities from JSON seed data...")

        created_count = 0

        async with await self.get_db_session() as session:
            try:
                for amenity_data in amenities_data[:count]:
                    try:
                        title = amenity_data.get("title")
                        if not title:
                            self.logger.warning("Skipping amenity without a title in JSON data")
                            continue

                        existing_amenity = await session.execute(
                            select(Amenity).where(Amenity.title == title)
                        )
                        if existing_amenity.scalar_one_or_none():
                            self.logger.debug(f"Amenity '{title}' already exists, skipping...")
                            continue

                        amenity = Amenity(**amenity_data)
                        session.add(amenity)
                        created_count += 1
                        self.logger.debug(f"Created amenity: {title}")

                    except Exception as exc:
                        self.logger.error(f"Failed to create amenity {amenity_data.get('title', '<unknown>')}: {exc}")
                        continue

                await session.commit()
                self.logger.info(f"Successfully created {created_count} amenities")

            except Exception as exc:
                await session.rollback()
                self.logger.error(f"Failed to create amenities: {exc}")
                raise

        return created_count
    
    async def clear_all(self, file_path: Optional[str] = None) -> int:
        """Clear JSON-defined amenities from the database."""
        try:
            try:
                amenities_data = self._load_amenities_from_file(file_path)
                target_titles = [a["title"] for a in amenities_data if a.get("title")]
            except (FileNotFoundError, ValueError) as exc:
                self.logger.warning(f"Unable to load amenity seed data for cleanup: {exc}")
                target_titles = []

            deleted_count = 0

            async with await self.get_db_session() as session:
                if target_titles:
                    for title in target_titles:
                        result = await session.execute(
                            delete(Amenity).where(Amenity.title == title)
                        )
                        deleted_count += result.rowcount or 0
                else:
                    result = await session.execute(delete(Amenity))
                    deleted_count = result.rowcount or 0

                await session.commit()

            self.logger.info(f"Deleted {deleted_count} amenities")
            return deleted_count

        except Exception as exc:
            self.logger.error(f"Failed to clear amenities: {exc}")
            return 0
