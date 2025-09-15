"""Agent data populator that loads seed data from JSON."""
import json
from typing import Optional, List, Dict, Any
import sys
import os
from sqlalchemy import select, delete

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.models import Agent
from app.models.enums import AgentType, ExperienceLevel
from .base import BasePopulator

class AgentPopulator(BasePopulator):
    """Populates 360Ghar agents in the database from JSON seed data."""

    def __init__(self):
        super().__init__()

    def _default_agents_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "agents.json")

    def _load_agents_from_file(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load agent definitions from JSON."""
        path = file_path or self._default_agents_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent JSON not found at: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("agents.json must contain a list of agent objects")
        return data

    def _prepare_agent_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON payload into model friendly structure."""
        payload = dict(raw)

        agent_type_value = payload.get("agent_type")
        if agent_type_value is not None:
            payload["agent_type"] = AgentType(agent_type_value)

        experience_value = payload.get("experience_level")
        if experience_value is not None:
            payload["experience_level"] = ExperienceLevel(experience_value)

        return payload

    async def populate(
        self,
        count: Optional[int] = None,
        file_path: Optional[str] = None,
    ) -> int:
        """
        Create test agents (defaults to all entries found in agents.json).

        Args:
            count: Optional cap on number of agents to create.
            file_path: Optional path to a custom agents.json file.

        Returns:
            Number of agents created.
        """
        agents_data = self._load_agents_from_file(file_path)

        if count is None:
            count = len(agents_data)

        self.logger.info(f"Creating {count} agents from JSON seed data...")

        created_count = 0

        async with await self.get_db_session() as session:
            try:
                for agent_data in agents_data[:count]:
                    try:
                        name = agent_data.get("name")
                        if not name:
                            self.logger.warning("Skipping agent without a name in JSON data")
                            continue

                        existing_agent = await session.execute(
                            select(Agent).where(Agent.name == name)
                        )
                        if existing_agent.scalar_one_or_none():
                            self.logger.info(f"Agent {name} already exists, skipping...")
                            continue

                        payload = self._prepare_agent_payload(agent_data)

                        agent = Agent(**payload)
                        session.add(agent)
                        await session.flush()
                        created_count += 1

                        self.logger.info(f"Created agent: {name}")

                    except Exception as exc:
                        self.logger.error(f"Failed to create agent {agent_data.get('name', '<unknown>')}: {exc}")
                        continue

                await session.commit()
                self.logger.info(f"Successfully created {created_count} agents")

            except Exception as exc:
                await session.rollback()
                self.logger.error(f"Failed to create agents: {exc}")
                raise

        return created_count

    async def clear_all(self, file_path: Optional[str] = None) -> int:
        """Clear JSON-defined agents from the database."""
        try:
            try:
                agents_data = self._load_agents_from_file(file_path)
                target_names = [a["name"] for a in agents_data if a.get("name")]
            except (FileNotFoundError, ValueError) as exc:
                self.logger.warning(f"Unable to load agent seed data for cleanup: {exc}")
                target_names = []

            if not target_names:
                self.logger.info("No agent names found in JSON; skipping cleanup")
                return 0

            deleted_count = 0

            async with await self.get_db_session() as session:
                for name in target_names:
                    result = await session.execute(
                        delete(Agent).where(Agent.name == name)
                    )
                    deleted_count += result.rowcount or 0

                await session.commit()

            self.logger.info(f"Deleted {deleted_count} agents defined in JSON")
            return deleted_count

        except Exception as exc:
            self.logger.error(f"Failed to clear agents: {exc}")
            return 0
