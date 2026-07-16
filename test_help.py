import modal
import subprocess

app = modal.App("test-help")

image = (
    modal.Image.from_registry("pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "Etc/UTC"})
    .apt_install("git", "build-essential", "ninja-build", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install("numpy<2.0.0", "nerfstudio==1.1.3")
    .apt_install("colmap")
)

@app.function(image=image)
def get_help():
    print(subprocess.run(["ns-process-data", "--help"], capture_output=True, text=True).stdout)

@app.local_entrypoint()
def main():
    get_help.remote()
