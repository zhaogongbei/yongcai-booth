#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Providers 合规连通性测试

约束:
- 不测活(不调用 /models 列表端点,只发真实对话请求)
- 并发 = 2
- 单渠道 1 分钟内 <= 4 个模型
- 测试问题: 日期 (验证模型真实回复)
- 流式测试 (模拟 Cursor 实际调用)
"""

import json
import time
import asyncio
import sys
import io
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import httpx
except ImportError:
    print("错误: 需要安装 httpx  (pip install httpx)")
    sys.exit(1)

CONFIG_PATH = r"c:\Users\Administrator\.ccursor\providers.json"
MAX_CONCURRENCY = 2
MAX_MODELS_PER_PROVIDER = 4
DATE_QUESTION = "今天是几月几号?请用简体中文回答。"
REQUEST_TIMEOUT = 40.0


def load_providers():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)["providers"]


async def stream_one(client, provider, model):
    """流式测试单个模型,返回结果字典"""
    ptype = provider["type"]
    base = provider["baseUrl"]
    key = provider["auth"]["value"]
    t0 = time.time()
    status = "error"
    status_code = None
    err = None
    sample = ""

    try:
        if ptype == "anthropic":
            url = f"{base}/v1/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model["apiModel"],
                "messages": [{"role": "user", "content": DATE_QUESTION}],
                "max_tokens": 60,
                "stream": True,
            }
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                status_code = resp.status_code
                text_acc = ""
                async for line in resp.aiter_lines():
                    if line and line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            d = json.loads(line[6:])
                            for ev in d.get("events", d.get("items", [])) if isinstance(d, dict) else []:
                                pass
                            delta = (d.get("delta") or {})
                            t = delta.get("text") or delta.get("content") or ""
                            text_acc += t
                        except Exception:
                            pass
                if resp.status_code == 200 and text_acc.strip():
                    status = "success"
                    sample = text_acc.strip()[:60]
                else:
                    status = "error"
                    err = f"HTTP {resp.status_code} 无有效文本"

        elif ptype in ("openai-chat", "openai"):
            url = f"{base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "content-type": "application/json",
            }
            payload = {
                "model": model["apiModel"],
                "messages": [{"role": "user", "content": DATE_QUESTION}],
                "max_tokens": 60,
                "stream": True,
            }
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                status_code = resp.status_code
                text_acc = ""
                async for line in resp.aiter_lines():
                    if line and line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            d = json.loads(line[6:])
                            ch = d.get("choices") or []
                            if ch:
                                delta = ch[0].get("delta") or {}
                                t = delta.get("content") or ""
                                text_acc += t
                        except Exception:
                            pass
                if resp.status_code == 200 and text_acc.strip():
                    status = "success"
                    sample = text_acc.strip()[:60]
                else:
                    status = "error"
                    err = f"HTTP {resp.status_code} 无有效文本"

        else:
            err = f"不支持的 type: {ptype}"

    except httpx.TimeoutException:
        status = "timeout"
        err = f"超时({REQUEST_TIMEOUT}s)"
    except httpx.ConnectError as e:
        err = f"连接失败: {str(e)[:80]}"
    except Exception as e:
        err = f"异常: {str(e)[:120]}"

    elapsed = round((time.time() - t0) * 1000, 0)
    return {
        "provider": provider["name"],
        "type": ptype,
        "model": model["displayName"],
        "api_model": model["apiModel"],
        "status": status,
        "http": status_code,
        "ms": elapsed,
        "sample": sample,
        "error": err,
    }


async def test_provider(client, provider):
    """测试单个渠道,限制最多 MAX_MODELS_PER_PROVIDER 个模型"""
    models = provider.get("models", [])
    if not models:
        return [{
            "provider": provider["name"],
            "type": provider["type"],
            "model": "(空)",
            "api_model": "",
            "status": "error",
            "http": None,
            "ms": 0,
            "sample": "",
            "error": "无模型配置",
        }]

    # 限制每渠道最多4个模型
    selected = models[:MAX_MODELS_PER_PROVIDER]
    print(f"\n[{provider['name']}] 测试 {len(selected)}/{len(models)} 个模型 (并发={MAX_CONCURRENCY})")

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def guarded(m):
        async with sem:
            return await stream_one(client, provider, m)

    tasks = [guarded(m) for m in selected]
    results = await asyncio.gather(*tasks)
    for r in results:
        icon = {"success": "OK", "error": "FAIL", "timeout": "TMO"}[r["status"]]
        print(f"  [{icon}] {r['model']:20s} {r['ms']:6.0f}ms HTTP {r['http']}")
        if r["sample"]:
            print(f"        回复: {r['sample']}")
        if r["error"]:
            print(f"        错误: {r['error']}")
    return results


async def main():
    providers = load_providers()
    targets = [p for p in providers if p["name"] in ("干草铺VIP", "喵喵")]

    print("=" * 60)
    print("合规连通性测试 (并发2 / 单渠道≤4 / 日期问题 / 流式)")
    print("=" * 60)

    all_results = []
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10.0),
        follow_redirects=True,
    ) as client:
        for p in targets:
            res = await test_provider(client, p)
            all_results.extend(res)

    # 汇总
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    ok = sum(1 for r in all_results if r["status"] == "success")
    print(f"成功 {ok}/{len(all_results)}")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
