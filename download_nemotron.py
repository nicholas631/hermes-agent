import os
from huggingface_hub import hf_hub_download

print("Downloading Nemotron-Cascade to K:\\models\\nemotron_cascade...")
os.makedirs("K:\\models\\nemotron_cascade", exist_ok=True)
path = hf_hub_download(
    repo_id="bartowski/nvidia_Nemotron-Cascade-2-30B-A3B-GGUF",
    filename="nvidia_Nemotron-Cascade-2-30B-A3B-IQ4_XS.gguf",
    local_dir="K:\\models\\nemotron_cascade"
)
print(f"Downloaded to {path}")
