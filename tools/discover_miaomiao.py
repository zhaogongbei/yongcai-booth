#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喵喵渠道模型发现脚本

策略: 测试常见模型名称,找出可用的
"""

import json
import os
import time
import asyncio
import sys
import io
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import httpx
except ImportError:
    print("错误: 需要安装 httpx")
    sys.exit(1)

BASE_URL = "https://new-api.rugao.me"
API_KEY = os.getenv("MIAOMIAO_API_KEY", "")
MAX_CONCURRENCY = 2
DATE_QUESTION = "今天几号?"

# 常见模型名称库
CANDIDATE_MODELS = [
    # Claude
    "claude-opus-4-8", "claude-sonnet-4-6", "claude-sonnet-4-5",
    "claude-opus-4-7", "claude-haiku-4-5",
    # DeepSeek
    "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-ai/deepseek-v4-pro",
    # Gemini
    "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash",
    # GLM
    "glm-5.1", "glm-5", "z-ai/glm-5.1",
    # Qwen
    "qwen3.7-plus", "qwen3.5-plus",
]


async def test_model(client, model_name):
    """测试单个模型是否可用"""
    # Anthropic 格式
    url = f"{BASE_URL}/v1/messages"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": DATE_QUESTION}],
        "max_tokens": 30,
        "stream": True,
    }

    t0 = time.time()
    status_code = None
    text_acc = ""
    error = None

    try:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            status_code = resp.status_code

            if status_code != 200:
                # 读取错误信息
                body = await resp.aread()
                error = body.decode('utf-8', errors='ignore')[:150]
            else:
                async for line in resp.aiter_lines():
                    if line and line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            d = json.loads(line[6:])
                            delta = (d.get("delta") or {})
                            t = delta.get("text") or delta.get("content") or ""
                            text_acc += t
                        except:
                            pass

    except httpx.TimeoutException:
        error = "超时"
    except Exception as e:
        error = str(e)[:100]

    elapsed = round((time.time() - t0) * 1000, 0)
    ok = (status_code == 200 and text_acc.strip())

    return {
        "model": model_name,
        "ok": ok,
        "http": status_code,
        "ms": elapsed,
        "sample": text_acc.strip()[:40] if ok else "",
        "error": error,
    }


async def main():
    if not API_KEY:
        print("错误: 请通过环境变量 MIAOMIAO_API_KEY 配置 API Key")
        return []
    print("=" * 60)
    print("喵喵渠道模型发现 (并发2)")
    print("=" * 60)
    print()

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def guarded(m):
        async with sem:
            result = await test_model(client, m)
            icon = "✓" if result["ok"] else "✗"
            print(f"[{icon}] {result['model']:35s} {result['ms']:6.0f}ms HTTP {result['http']}")
            if result["sample"]:
                print(f"    回复: {result['sample']}")
            if result["error"] and not result["ok"]:
                print(f"    错误: {result['error'][:80]}")
            return result

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
    ) as client:
        tasks = [guarded(m) for m in CANDIDATE_MODELS]
        results = await asyncio.gather(*tasks)

    # 汇总可用模型
    available = [r for r in results if r["ok"]]
    print()
    print("=" * 60)
    print(f"发现 {len(available)} 个可用模型:")
    print("=" * 60)
    for r in available:
        print(f"  {r['model']}")

    return available


if __name__ == "__main__":
    asyncio.run(main())

