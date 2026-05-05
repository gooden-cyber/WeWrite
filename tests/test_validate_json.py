"""validate_json.py 单元测试。"""

import json
from pathlib import Path

import pytest

# 导入被测模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from validate_json import (
    validate_file,
    ID_PATTERN,
    URL_PATTERN,
    VALID_STATUSES,
    REQUIRED_FIELDS,
    MIN_SUMMARY_LENGTH,
    MIN_TAGS_COUNT,
)


class TestIDPattern:
    """测试 ID 正则表达式。"""

    def test_valid_uuid(self):
        """应该匹配标准 UUID。"""
        assert ID_PATTERN.match("01a751a2-a2e0-47ca-847c-9acfcfdee7fc")

    def test_invalid_format(self):
        """不应该匹配非 UUID 格式。"""
        assert not ID_PATTERN.match("github-20260501-001")
        assert not ID_PATTERN.match("12345")
        assert not ID_PATTERN.match("abc")

    def test_case_insensitive(self):
        """应该只支持小写。"""
        # 当前实现只支持小写
        assert not ID_PATTERN.match("01A751A2-A2E0-47CA-847C-9ACFCFDEE7FC")


class TestURLPattern:
    """测试 URL 正则表达式。"""

    def test_valid_http(self):
        """应该匹配 HTTP URL。"""
        assert URL_PATTERN.match("http://example.com")

    def test_valid_https(self):
        """应该匹配 HTTPS URL。"""
        assert URL_PATTERN.match("https://example.com/path?query=1")

    def test_invalid_url(self):
        """不应该匹配无效 URL。"""
        assert not URL_PATTERN.match("not-a-url")
        assert not URL_PATTERN.match("ftp://example.com")


class TestConstants:
    """测试常量定义。"""

    def test_valid_statuses(self):
        """应该包含预期的状态。"""
        expected = {"draft", "review", "published", "archived", "analyzed", "raw", "curated", "distributed"}
        assert VALID_STATUSES == expected

    def test_required_fields(self):
        """应该包含必需的字段。"""
        expected = {"id", "title", "source_url", "summary", "tags", "status"}
        assert set(REQUIRED_FIELDS.keys()) == expected

    def test_field_types(self):
        """字段类型应该正确。"""
        assert REQUIRED_FIELDS["id"] == str
        assert REQUIRED_FIELDS["title"] == str
        assert REQUIRED_FIELDS["source_url"] == str
        assert REQUIRED_FIELDS["summary"] == str
        assert REQUIRED_FIELDS["tags"] == list
        assert REQUIRED_FIELDS["status"] == str


class TestValidateFile:
    """测试 validate_file 函数。"""

    def test_valid_article(self, tmp_path):
        """有效文章应该通过验证。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length to pass validation.",
            "tags": ["LLM", "Agent"],
            "status": "analyzed",
            "score": 8,
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert errors == []

    def test_missing_required_field(self, tmp_path):
        """缺少必需字段应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            # 缺少 source_url
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("source_url" in e for e in errors)

    def test_invalid_id_format(self, tmp_path):
        """无效 ID 格式应该报错。"""
        article = {
            "id": "invalid-id",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("ID 格式错误" in e for e in errors)

    def test_invalid_status(self, tmp_path):
        """无效状态应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "invalid_status",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("status 值无效" in e for e in errors)

    def test_short_summary(self, tmp_path):
        """过短的摘要应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "Too short",
            "tags": ["LLM"],
            "status": "analyzed",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("摘要过短" in e for e in errors)

    def test_too_few_tags(self, tmp_path):
        """标签数量不足应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": [],
            "status": "analyzed",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("标签数量不足" in e for e in errors)

    def test_invalid_score(self, tmp_path):
        """无效分数应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
            "score": 15,  # 超出范围
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("score 超出范围" in e for e in errors)

    def test_invalid_url(self, tmp_path):
        """无效 URL 应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "not-a-url",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("URL 格式无效" in e for e in errors)

    def test_invalid_json(self, tmp_path):
        """无效 JSON 应该报错。"""
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            f.write("not json")
        
        errors = validate_file(filepath)
        assert any("JSON 解析失败" in e for e in errors)

    def test_non_dict_json(self, tmp_path):
        """非字典 JSON 应该报错。"""
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump([1, 2, 3], f)
        
        errors = validate_file(filepath)
        assert any("顶层结构必须是对象" in e for e in errors)

    def test_nonexistent_file(self):
        """不存在的文件应该报错。"""
        filepath = Path("/nonexistent/file.json")
        errors = validate_file(filepath)
        assert any("文件读取失败" in e for e in errors)

    def test_optional_score_field(self, tmp_path):
        """可选的 score 字段应该正常验证。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
            "score": 8,
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert errors == []

    def test_optional_audience_field(self, tmp_path):
        """可选的 audience 字段应该正常验证。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
            "audience": "intermediate",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert errors == []

    def test_invalid_audience(self, tmp_path):
        """无效的 audience 应该报错。"""
        article = {
            "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
            "title": "Test Article",
            "source_url": "https://example.com/article",
            "summary": "This is a test summary with enough length.",
            "tags": ["LLM"],
            "status": "analyzed",
            "audience": "invalid",
        }
        filepath = tmp_path / "test.json"
        with open(filepath, "w") as f:
            json.dump(article, f)
        
        errors = validate_file(filepath)
        assert any("audience 值无效" in e for e in errors)
