"""统一的 LLM 调用客户端模块。

支持 DeepSeek、Qwen、OpenAI 三种模型提供商，通过环境变量切换。
使用 httpx 直接调用 OpenAI 兼容 API，不依赖 openai SDK。

Example:
    >>> from pipeline.model_client import quick_chat
    >>> response = quick_chat("Hello, how are you?")
    >>> print(response.content)
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Token 使用统计文件
STATS_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "token_stats.json"
# AI 调用记录文件（详细日志）
CALL_LOG_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "ai_call_log.jsonl"

# 模型提供商配置
PROVIDER_CONFIGS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "pricing": {
            "deepseek-chat": {"input": 0.14, "output": 0.28},
            "deepseek-coder": {"input": 0.14, "output": 0.28},
        },
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
        "default_model": "qwen-turbo",
        "pricing": {
            "qwen-turbo": {"input": 0.02, "output": 0.06},
            "qwen-plus": {"input": 0.04, "output": 0.12},
            "qwen-max": {"input": 0.12, "output": 0.36},
        },
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
        "pricing": {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        },
    },
    "mimo": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "api_key_env": "MIMO_API_KEY",
        "default_model": "mimo-v2.5-pro",
        "pricing": {},
    },
}

# 重试配置
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 60.0


@dataclass
class Usage:
    """Token 用量统计。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        """自动计算 total_tokens。"""
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    """LLM 调用响应统一数据结构。

    Attributes:
        content: 模型生成的文本内容。
        usage: Token 用量统计。
        model: 实际使用的模型名称。
        provider: 模型提供商名称。
        latency_ms: 请求耗时（毫秒）。
        finish_reason: 生成结束原因。
    """

    content: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    finish_reason: str = ""


class LLMProvider(ABC):
    """LLM 提供商抽象基类。"""

    @abstractmethod
    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """发送聊天请求。

        Args:
            prompt: 用户输入的提示文本。
            system_prompt: 系统提示文本。
            temperature: 生成温度，控制随机性。
            max_tokens: 最大生成 token 数。

        Returns:
            LLMResponse 对象，包含生成内容和用量统计。

        Raises:
            httpx.HTTPStatusError: API 返回错误状态码。
            httpx.TimeoutException: 请求超时。
        """
        pass


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容 API 提供商实现。

    支持 DeepSeek、Qwen、OpenAI 等兼容 OpenAI API 格式的提供商。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: str,
    ) -> None:
        """初始化提供商。

        Args:
            base_url: API 基础 URL。
            api_key: API 密钥。
            model: 模型名称。
            provider_name: 提供商名称标识。
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider_name = provider_name

    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """发送聊天请求到 OpenAI 兼容 API。

        Args:
            prompt: 用户输入的提示文本。
            system_prompt: 系统提示文本。
            temperature: 生成温度。
            max_tokens: 最大生成 token 数。

        Returns:
            LLMResponse 对象。

        Raises:
            httpx.HTTPStatusError: API 返回错误状态码。
            httpx.TimeoutException: 请求超时。
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.monotonic()

        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        latency_ms = (time.monotonic() - start_time) * 1000
        data = response.json()

        choice = data["choices"][0]
        usage_data = data.get("usage", {})

        # 处理mimo模型返回reasoning_content但content为空的情况
        message = choice["message"]
        content = message.get("content", "")
        reasoning_content = message.get("reasoning_content", "")

        # 如果content为空但有reasoning_content，使用reasoning_content
        if not content and reasoning_content:
            content = reasoning_content
            logger.debug("使用reasoning_content作为content")

        return LLMResponse(
            content=content,
            usage=Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            ),
            model=data.get("model", self.model),
            provider=self.provider_name,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", ""),
        )


def get_provider(provider_name: str | None = None) -> OpenAICompatibleProvider:
    """获取 LLM 提供商实例。

    根据环境变量 LLM_PROVIDER 或指定的提供商名称创建实例。

    Args:
        provider_name: 提供商名称，为 None 时从环境变量读取。

    Returns:
        OpenAICompatibleProvider 实例。

    Raises:
        ValueError: 不支持的提供商名称或缺少 API 密钥。
    """
    name = provider_name or os.getenv("LLM_PROVIDER", "mimo").lower()

    if name not in PROVIDER_CONFIGS:
        raise ValueError(
            f"不支持的提供商: {name}，可选: {list(PROVIDER_CONFIGS.keys())}"
        )

    config = PROVIDER_CONFIGS[name]
    api_key = os.getenv(config["api_key_env"])

    if not api_key:
        raise ValueError(
            f"缺少 API 密钥，请设置环境变量 {config['api_key_env']}"
        )

    return OpenAICompatibleProvider(
        base_url=config["base_url"],
        api_key=api_key,
        model=config["default_model"],
        provider_name=name,
    )


