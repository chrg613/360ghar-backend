import modal
import subprocess
from pathlib import Path

app = modal.App("splat-lab-gpu")

image = (
    modal.Image.from_registry("pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "Etc/UTC"})
    .apt_install("git", "build-essential", "ninja-build", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install("nerfstudio==1.1.3", "gsplat==1.0.0")
)

@app.local_entrypoint()
def main():
    print(debug_ns.remote())

@app.function(gpu="A10G", image=image)
def debug_ns():
    try:
        r = subprocess.run(["ns-process-data", "video", "--help"], capture_output=True, text=True)
        return r.stdout + "\n" + r.stderr
    except Exception as e:
        return f"EXCEPTION: {str(e)}"
