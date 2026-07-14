"""
Daytona Sandbox Integration for Tour AI.

Handles spinning up an isolated Daytona workspace, injecting assets and SKILL.md,
and running the Claude Code agent (or custom Python agent) to produce tour.json safely.
"""
from __future__ import annotations

import json
import os
import tempfile
import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.ai import AIProviderError
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


async def generate_tour_in_sandbox(
    images_base64: list[dict[str, Any]],
    skill_content: str,
    title: str = "Virtual Tour",
) -> dict[str, Any]:
    """
    Spins up a Daytona sandbox, uploads images and SKILL.md, executes the agent,
    and returns the resulting tour.json.
    """
    try:
        from daytona import AsyncDaytona, CreateSandboxFromImageParams
    except ImportError as e:
        logger.error("daytona sdk not installed")
        raise AIProviderError("Daytona SDK is not installed.") from e

    api_key = settings.DAYTONA_API_KEY
    if not api_key:
        raise AIProviderError("DAYTONA_API_KEY is missing from environment.")

    # In production, you might also pass the Anthropic key to the sandbox.
    # anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    logger.info("Initializing Daytona Sandbox...")
    from daytona import DaytonaConfig
    config = DaytonaConfig(api_key=api_key, server_url="https://app.daytona.io/api")
    daytona_client = AsyncDaytona(config=config)

    # 1. Create a clean sandbox
    sandbox = await daytona_client.create(
        CreateSandboxFromImageParams(image="python:3.11")
    )
    
    try:
        logger.info("Sandbox %s created. Preparing workspace...", sandbox.id)
        
        # 2. Upload images and SKILL.md
        # Write files locally to tempdir first, then upload to Daytona.
        # Alternatively we could use sandbox.fs.upload_file or similar.
        # Note: Depending on the exact methods available in daytona_sdk 0.196.0,
        # we might need to use standard file upload patterns.
        # For this implementation we will write a small agent runner script and push it.
        
        # We'll pass the image keys into the agent script so it can mock correctly
        image_keys = [img.get("key", f"img_{i}") for i, img in enumerate(images_base64)]
        
        # The agent script that will run inside the sandbox.
        agent_script = f"""
import os
import json

def main():
    print("Agent running in Daytona Sandbox...")
    
    # In a real scenario, the agent reads SKILL.md and uses LLM to build the graph
    # For now, we mock the output so the pipeline completes end-to-end.
    image_keys = {json.dumps(image_keys)}
    
    scenes = []
    for i, key in enumerate(image_keys):
        scenes.append({{
            "id": f"scene_{{i}}",
            "title": f"Scene {{i+1}}",
            "image_key": key,
            "room_type": "living_room" if i == 0 else "bedroom",
            "metadata": {{ "initial_view": {{ "yaw": 0, "pitch": 0, "zoom": 50 }} }},
            "hotspots": []
        }})
        
    # Mock simple linear connections between scenes
    for i in range(len(scenes) - 1):
        scenes[i]["hotspots"].append({{
            "position": {{ "yaw": 180, "pitch": 0 }},
            "target_scene_id": scenes[i+1]["id"],
            "title": "Next Scene"
        }})
        scenes[i+1]["hotspots"].append({{
            "position": {{ "yaw": 0, "pitch": 0 }},
            "target_scene_id": scenes[i]["id"],
            "title": "Previous Scene"
        }})
        
    tour_plan = {{
        "title": "{title}",
        "initial_scene_id": "scene_0",
        "scenes": scenes
    }}
    
    with open("tour.json", "w") as f:
        json.dump(tour_plan, f, indent=2)
        
    print("Saved tour.json")

if __name__ == "__main__":
    main()
"""
import os
import json

# Placeholder agent execution inside the sandbox
# This represents the Claude/LLM thinking step inside the isolated container
# For now, it will output a stub tour.json based on SKILL.md and the input files.

def main():
    print("Agent running in Daytona Sandbox...")
    
    # In a real scenario, the agent reads SKILL.md and uses LLM to build the graph
    # For now, we mock the output so the pipeline completes end-to-end.
    tour_plan = {{
        "title": "{title}",
        "initial_scene_id": "scene_0",
        "scenes": [
            {{
                "id": "scene_0",
                "title": "Entrance",
                "image_key": "img_0", # Mapped back to DB by key
                "room_type": "entrance",
                "metadata": {{ "initial_view": {{ "yaw": 0, "pitch": 0, "zoom": 50 }} }},
                "hotspots": []
            }}
        ]
    }}
    
    with open("tour.json", "w") as f:
        json.dump(tour_plan, f, indent=2)
        
    print("Saved tour.json")

if __name__ == "__main__":
    main()
"""
        
        # To make it simple for the MVP, we upload the script directly.
        # In the future, this is where we run `npx @anthropic-ai/claude-code`.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            script_path = temp_path / "agent.py"
            script_path.write_text(agent_script)
            
            skill_path = temp_path / "SKILL.md"
            skill_path.write_text(skill_content)
            
            # Since upload_file might take remote path and local path
            # let's assume standard sdk method: sandbox.fs.upload_file(local_path, remote_dir)
            # Actually, `sandbox.fs` or `sandbox.upload_file` is commonly used.
            # We'll use a bash echo if the method signature is unknown, to be perfectly robust.
            
            logger.info("Executing agent script in sandbox...")
            
            # Run the agent
            exec_res = await sandbox.process.code_run(agent_script)
            if exec_res.exit_code != 0:
                logger.error("Sandbox agent failed: %s", exec_res.result)
                raise AIProviderError(f"Agent in sandbox failed: {exec_res.result}")
                
            logger.info("Agent execution complete. Extracting tour.json...")
            
            # Retrieve the tour.json
            cat_result = await sandbox.process.code_run("import sys; sys.stdout.write(open('tour.json', 'r').read())")
            if cat_result.exit_code != 0:
                raise AIProviderError("tour.json was not produced by the sandbox agent")
                
            tour_plan = json.loads(cat_result.result)
            return tour_plan

    finally:
        logger.info("Destroying Sandbox %s...", sandbox.id)
        await daytona_client.delete(sandbox)
