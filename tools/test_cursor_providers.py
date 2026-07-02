#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor IDE Providers Connection Tester

测试 Cursor IDE 配置的所有 AI 提供商的 API 连接状态。
支持 Anthropic 和 Gemini 类型的提供商。
"""

import json
import time
import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime

# 设置控制台输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import httpx
except ImportError:
    print("错误: 需要安装 httpx 库")
    print("请运行: pip install httpx")
    exit(1)


@dataclass
class ProviderConfig:
    """解析后的提供商配置"""
    id: str
    name: str
    type: Literal["anthropic", "gemini"]
    base_url: str
    api_key: str
    models: List[Dict]


@dataclass
class TestResult:
    """单个测试结果"""
    provider_id: str
    provider_name: str
    provider_type: str
    model_id: str
    model_name: str
    api_model: str
    status: Literal["success", "error", "timeout"]
    response_time_ms: float
    status_code: Optional[int]
    error_message: Optional[str]
    timestamp: str


ERROR_MESSAGES = {
    400: "请求格式错误或不支持的模型",
    401: "认证失败 - API key 无效",
    403: "访问被拒绝 - 检查权限",
    404: "端点未找到 - baseUrl 可能不正确",
    429: "速率限制 - 请稍后重试",
    500: "服务器错误 - 提供商服务问题",
    502: "网关错误 - 代理/路由问题",
    503: "服务不可用 - 临时故障",
    504: "网关超时 - 响应缓慢"
}


class ProviderTester:
    """主测试器类"""

    def __init__(self, config_path: str, timeout: int = 30, verbose: bool = False):
        self.config_path = Path(config_path)
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[TestResult] = []

    def load_config(self) -> List[ProviderConfig]:
        """加载并解析 providers.json"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        providers = []
        for p in config.get("providers", []):
            providers.append(ProviderConfig(
                id=p["id"],
                name=p["name"],
                type=p["type"],
                base_url=p["baseUrl"],
                api_key=p["auth"]["value"],
                models=p["models"]
            ))

        return providers

    async def test_anthropic_model(
        self,
        client: httpx.AsyncClient,
        provider: ProviderConfig,
        model: Dict
    ) -> TestResult:
        """测试 Anthropic 兼容 API"""
        url = f"{provider.base_url}/v1/messages"
        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model["apiModel"],
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }

        start_time = time.time()
        status = "error"
        status_code = None
        error_message = None

        try:
            response = await client.post(url, headers=headers, json=payload)
            response_time = (time.time() - start_time) * 1000
            status_code = response.status_code

            if response.status_code == 200:
                status = "success"
                if self.verbose:
                    print(f"    响应: {response.json()}")
            else:
                error_message = ERROR_MESSAGES.get(
                    response.status_code,
                    f"HTTP {response.status_code}"
                )
                try:
                    error_detail = response.json()
                    if "error" in error_detail:
                        error_message += f" - {error_detail['error'].get('message', '')}"
                except:
                    pass

        except httpx.TimeoutException:
            response_time = self.timeout * 1000
            status = "timeout"
            error_message = f"请求超时 ({self.timeout}秒)"

        except httpx.ConnectError as e:
            response_time = (time.time() - start_time) * 1000
            error_message = f"连接失败 - 检查 baseUrl: {str(e)}"

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_message = f"未知错误: {str(e)}"

        return TestResult(
            provider_id=provider.id,
            provider_name=provider.name,
            provider_type=provider.type,
            model_id=model["id"],
            model_name=model["displayName"],
            api_model=model["apiModel"],
            status=status,
            response_time_ms=round(response_time, 2),
            status_code=status_code,
            error_message=error_message,
            timestamp=datetime.now().isoformat()
        )

    async def test_gemini_model(
        self,
        client: httpx.AsyncClient,
        provider: ProviderConfig,
        model: Dict
    ) -> TestResult:
        """测试 Gemini API"""
        model_name = model["apiModel"]
        url = f"{provider.base_url}/v1beta/models/{model_name}:generateContent"
        headers = {
            "x-api-key": provider.api_key,
            "content-type": "application/json"
        }
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": "Hello"}]
            }],
            "generationConfig": {
                "maxOutputTokens": 10
            }
        }

        start_time = time.time()
        status = "error"
        status_code = None
        error_message = None

        try:
            response = await client.post(url, headers=headers, json=payload)
            response_time = (time.time() - start_time) * 1000
            status_code = response.status_code

            if response.status_code == 200:
                status = "success"
                if self.verbose:
                    print(f"    响应: {response.json()}")
            else:
                error_message = ERROR_MESSAGES.get(
                    response.status_code,
                    f"HTTP {response.status_code}"
                )
                try:
                    error_detail = response.json()
                    if "error" in error_detail:
                        error_message += f" - {error_detail['error'].get('message', '')}"
                except:
                    pass

        except httpx.TimeoutException:
            response_time = self.timeout * 1000
            status = "timeout"
            error_message = f"请求超时 ({self.timeout}秒)"

        except httpx.ConnectError as e:
            response_time = (time.time() - start_time) * 1000
            error_message = f"连接失败 - 检查 baseUrl: {str(e)}"

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_message = f"未知错误: {str(e)}"

        return TestResult(
            provider_id=provider.id,
            provider_name=provider.name,
            provider_type=provider.type,
            model_id=model["id"],
            model_name=model["displayName"],
            api_model=model["apiModel"],
            status=status,
            response_time_ms=round(response_time, 2),
            status_code=status_code,
            error_message=error_message,
            timestamp=datetime.now().isoformat()
        )

    async def test_provider(
        self,
        client: httpx.AsyncClient,
        provider: ProviderConfig,
        provider_num: int,
        total_providers: int
    ) -> List[TestResult]:
        """测试单个提供商的所有模型"""
        print(f"\n[{provider_num}/{total_providers}] Provider: {provider.name} ({provider.type})")

        results = []
        for model in provider.models:
            model_name = model["displayName"]

            if provider.type == "anthropic":
                result = await self.test_anthropic_model(client, provider, model)
            elif provider.type == "gemini":
                result = await self.test_gemini_model(client, provider, model)
            else:
                result = TestResult(
                    provider_id=provider.id,
                    provider_name=provider.name,
                    provider_type=provider.type,
                    model_id=model["id"],
                    model_name=model_name,
                    api_model=model["apiModel"],
                    status="error",
                    response_time_ms=0,
                    status_code=None,
                    error_message=f"不支持的提供商类型: {provider.type}",
                    timestamp=datetime.now().isoformat()
                )

            results.append(result)

            # 打印结果
            status_icon = {
                "success": "✓",
                "error": "✗",
                "timeout": "⏱"
            }[result.status]

            status_text = f"{result.response_time_ms:.0f}ms"
            if result.status_code:
                status_text += f" ({result.status_code} OK)" if result.status == "success" else f" ({result.status_code})"

            print(f"  {'└─' if model == provider.models[-1] else '├─'} {model_name}: {status_icon} {status_text}")

            if result.error_message and result.status != "success":
                print(f"     错误: {result.error_message}")

        return results

    async def test_all_providers(self, parallel: bool = False) -> List[TestResult]:
        """测试所有提供商"""
        providers = self.load_config()

        print("Testing Cursor IDE Providers...")
        print("━" * 50)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(self.timeout),
                write=10.0,
                pool=5.0
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=True,
            verify=True
        ) as client:
            if parallel:
                tasks = [
                    self.test_provider(client, p, i+1, len(providers))
                    for i, p in enumerate(providers)
                ]
                results_lists = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results_lists:
                    if isinstance(r, list):
                        self.results.extend(r)
            else:
                for i, provider in enumerate(providers, 1):
                    results = await self.test_provider(client, provider, i, len(providers))
                    self.results.extend(results)
                    if i < len(providers):
                        await asyncio.sleep(1)

        return self.results

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "━" * 50)
        print("Summary:")

        success = sum(1 for r in self.results if r.status == "success")
        errors = sum(1 for r in self.results if r.status == "error")
        timeouts = sum(1 for r in self.results if r.status == "timeout")

        print(f"  Total tests: {len(self.results)}")
        print(f"  ✓ Success: {success}")
        print(f"  ✗ Errors: {errors}")
        print(f"  ⏱ Timeouts: {timeouts}")

        if success > 0:
            successful_results = [r for r in self.results if r.status == "success"]
            avg_time = sum(r.response_time_ms for r in successful_results) / len(successful_results)
            fastest = min(successful_results, key=lambda r: r.response_time_ms)
            slowest = max(successful_results, key=lambda r: r.response_time_ms)

            print(f"\n  Avg response time: {avg_time:.0f}ms")
            print(f"  Fastest: {fastest.response_time_ms:.0f}ms ({fastest.provider_name}/{fastest.model_name})")
            print(f"  Slowest: {slowest.response_time_ms:.0f}ms ({slowest.provider_name}/{slowest.model_name})")

    def export_results(self, output_path: str):
        """导出结果到 JSON 文件"""
        success = sum(1 for r in self.results if r.status == "success")
        errors = sum(1 for r in self.results if r.status == "error")
        timeouts = sum(1 for r in self.results if r.status == "timeout")

        successful_results = [r for r in self.results if r.status == "success"]
        avg_time = sum(r.response_time_ms for r in successful_results) / len(successful_results) if successful_results else 0

        providers = self.load_config()

        output = {
            "test_timestamp": datetime.now().isoformat(),
            "total_providers": len(providers),
            "total_models": len(self.results),
            "summary": {
                "success": success,
                "errors": errors,
                "timeouts": timeouts,
                "avg_response_time_ms": round(avg_time, 2)
            },
            "results": [asdict(r) for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="测试 Cursor IDE AI 提供商连接"
    )
    parser.add_argument(
        "--config",
        default=r"c:\Users\Administrator\.ccursor\providers.json",
        help="providers.json 文件路径"
    )
    parser.add_argument(
        "--output",
        default=r"d:\安装包归档\咏彩booth\tools\provider_test_results.json",
        help="输出 JSON 文件路径"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间（秒）"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="并行测试所有提供商"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )

    args = parser.parse_args()

    tester = ProviderTester(
        config_path=args.config,
        timeout=args.timeout,
        verbose=args.verbose
    )

    await tester.test_all_providers(parallel=args.parallel)
    tester.print_summary()
    tester.export_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())
