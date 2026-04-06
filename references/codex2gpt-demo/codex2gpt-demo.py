#!/usr/bin/env python3
"""Minimal demo for the local OpenAI-compatible endpoint.

Usage:
  python3 examples/openai_compatible_demo.py
  python3 examples/openai_compatible_demo.py "用三句话介绍你自己"
  OPENAI_BASE_URL=http://127.0.0.1:18100/v1 python3 examples/openai_compatible_demo.py

If the `openai` SDK is installed, this script uses it first.
Otherwise it falls back to a standard-library HTTP request against
`/v1/chat/completions`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:18100/v1").rstrip("/")
API_KEY = os.environ.get("OPENAI_API_KEY", "dummy")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "你好，用三句话说明你是什么。"


def run_with_openai_sdk() -> str:
    from openai import OpenAI

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        stream=False,
    )
    return response.choices[0].message.content or ""


def run_with_http() -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": False,
    }
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def main() -> int:
    print(f"base_url={BASE_URL}")
    print(f"model={MODEL}")
    print(f"prompt={PROMPT}")
    print()

    try:
        try:
            content = run_with_openai_sdk()
            print("[via openai sdk]")
        except ModuleNotFoundError:
            content = run_with_http()
            print("[via stdlib http]")
        print(content)
        return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
