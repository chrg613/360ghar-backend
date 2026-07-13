import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_sandbox")

# Add the app directory to sys.path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.tour_ai.daytona_sandbox import DaytonaSandboxService

async def main():
    logger.info("Starting Daytona Sandbox Test Pipeline...")
    
    try:
        service = DaytonaSandboxService()
    except Exception as e:
        logger.error(f"Failed to initialize Daytona Sandbox Service: {e}")
        return

    sandbox = None
    try:
        # Step 1: Provision the Sandbox
        sandbox = service.create_workspace()
        
        # Step 2: Setup workspace with mock files
        image_paths = [] # Add dummy paths if you have them locally
        skill_path = os.path.abspath("../360-tours/.agents/skills/build-360-tour/SKILL.md")
        
        workspace_dir = service.setup_workspace(sandbox, image_paths, skill_path)
        
        # Step 3: Run the Agent
        # If using google-antigravity, command would be `agy --skill build-360-tour`
        # If using Claude, command would be `claude`
        command = "echo 'Agent is running...'" 
        
        output = await service.execute_agent(sandbox, command)
        logger.info(f"Agent Output: {output}")
        
        # Step 4: Retrieve Results
        results = service.retrieve_results(sandbox)
        logger.info(f"Final tour.json: {results}")

    except Exception as e:
        logger.error(f"Error during sandbox execution: {e}")
    finally:
        # Step 5: Teardown
        if sandbox:
            service.teardown_workspace(sandbox)

if __name__ == "__main__":
    asyncio.run(main())
