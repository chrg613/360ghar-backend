import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_agent")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app.schemas.tour_json import TourJsonSchema

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("Please install google-genai to run this test.")
    sys.exit(1)

def main():
    logger.info("Starting Gemini API Test (via google-genai)...")

    # Load SKILL.md instructions
    skill_path = Path(os.path.abspath("../360-tours/.agents/skills/build-360-tour/SKILL.md"))
    instructions = skill_path.read_text() if skill_path.exists() else ""

    # Get the images from the drive folder
    images_dir = Path(os.path.abspath("../360-tours/drive-download-20260709T101236Z-2-001/"))
    image_files = list(images_dir.glob("*.[jJ][pP]*[gG]")) + list(images_dir.glob("*.[pP][nN][gG]"))
    
    # Limit to 2 images to avoid Gemini API Quota Exceeded errors
    image_files = image_files[:2]
    
    if not image_files:
        logger.error(f"No images found in {images_dir}")
        return

    logger.info(f"Found {len(image_files)} images. Loading them into multimodal context...")
    
    # Initialize GenAI Client
    client = genai.Client()

    contents = []
    # Tell the agent what to do
    contents.append("Here are the panoramas for a property.")
    
    for i, file in enumerate(image_files):
        contents.append(f"Image {i+1} (Filename: {file.name}):")
        with open(file, 'rb') as f:
            contents.append(
                types.Part.from_bytes(data=f.read(), mime_type='image/jpeg' if file.suffix.lower() in ['.jpg', '.jpeg'] else 'image/png')
            )
    
    contents.append("Using the instructions below, build the final connected virtual tour JSON.")

    logger.info("Invoking Gemini 1.5 Flash...")
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",
                response_schema=TourJsonSchema,
            )
        )
        logger.info("\n--- FINAL TOUR JSON ---\n")
        print(response.text)
        logger.info("\n-----------------------\n")
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")

if __name__ == "__main__":
    main()
