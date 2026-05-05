"""pipeline.py 核心函数单元测试。"""

import json

# 导入被测模块
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from pipeline import (
    _now_iso,
    deduplicate,
    load_raw_data,
    load_rss_sources,
    save_raw_data,
    standardize_item,
    update_raw_data_status,
    validate_item,
)


class TestNowIso:
    """测试 _now_iso 函数。"""

    def test_returns_iso_format(self):
        """应该返回 ISO 格式的字符串。"""
        result = _now_iso()
        # 验证可以解析
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_returns_utc(self):
        """应该返回 UTC 时间。"""
        result = _now_iso()
        assert "+00:00" in result or result.endswith("Z")


class TestDeduplicate:
    """测试 deduplicate 函数。"""

    def test_empty_list(self):
        """空列表应该返回空列表。"""
        assert deduplicate([]) == []

    def test_no_duplicates(self):
        """无重复应该返回原列表。"""
        items = [
            {"url": "https://example.com/1", "title": "A"},
            {"url": "https://example.com/2", "title": "B"},
        ]
        result = deduplicate(items)
        assert len(result) == 2

    def test_with_duplicates(self):
        """有重复应该去重。"""
        items = [
            {"url": "https://example.com/1", "title": "A"},
            {"url": "https://example.com/2", "title": "B"},
            {"url": "https://example.com/1", "title": "A"},
        ]
        result = deduplicate(items)
        assert len(result) == 2

    def test_empty_url_filtered(self):
        """空 URL 应该被过滤掉。"""
        items = [
            {"url": "", "title": "A"},
            {"url": "", "title": "B"},
        ]
        result = deduplicate(items)
        assert len(result) == 0


class TestValidateItem:
    """测试 validate_item 函数。"""

    def test_valid_item(self):
        """有效条目应该通过验证。"""
        item = {
            "title": "Test",
            "url": "https://example.com",
            "source": "github",
        }
        assert validate_item(item) is True

    def test_missing_title(self):
        """缺少 title 应该失败。"""
        item = {
            "url": "https://example.com",
            "source": "github",
        }
        assert validate_item(item) is False

    def test_missing_url(self):
        """缺少 url 应该失败。"""
        item = {
            "title": "Test",
            "source": "github",
        }
        assert validate_item(item) is False

    def test_missing_source(self):
        """缺少 source 应该失败。"""
        item = {
            "title": "Test",
            "url": "https://example.com",
        }
        assert validate_item(item) is False

    def test_empty_title(self):
        """空 title 应该失败。"""
        item = {
            "title": "",
            "url": "https://example.com",
            "source": "github",
        }
        assert validate_item(item) is False


class TestStandardizeItem:
    """测试 standardize_item 函数。"""

    def test_basic_standardization(self):
        """基本标准化应该正确。"""
        item = {
            "title": "  Test Title  ",
            "url": "https://example.com",
            "source": "github",
            "description": "Test description",
            "stars": 100,
            "language": "Python",
            "topics": ["llm"],
        }
        result = standardize_item(item)

        assert result["title"] == "Test Title"
        assert result["source_url"] == "https://example.com"
        assert result["source_type"] == "github"
        assert result["content"] == "Test description"
        assert result["source_metadata"]["stars"] == 100
        assert result["source_metadata"]["language"] == "Python"
        assert result["source_metadata"]["topics"] == ["llm"]
        assert result["status"] == "analyzed"
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_missing_optional_fields(self):
        """缺少可选字段应该使用默认值。"""
        item = {
            "title": "Test",
            "url": "https://example.com",
            "source": "rss",
        }
        result = standardize_item(item)

        assert result["content"] == ""
        assert result["source_metadata"]["stars"] == 0
        assert result["source_metadata"]["language"] == ""
        assert result["source_metadata"]["topics"] == []
        assert result["summary"] == ""
        assert result["key_points"] == []
        assert result["tags"] == []
        assert result["category"] == "技术动态"
        assert result["score"] == 0

    def test_with_analysis_data(self):
        """包含分析数据应该正确合并。"""
        item = {
            "title": "Test",
            "url": "https://example.com",
            "source": "github",
            "summary": "Test summary",
            "score": 8,
            "tags": ["LLM"],
            "category": "开源项目",
            "key_points": ["Point 1"],
        }
        result = standardize_item(item)

        assert result["summary"] == "Test summary"
        assert result["score"] == 8
        assert result["tags"] == ["LLM"]
        assert result["category"] == "开源项目"
        assert result["key_points"] == ["Point 1"]


