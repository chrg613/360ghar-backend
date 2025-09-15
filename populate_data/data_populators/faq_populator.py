"""FAQ data populator that loads FAQs from JSON."""
import json
from typing import Optional, List, Dict, Any
import sys
import os
from sqlalchemy import select, delete, update

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.models import FAQ
from .base import BasePopulator


class FAQPopulator(BasePopulator):
    """Populates FAQs in the database from JSON seed data."""

    def __init__(self):
        super().__init__()

    def _default_faqs_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "faqs.json")

    def _load_faqs_from_file(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load FAQ definitions from JSON."""
        path = file_path or self._default_faqs_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"FAQ JSON not found at: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("faqs.json must contain a list of FAQ objects")
        return data

    def _prepare_faq_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize FAQ payload prior to database insertion/update."""
        payload = dict(raw)

        # Default toggles for optional fields
        payload.setdefault("category", None)
        payload.setdefault("tags", None)
        payload.setdefault("display_order", 0)
        payload.setdefault("is_active", True)

        return payload

    async def populate(
        self,
        count: Optional[int] = None,
        file_path: Optional[str] = None,
        update_existing: bool = False,
    ) -> int:
        """Create (and optionally update) FAQs from JSON seed data."""
        faqs_data = self._load_faqs_from_file(file_path)

        if count is None:
            count = len(faqs_data)

        self.logger.info(
            f"Creating up to {count} FAQs from JSON seed data{' with updates' if update_existing else ''}..."
        )

        created_count = 0
        updated_count = 0

        async with await self.get_db_session() as session:
            try:
                for faq_data in faqs_data[:count]:
                    try:
                        question = faq_data.get("question")
                        if not question:
                            self.logger.warning("Skipping FAQ without a question in JSON data")
                            continue

                        existing_faq = await session.execute(
                            select(FAQ).where(FAQ.question == question)
                        )
                        existing = existing_faq.scalar_one_or_none()

                        if existing:
                            if update_existing:
                                payload = self._prepare_faq_payload(faq_data)
                                await session.execute(
                                    update(FAQ)
                                    .where(FAQ.id == existing.id)
                                    .values(**payload)
                                )
                                updated_count += 1
                                self.logger.debug(f"Updated FAQ: {question}")
                            else:
                                self.logger.debug(
                                    f"FAQ '{question}' already exists, skipping (use --update to update)."
                                )
                            continue

                        payload = self._prepare_faq_payload(faq_data)
                        faq = FAQ(**payload)
                        session.add(faq)
                        created_count += 1
                        self.logger.debug(f"Created FAQ: {question}")

                    except Exception as exc:
                        self.logger.error(
                            f"Failed to process FAQ {faq_data.get('question', '<unknown>')}: {exc}"
                        )
                        continue

                await session.commit()
                self.logger.info(
                    f"FAQs processed. Created: {created_count}, Updated: {updated_count}"
                )
                return created_count

            except Exception as exc:
                await session.rollback()
                self.logger.error(f"Failed to populate FAQs: {exc}")
                raise

    async def clear_all(self, file_path: Optional[str] = None) -> int:
        """Delete FAQs defined in JSON from the database."""
        try:
            try:
                faqs_data = self._load_faqs_from_file(file_path)
                target_questions = [faq["question"] for faq in faqs_data if faq.get("question")]
            except (FileNotFoundError, ValueError) as exc:
                self.logger.warning(f"Unable to load FAQ seed data for cleanup: {exc}")
                target_questions = []

            deleted_count = 0

            async with await self.get_db_session() as session:
                if target_questions:
                    for question in target_questions:
                        result = await session.execute(
                            delete(FAQ).where(FAQ.question == question)
                        )
                        deleted_count += result.rowcount or 0
                else:
                    result = await session.execute(delete(FAQ))
                    deleted_count = result.rowcount or 0

                await session.commit()

            self.logger.info(f"Deleted {deleted_count} FAQs")
            return deleted_count

        except Exception as exc:
            self.logger.error(f"Failed to clear FAQs: {exc}")
            return 0
