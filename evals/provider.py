from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


def call_api(prompt, options, context):
    config = options.get("config", {})
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY；请只在本机终端设置环境变量。")
    payload = {
        "model": config.get("model", "deepseek-v4-flash"),
        "messages": [
            {"role": "system", "content": "Return the answer only. Do not reveal hidden reasoning."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 400,
        "stream": False,
        "thinking": {"type": config.get("thinking", "disabled")},
    }
    if config.get("reasoningEffort"):
        payload["reasoning_effort"] = config["reasoningEffort"]
    request = Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urlopen(request, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
    message = body["choices"][0]["message"]
    return {
        "output": message.get("content", ""),
        "tokenUsage": {
            "prompt": body.get("usage", {}).get("prompt_tokens", 0),
            "completion": body.get("usage", {}).get("completion_tokens", 0),
            "total": body.get("usage", {}).get("total_tokens", 0),
        },
        "metadata": {"promptVersion": config.get("promptVersion", "unknown")},
    }