class TestLoadRawData:
    """测试 load_raw_data 函数。"""

    def test_empty_dir(self, tmp_dir):
        """空目录应该返回空列表。"""
        raw_dir = tmp_dir / "raw"
        raw_dir.mkdir()

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data()
        assert result == []

    def test_loads_data(self, sample_raw_data_file):
        """应该正确加载数据。"""
        raw_dir = sample_raw_data_file.parent

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data()
        assert len(result) == 2

    def test_deduplicates_by_url(self, raw_dir):
        """应该按 URL 去重。"""
        # 创建两个文件，包含相同 URL
        data1 = [{"url": "https://example.com/1", "title": "A"}]
        data2 = [{"url": "https://example.com/1", "title": "A"}, {"url": "https://example.com/2", "title": "B"}]

        with open(raw_dir / "file1.json", "w") as f:
            json.dump(data1, f)
        with open(raw_dir / "file2.json", "w") as f:
            json.dump(data2, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data()
        assert len(result) == 2

    def test_status_filter_unanalyzed(self, raw_dir):
        """应该过滤出未分析的数据。"""
        data = [
            {"url": "https://example.com/1", "title": "A", "analyzed": False},
            {"url": "https://example.com/2", "title": "B", "analyzed": True},
            {"url": "https://example.com/3", "title": "C"},
        ]

        with open(raw_dir / "file.json", "w") as f:
            json.dump(data, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data(status_filter="unanalyzed")
        assert len(result) == 2  # 未分析的 + 没有 analyzed 字段的

    def test_status_filter_organized(self, raw_dir):
        """应该过滤出已整理的数据。"""
        data = [
            {"url": "https://example.com/1", "title": "A", "analyzed": True, "organized": True},
            {"url": "https://example.com/2", "title": "B", "analyzed": True, "organized": False},
            {"url": "https://example.com/3", "title": "C", "analyzed": False},
        ]

        with open(raw_dir / "file.json", "w") as f:
            json.dump(data, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data(status_filter="organized")
        assert len(result) == 1

    def test_date_filter(self, raw_dir):
        """应该按日期过滤文件。"""
        data1 = [{"url": "https://example.com/1", "title": "A"}]
        data2 = [{"url": "https://example.com/2", "title": "B"}]

        with open(raw_dir / "github_20260501_074357.json", "w") as f:
            json.dump(data1, f)
        with open(raw_dir / "github_20260502_074357.json", "w") as f:
            json.dump(data2, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data(date_filter="20260501")
        assert len(result) == 1

    def test_limit(self, raw_dir):
        """应该限制返回数量。"""
        data = [
            {"url": f"https://example.com/{i}", "title": f"T{i}"}
            for i in range(10)
        ]

        with open(raw_dir / "file.json", "w") as f:
            json.dump(data, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data(limit=5)
        assert len(result) == 5

    def test_unifies_source_url_to_url(self, raw_dir):
        """应该将 source_url 统一为 url。"""
        data = [
            {"source_url": "https://example.com/1", "title": "A"},
        ]

        with open(raw_dir / "file.json", "w") as f:
            json.dump(data, f)

        with patch("pipeline.RAW_DIR", raw_dir):
            result = load_raw_data()
        assert result[0]["url"] == "https://example.com/1"


class TestUpdateRawDataStatus:
    """测试 update_raw_data_status 函数。"""

    def test_updates_status(self, sample_raw_data_file):
        """应该更新状态字段。"""
        raw_dir = sample_raw_data_file.parent
        url = "https://github.com/test/repo1"

        with patch("pipeline.RAW_DIR", raw_dir):
            result = update_raw_data_status(url, "analyzed", True)

        assert result is True

        # 验证更新
        with open(sample_raw_data_file) as f:
            items = json.load(f)
        item = next(i for i in items if i["url"] == url)
        assert item["analyzed"] is True

    def test_returns_false_for_missing_url(self, sample_raw_data_file):
        """不存在的 URL 应该返回 False。"""
        raw_dir = sample_raw_data_file.parent

        with patch("pipeline.RAW_DIR", raw_dir):
            result = update_raw_data_status("https://not-found.com", "analyzed", True)

        assert result is False


class TestSaveRawData:
    """测试 save_raw_data 函数。"""

    def test_saves_to_file(self, raw_dir):
        """应该保存到文件。"""
        items = [
            {"url": "https://example.com/1", "title": "A"},
            {"url": "https://example.com/2", "title": "B"},
        ]

        with patch("pipeline.RAW_DIR", raw_dir):
            filepath = save_raw_data(items, "github")

        assert filepath.exists()
        with open(filepath) as f:
            saved = json.load(f)
        assert len(saved) == 2

    def test_creates_timestamped_filename(self, raw_dir):
        """应该创建带时间戳的文件名。"""
        items = [{"url": "https://example.com/1"}]

        with patch("pipeline.RAW_DIR", raw_dir):
            filepath = save_raw_data(items, "github")

        assert "github_" in filepath.name
        assert filepath.suffix == ".json"


class TestLoadRssSources:
    """测试 load_rss_sources 函数。"""

    def test_loads_enabled_sources(self, sample_rss_sources):
        """应该只加载启用的源。"""
        with patch("pipeline.RSS_SOURCES_FILE", sample_rss_sources):
            result = load_rss_sources()

        assert len(result) == 1
        assert result[0]["name"] == "Test Source"

    def test_returns_empty_for_missing_file(self, tmp_dir):
        """文件不存在应该返回空列表。"""
        config_file = tmp_dir / "nonexistent.yaml"

        with patch("pipeline.RSS_SOURCES_FILE", config_file):
            result = load_rss_sources()

        assert result == []
