import json

with open("app/services/tour_ai/daytona_service.py", "r") as f:
    content = f.read()

replacement = """
        # We'll pass the image keys into the agent script so it can mock correctly
        image_keys = [img.get("key", f"img_{i}") for i, img in enumerate(images_base64)]
        
        # The agent script that will run inside the sandbox.
        agent_script = f\"\"\"
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
\"\"\"
"""

import re
pattern = re.compile(r'\n        # The agent script that will run inside the sandbox\..*?\"\"\"\n', re.DOTALL)
new_content = pattern.sub(replacement, content)

with open("app/services/tour_ai/daytona_service.py", "w") as f:
    f.write(new_content)
