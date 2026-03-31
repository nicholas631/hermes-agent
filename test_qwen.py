import requests
import time

url = "http://127.0.0.1:8085/v1/chat/completions"
payload = {
    "model": "qwen35_27b_q4",
    "messages": [{"role": "user", "content": "Explain the significance of the Turing test in 50 words."}],
    "max_tokens": 100
}

t0 = time.time()
response = requests.post(url, json=payload).json()
t1 = time.time()

usage = response.get('usage', {})
timings = response.get('metadata', {}).get('generation_time_ms', 0)
latency = response.get('latency_ms', (t1 - t0) * 1000)

print(f"Model: {response.get('model')}")
print(f"Tokens Generated: {usage.get('completion_tokens')}")
print(f"Total Latency: {latency:.2f} ms")
print(f"Tokens/Second: {usage.get('completion_tokens', 0) / (latency / 1000):.2f} tok/s")
print(f"Response Preview: {response['choices'][0]['message']['content'][:100]}...")