def chat_with_retry(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    provider_name: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> LLMResponse:
    """带重试机制的 LLM 聊天调用。

    使用指数退避策略进行重试，最多重试 max_retries 次。

    Args:
        prompt: 用户输入的提示文本。
        system_prompt: 系统提示文本。
        temperature: 生成温度。
        max_tokens: 最大生成 token 数。
        provider_name: 提供商名称，为 None 时从环境变量读取。
        max_retries: 最大重试次数。

    Returns:
        LLMResponse 对象。

    Raises:
        httpx.HTTPStatusError: 重试耗尽后仍失败。
        httpx.TimeoutException: 重试耗尽后仍超时。
    """
    provider = get_provider(provider_name)
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            logger.debug(
                "调用 %s，第 %d/%d 次尝试",
                provider.provider_name,
                attempt + 1,
                max_retries + 1,
            )
            response = provider.chat(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(
                "调用成功: provider=%s, model=%s, tokens=%d, latency=%.1fms",
                response.provider,
                response.model,
                response.usage.total_tokens,
                response.latency_ms,
            )
            return response

        except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
            last_exception = exc
            if attempt < max_retries:
                backoff = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "调用失败 (attempt %d/%d): %s，%.1f 秒后重试",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
            else:
                logger.error(
                    "调用失败，重试耗尽: %s", exc
                )

    raise last_exception  # type: ignore[misc]


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量。

    使用简化的估算规则：英文约 4 字符/token，中文约 2 字符/token。

    Args:
        text: 需要估算的文本。

    Returns:
        估算的 token 数量。
    """
    if not text:
        return 0

    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other_chars = len(text) - chinese_chars

    return int(chinese_chars / 2 + other_chars / 4)


def calculate_cost(
    provider_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """计算 API 调用成本（USD）。

    Args:
        provider_name: 提供商名称。
        model: 模型名称。
        prompt_tokens: 输入 token 数量。
        completion_tokens: 输出 token 数量。

    Returns:
        成本金额（美元）。

    Raises:
        ValueError: 未找到指定模型的定价信息。
    """
    provider_config = PROVIDER_CONFIGS.get(provider_name)
    if not provider_config:
        raise ValueError(f"未知提供商: {provider_name}")

    pricing = provider_config["pricing"].get(model)
    if not pricing:
        raise ValueError(
            f"未找到 {provider_name}/{model} 的定价信息"
        )

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def quick_chat(
    prompt: str,
    system_prompt: str | None = None,
    provider_name: str | None = None,
) -> str:
    """便捷的 LLM 聊天函数。

    一句话调用 LLM，返回纯文本内容。

    Args:
        prompt: 用户输入的提示文本。
        system_prompt: 系统提示文本。
        provider_name: 提供商名称，为 None 时从环境变量读取。

    Returns:
        模型生成的文本内容。

    Example:
        >>> answer = quick_chat("用一句话解释什么是机器学习")
        >>> print(answer)
    """
    response = chat_with_retry(
        prompt=prompt,
        system_prompt=system_prompt,
        provider_name=provider_name,
    )

    # 记录 token 使用统计
    _record_usage(
        provider_name=provider_name or os.getenv("LLM_PROVIDER", "mimo").lower(),
        model=response.model if hasattr(response, 'model') else "unknown",
        usage=response.usage,
        prompt=prompt,
    )

    return response.content


def _record_usage(provider_name: str, model: str, usage: Usage, prompt: str = "") -> None:
    """记录 token 使用统计到文件。"""
    try:
        stats = _load_stats()

        # 更新总计
        stats["total"]["prompt_tokens"] += usage.prompt_tokens
        stats["total"]["completion_tokens"] += usage.completion_tokens
        stats["total"]["total_tokens"] += usage.total_tokens
        stats["total"]["requests"] += 1

        # 更新今日统计
        stats["today"]["prompt_tokens"] += usage.prompt_tokens
        stats["today"]["completion_tokens"] += usage.completion_tokens
        stats["today"]["total_tokens"] += usage.total_tokens
        stats["today"]["requests"] += 1

        # 更新按提供商统计
        if provider_name not in stats["by_provider"]:
            stats["by_provider"][provider_name] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "requests": 0,
            }
        provider_stats = stats["by_provider"][provider_name]
        provider_stats["prompt_tokens"] += usage.prompt_tokens
        provider_stats["completion_tokens"] += usage.completion_tokens
        provider_stats["total_tokens"] += usage.total_tokens
        provider_stats["requests"] += 1

        # 计算成本
        try:
            cost = calculate_cost(provider_name, model, usage.prompt_tokens, usage.completion_tokens)
            stats["total"]["estimated_cost_usd"] = stats["total"].get("estimated_cost_usd", 0) + cost
            stats["today"]["estimated_cost_usd"] = stats["today"].get("estimated_cost_usd", 0) + cost
        except (ValueError, KeyError):
            pass  # 无定价信息时跳过

        _save_stats(stats)

        # 记录详细调用日志
        _log_call(provider_name, model, usage, prompt)
    except Exception as e:
        logger.warning("记录 token 统计失败: %s", e)


def _log_call(provider_name: str, model: str, usage: Usage, prompt: str = "") -> None:
    """记录单次 AI 调用到详细日志。"""
    try:
        from datetime import datetime
        record = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider_name,
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "prompt_preview": prompt[:100] if prompt else "",
        }

        # 计算成本
        try:
            cost = calculate_cost(provider_name, model, usage.prompt_tokens, usage.completion_tokens)
            record["cost_usd"] = round(cost, 6)
        except (ValueError, KeyError):
            record["cost_usd"] = None

        CALL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("记录 AI 调用日志失败: %s", e)


def _load_stats() -> dict:
    """加载 token 统计数据。"""
    from datetime import datetime
    today = datetime.now().date().isoformat()

    default_stats = {
        "total": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "estimated_cost_usd": 0,
        },
        "today": {
            "date": today,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "estimated_cost_usd": 0,
        },
        "by_provider": {},
    }

    if STATS_FILE.exists():
        try:
            stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
            # 确保 today 字段存在且是今天的
            if "today" not in stats or stats["today"].get("date") != today:
                stats["today"] = default_stats["today"]
            return stats
        except (json.JSONDecodeError, OSError):
            pass

    return default_stats


def _save_stats(stats: dict) -> None:
    """保存 token 统计数据。"""
    from datetime import datetime
    today = datetime.now().date().isoformat()

    # 确保 today 字段存在且是今天的
    if "today" not in stats or stats["today"].get("date") != today:
        stats["today"] = {
            "date": today,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "estimated_cost_usd": 0,
        }

    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")


def get_token_stats() -> dict:
    """获取 token 使用统计（公开 API）。"""
    return _load_stats()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("LLM 统一客户端测试")
    print("=" * 60)

    # 测试 token 估算
    test_text = "Hello, how are you? 你好吗？"
    estimated = estimate_tokens(test_text)
    print("\n[Token 估算测试]")
    print(f"  文本: {test_text!r}")
    print(f"  估算 token 数: {estimated}")

    # 测试成本计算
    print("\n[成本计算测试]")
    try:
        cost = calculate_cost("deepseek", "deepseek-chat", 1000, 500)
        print(f"  DeepSeek (1000 input + 500 output): ${cost:.6f}")
    except ValueError as exc:
        print(f"  跳过: {exc}")

    # 测试实际调用（需要设置环境变量）
    print("\n[实际调用测试]")
    provider = os.getenv("LLM_PROVIDER", "mimo").lower()
    api_key_env = PROVIDER_CONFIGS.get(provider, {}).get("api_key_env", "")

    if os.getenv(api_key_env):
        try:
            print(f"  使用提供商: {provider}")
            answer = quick_chat("请用一句话介绍你自己。")
            print(f"  回复: {answer}")
        except Exception as exc:
            print(f"  调用失败: {exc}")
    else:
        print(f"  跳过: 未设置 {api_key_env} 环境变量")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
