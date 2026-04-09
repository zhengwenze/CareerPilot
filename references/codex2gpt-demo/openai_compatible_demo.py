#!/usr/bin/env python3
"""Minimal demo for the local OpenAI-compatible endpoint.

Usage:
  python3 examples/openai_compatible_demo.py
  python3 examples/openai_compatible_demo.py "你好"
"""

import json
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:18100/v1"
MODEL = "gpt-5.4"
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "你好，用一句话说明你是什么。"


def main():
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": True,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    chunks = []
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            line = line.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            delta = json.loads(line[6:])["choices"][0].get("delta", {})
            if delta.get("content"):
                chunks.append(delta["content"])
    print("".join(chunks))


if __name__ == "__main__":
    main()
