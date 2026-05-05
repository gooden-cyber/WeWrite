"""model_client.py 单元测试。"""

# 导入被测模块
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from model_client import (
    PROVIDER_CONFIGS,
    LLMResponse,
    Usage,
    calculate_cost,
    get_provider,
)


class TestUsage:
    """测试 Usage 数据类。"""

    def test_auto_calculates_total(self):
        """应该自动计算 total_tokens。"""
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        assert usage.total_tokens == 150

    def test_explicit_total(self):
        """显式设置的 total 不会被覆盖。"""
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=200)
        assert usage.total_tokens == 200

    def test_zero_tokens(self):
        """零 token 应该正常工作。"""
        usage = Usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestLLMResponse:
    """测试 LLMResponse 数据类。"""

    def test_default_values(self):
        """默认值应该正确。"""
        response = LLMResponse(content="test")
        assert response.content == "test"
        assert response.model == ""
        assert response.provider == ""
        assert response.latency_ms == 0.0
        assert response.finish_reason == ""

    def test_with_usage(self):
        """应该正确包含 usage。"""
        usage = Usage(prompt_tokens=10, completion_tokens=20)
        response = LLMResponse(content="test", usage=usage)
        assert response.usage.total_tokens == 30


class TestProviderConfigs:
    """测试 PROVIDER_CONFIGS 配置。"""

    def test_all_providers_have_required_fields(self):
        """所有提供商应该有必需的字段。"""
        required_fields = ["base_url", "api_key_env", "default_model"]
        for provider_name, config in PROVIDER_CONFIGS.items():
            for field in required_fields:
                assert field in config, f"{provider_name} 缺少 {field}"

    def test_provider_names(self):
        """应该包含预期的提供商。"""
        expected = {"deepseek", "qwen", "openai", "mimo"}
        assert set(PROVIDER_CONFIGS.keys()) == expected

    def test_deepseek_config(self):
        """DeepSeek 配置应该正确。"""
        config = PROVIDER_CONFIGS["deepseek"]
        assert config["base_url"] == "https://api.deepseek.com/v1"
        assert config["api_key_env"] == "DEEPSEEK_API_KEY"
        assert config["default_model"] == "deepseek-chat"

    def test_qwen_config(self):
        """Qwen 配置应该正确。"""
        config = PROVIDER_CONFIGS["qwen"]
        assert "dashscope.aliyuncs.com" in config["base_url"]
        assert config["api_key_env"] == "QWEN_API_KEY"
        assert config["default_model"] == "qwen-turbo"

    def test_openai_config(self):
        """OpenAI 配置应该正确。"""
        config = PROVIDER_CONFIGS["openai"]
        assert config["base_url"] == "https://api.openai.com/v1"
        assert config["api_key_env"] == "OPENAI_API_KEY"
        assert config["default_model"] == "gpt-4o-mini"

    def test_mimo_config(self):
        """Mimo 配置应该正确。"""
        config = PROVIDER_CONFIGS["mimo"]
        assert "xiaomimimo.com" in config["base_url"]
        assert config["api_key_env"] == "MIMO_API_KEY"
        assert config["default_model"] == "mimo-v2.5-pro"


class TestCalculateCost:
    """测试 calculate_cost 函数。"""

    def test_known_model(self):
        """已知模型应该计算成本。"""
        cost = calculate_cost("deepseek", "deepseek-chat", 1000, 500)
        assert cost > 0

    def test_unknown_model(self):
        """未知提供商应该抛出异常。"""
        with pytest.raises(ValueError, match="未知提供商"):
            calculate_cost("unknown", "unknown-model", 1000, 500)

    def test_zero_tokens(self):
        """零 token 应该返回 0 成本。"""
        cost = calculate_cost("deepseek", "deepseek-chat", 0, 0)
        assert cost == 0


class TestGetProvider:
    """测试 get_provider 函数。"""

    def test_raises_for_unknown_provider(self):
        """未知提供商应该抛出异常。"""
        with pytest.raises(ValueError, match="不支持的提供商"):
            get_provider("unknown")

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_creates_deepseek_provider(self):
        """应该创建 DeepSeek 提供商。"""
        provider = get_provider("deepseek")
        assert provider.provider_name == "deepseek"
        assert provider.model == "deepseek-chat"

    @patch.dict("os.environ", {"QWEN_API_KEY": "test-key"})
    def test_creates_qwen_provider(self):
        """应该创建 Qwen 提供商。"""
        provider = get_provider("qwen")
        assert provider.provider_name == "qwen"
        assert provider.model == "qwen-turbo"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_creates_openai_provider(self):
        """应该创建 OpenAI 提供商。"""
        provider = get_provider("openai")
        assert provider.provider_name == "openai"
        assert provider.model == "gpt-4o-mini"

    @patch.dict("os.environ", {"MIMO_API_KEY": "test-key"})
    def test_creates_mimo_provider(self):
        """应该创建 Mimo 提供商。"""
        provider = get_provider("mimo")
        assert provider.provider_name == "mimo"
        assert provider.model == "mimo-v2.5-pro"

    def test_raises_for_missing_api_key(self):
        """缺少 API key 应该抛出异常。"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="缺少 API 密钥"):
                get_provider("deepseek")

    @patch.dict("os.environ", {"LLM_PROVIDER": "qwen", "QWEN_API_KEY": "test-key"})
    def test_uses_env_provider(self):
        """应该使用环境变量中的提供商。"""
        provider = get_provider()
        assert provider.provider_name == "qwen"

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_defaults_to_mimo(self):
        """默认应该使用 mimo。"""
        with patch.dict("os.environ", {"MIMO_API_KEY": "test-key"}, clear=False):
            provider = get_provider()
        assert provider.provider_name == "mimo"


class TestOpenAICompatibleProvider:
    """测试 OpenAICompatibleProvider 类。"""

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_initialization(self):
        """应该正确初始化。"""
        provider = get_provider("deepseek")
        assert provider.base_url == "https://api.deepseek.com/v1"
        assert provider.api_key == "test-key"
        assert provider.model == "deepseek-chat"
        assert provider.provider_name == "deepseek"
