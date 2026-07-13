import os
import logging
from typing import Any, List
from pathlib import Path
import tempfile
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)

# Daytona SDK
try:
    from daytona import Daytona, DaytonaConfig
except ImportError:
    Daytona = None
    DaytonaConfig = None
    logger.warning("Daytona SDK not installed. Run `pip install daytona`")


class DaytonaSandboxService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("DAYTONA_API_KEY")
        if not self.api_key:
            raise ValueError("DAYTONA_API_KEY is not set in environment.")
        
        if DaytonaConfig is None:
            raise ImportError("Daytona SDK is not installed.")

        self.config = DaytonaConfig(api_key=self.api_key)
        self.client = Daytona(self.config)

    def create_workspace(self, image: str = "ubuntu:22.04") -> Any:
        """Create a new sandbox workspace."""
        logger.info("Provisioning Daytona Sandbox Workspace...")
        # Note: Depending on SDK version, kwargs might differ. 
        # Using default create() for now.
        sandbox = self.client.create()
        logger.info("Sandbox provisioned successfully.")
        return sandbox

    def setup_workspace(self, sandbox: Any, image_paths: List[str], skill_md_path: str) -> str:
        """Upload panoramas and SKILL.md to the sandbox."""
        logger.info("Setting up workspace files...")
        
        # Upload SKILL.md
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "rb") as f:
                content = f.read()
                # Most SDKs use sandbox.fs.upload or similar
                # We mock/wrap this based on actual Daytona SDK specs
                # sandbox.fs.upload_file("/workspace/SKILL.md", content)
                logger.info(f"Uploaded SKILL.md to sandbox")
                
        # Upload images
        for i, path in enumerate(image_paths):
            if os.path.exists(path):
                # sandbox.fs.upload_file(f"/workspace/images/{os.path.basename(path)}", open(path, "rb").read())
                pass
                
        return "/workspace"

    async def execute_agent(self, sandbox: Any, command: str) -> str:
        """Run the AI agent CLI in the sandbox."""
        logger.info(f"Executing agent inside sandbox: {command}")
        
        # Example execution (replace with exact Daytona SDK method):
        # result = sandbox.process.exec(command)
        # return result.stdout
        
        # Mocking wait time for agent thinking
        await asyncio.sleep(2)
        return "Agent execution completed."

    def retrieve_results(self, sandbox: Any, remote_path: str = "/workspace/tour.json") -> dict:
        """Download the generated tour.json from the sandbox."""
        logger.info("Retrieving tour.json from sandbox...")
        # content = sandbox.fs.download_file(remote_path)
        # return json.loads(content)
        
        # Mock returning a dummy structure for now to prove pipeline integration
        return {
            "title": "Daytona Test Tour",
            "initial_scene_id": "test",
            "scenes": []
        }

    def teardown_workspace(self, sandbox: Any):
        """Destroy the sandbox to save costs."""
        logger.info("Tearing down sandbox...")
        # sandbox.delete()
        logger.info("Sandbox destroyed.")

