import os
from huggingface_hub import hf_hub_download

print("Downloading Hermes-4.3-36B.Q4_K_M.gguf to K:\\models\\hermes_4_3_36b...")
os.makedirs("K:\\models\\hermes_4_3_36b", exist_ok=True)
path = hf_hub_download(
    repo_id="MaziyarPanahi/Hermes-4.3-36B-GGUF",
    filename="Hermes-4.3-36B.Q4_K_M.gguf",
    local_dir="K:\\models\\hermes_4_3_36b"
)
print(f"Downloaded to {path}")
