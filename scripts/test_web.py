#!/usr/bin/env python3
"""Web 功能自动测试脚本。

测试所有 Web 页面和 API 端点，确保功能正常。

用法：
    python scripts/test_web.py                    # 测试所有端点
    python scripts/test_web.py --url http://...   # 指定 URL
    python scripts/test_web.py --verbose          # 详细输出
    python scripts/test_web.py --quick            # 快速模式（跳过耗时测试）
    python scripts/test_web.py --skip-ai          # 跳过 AI 相关测试
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 默认配置
DEFAULT_URL = "http://localhost:8000"
TIMEOUT = 10


class WebTester:
    """Web 功能测试器。"""

    def __init__(self, base_url: str, verbose: bool = False, quick: bool = False, skip_ai: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.quick = quick
        self.skip_ai = skip_ai
        self.results = []
        self.client = httpx.Client(timeout=TIMEOUT)

    def log(self, msg: str):
        """输出详细日志。"""
        if self.verbose:
            print(f"  {msg}")

    def test_endpoint(self, name: str, method: str, path: str,
                      expected_status: int = 200,
                      data: dict = None,
                      check_content: str = None,
                      timeout: int = None) -> bool:
        """测试单个端点。"""
        url = f"{self.base_url}{path}"
        try:
            client = httpx.Client(timeout=timeout or TIMEOUT)
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                response = client.post(url, json=data)
            else:
                raise ValueError(f"不支持的方法: {method}")

            success = response.status_code == expected_status

            if success and check_content:
                success = check_content in response.text

            status = "✅" if success else "❌"
            self.results.append({
                "name": name,
                "status": success,
                "code": response.status_code,
                "url": url,
            })

            print(f"{status} {name} [{response.status_code}]")
            self.log(f"URL: {url}")

            if not success and response.status_code != expected_status:
                print(f"   期望状态码 {expected_status}，实际 {response.status_code}")

            return success

        except Exception as e:
            self.results.append({
                "name": name,
                "status": False,
                "error": str(e),
                "url": url,
            })
            print(f"❌ {name} [ERROR: {e}]")
            return False

    def test_health(self):
        """测试健康检查。"""
        print("\n=== 健康检查 ===")
        self.test_endpoint("健康检查", "GET", "/health", check_content='"status":"ok"')

    def test_pages(self):
        """测试页面。"""
        print("\n=== 页面测试 ===")
        self.test_endpoint("首页", "GET", "/", check_content="WeWrite")
        self.test_endpoint("发布页", "GET", "/publish", check_content="发布文章")
        self.test_endpoint("管理页", "GET", "/admin", check_content="管理后台")
        self.test_endpoint("404 页面", "GET", "/article/nonexistent", expected_status=404)

    def test_api(self):
        """测试 API 端点。"""
        print("\n=== API 测试 ===")
        self.test_endpoint("文章列表 API", "GET", "/api/articles", check_content='"articles"')
        self.test_endpoint("统计 API", "GET", "/api/stats", check_content='"total"')
        self.test_endpoint("系统状态 API", "GET", "/api/system/status", check_content='"pipeline"')
        self.test_endpoint("自动发布设置 API", "GET", "/api/settings/auto-publish", check_content='"enabled"')
        self.test_endpoint("Token 统计 API", "GET", "/api/token-stats", check_content='"total"')
        self.test_endpoint("草稿列表 API", "GET", "/api/drafts", check_content='"drafts"')
        self.test_endpoint("发布历史 API", "GET", "/api/publish/history", check_content='"history"')
        self.test_endpoint("Pipeline 历史 API", "GET", "/api/pipeline/history", check_content='"history"')
        self.test_endpoint("AI 调用记录 API", "GET", "/api/ai-call-log", check_content='"calls"')

    def test_preview_api(self):
        """测试预览 API（超时设置较长，AI 生成需要时间）。"""
        if self.skip_ai:
            print("\n=== 预览 API 测试 ===")
            print("⚠️  预览 API 测试跳过（--skip-ai）")
            return

        print("\n=== 预览 API 测试 ===")
        # 先获取文章列表
        try:
            response = self.client.get(f"{self.base_url}/api/articles?limit=1")
            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                print("⚠️  预览 API 测试跳过（无文章）")
                return

            article_id = articles[0]["id"]
            self.test_endpoint(
                "预览 API",
                "POST",
                "/api/preview",
                data={"article_id": article_id, "theme": "default"},
                check_content='"html"',
                timeout=120  # AI 生成需要较长时间
            )
        except Exception as e:
            print(f"❌ 预览 API 测试失败: {e}")

    def run_all(self):
        """运行所有测试。"""
        print(f"\n{'='*50}")
        print(f"  Web 功能自动测试")
        print(f"  目标: {self.base_url}")
        if self.quick:
            print(f"  模式: 快速（跳过 AI 测试）")
        if self.skip_ai:
            print(f"  跳过: AI 相关测试")
        print(f"{'='*50}")

        self.test_health()
        self.test_pages()
        self.test_api()

        if not self.quick and not self.skip_ai:
            self.test_preview_api()
            self.test_static()

        # 汇总
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"])
        failed = total - passed

        print(f"\n{'='*50}")
        print(f"  测试结果: {passed}/{total} 通过")
        if failed > 0:
            print(f"  失败: {failed} 个")
            for r in self.results:
                if not r["status"]:
                    print(f"    - {r['name']}: {r.get('error', r.get('code', '未知'))}")
        print(f"{'='*50}\n")

        return failed == 0

    def test_static(self):
        """测试静态资源。"""
        print("\n=== 静态资源测试 ===")
        self.test_endpoint("静态资源 404", "GET", "/static/nonexistent", expected_status=404)

    def run_all(self):
        """运行所有测试。"""
        print(f"\n{'='*50}")
        print(f"  Web 功能自动测试")
        print(f"  目标: {self.base_url}")
        print(f"{'='*50}")

        self.test_health()
        self.test_pages()
        self.test_api()
        self.test_preview_api()
        self.test_static()

        # 汇总
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"])
        failed = total - passed

        print(f"\n{'='*50}")
        print(f"  测试结果: {passed}/{total} 通过")
        if failed > 0:
            print(f"  失败: {failed} 个")
            for r in self.results:
                if not r["status"]:
                    print(f"    - {r['name']}: {r.get('error', r.get('code', '未知'))}")
        print(f"{'='*50}\n")

        return failed == 0

    def close(self):
        """关闭客户端。"""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Web 功能自动测试")
    parser.add_argument("--url", default=DEFAULT_URL, help="Web 服务地址")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--quick", "-q", action="store_true", help="快速模式（跳过 AI 测试）")
    parser.add_argument("--skip-ai", action="store_true", help="跳过 AI 相关测试")
    args = parser.parse_args()

    tester = WebTester(args.url, args.verbose, args.quick, args.skip_ai)
    try:
        success = tester.run_all()
        sys.exit(0 if success else 1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()
