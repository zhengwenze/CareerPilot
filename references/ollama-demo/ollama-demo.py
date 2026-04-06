import requests
import json

with requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen2.5:7b",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": True,
        "keep_alive": "10m",
    },
    stream=True,
) as r:
    for line in r.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            msg = data.get("message", {}).get("content", "")
            if msg:
                print(msg, end="", flush=True)
