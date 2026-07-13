import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import Image

async def main():
    config = LocalAgentConfig()
    images_dir = Path(os.path.abspath("../360-tours/drive-download-20260709T101236Z-2-001/"))
    image_files = list(images_dir.glob("*.[jJ][pP]*[gG]"))[:2]
    
    if not image_files:
        print("No images found.")
        return

    img1 = Image.from_file(str(image_files[0]))
    img2 = Image.from_file(str(image_files[1]))
    
    async with Agent(config) as agent:
        print("Sending 2 images...")
        try:
            response = await agent.chat(["Image 1:", img1, "Image 2:", img2])
            print("Success")
            print(await response.text())
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
