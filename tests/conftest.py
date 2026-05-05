"""测试配置文件。

提供共享的 fixtures 和测试工具。
"""

import json

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """创建临时目录。"""
    return tmp_path


@pytest.fixture
def sample_raw_item():
    """示例原始数据条目。"""
    return {
        "source": "github",
        "source_id": "123456789",
        "title": "test-org/test-repo",
        "url": "https://github.com/test-org/test-repo",
        "description": "A test repository for testing purposes.",
        "language": "Python",
        "stars": 1000,
        "forks": 100,
        "topics": ["llm", "agent", "python"],
        "collected_at": "2026-05-01T07:43:57Z",
    }


@pytest.fixture
def sample_analyzed_item(sample_raw_item):
    """示例已分析数据条目。"""
    return {
        **sample_raw_item,
        "summary": "这是一个测试仓库，用于测试目的。",
        "score": 8,
        "tags": ["LLM", "Agent", "Python"],
        "category": "开源项目",
        "key_points": ["支持 LLM", "支持 Agent", "Python 编写"],
        "analyzed": True,
    }


@pytest.fixture
def sample_article():
    """示例知识条目。"""
    return {
        "id": "01a751a2-a2e0-47ca-847c-9acfcfdee7fc",
        "title": "test-org/test-repo",
        "source_url": "https://github.com/test-org/test-repo",
        "source_type": "github",
        "source_metadata": {
            "stars": 1000,
            "language": "Python",
            "topics": ["llm", "agent"],
            "collected_at": "2026-05-01T07:43:57Z",
        },
        "content": "A test repository for testing purposes.",
        "summary": "这是一个测试仓库，用于测试目的。",
        "key_points": ["支持 LLM", "支持 Agent"],
        "tags": ["LLM", "Agent", "Python"],
        "category": "开源项目",
        "score": 8,
        "status": "analyzed",
        "analyzed": True,
        "organized": True,
        "created_at": "2026-05-01T07:53:41Z",
        "updated_at": "2026-05-01T07:53:41Z",
    }


@pytest.fixture
def raw_dir(tmp_dir):
    """创建临时 raw 目录。"""
    raw = tmp_dir / "knowledge" / "raw"
    raw.mkdir(parents=True)
    return raw


@pytest.fixture
def articles_dir(tmp_dir):
    """创建临时 articles 目录。"""
    articles = tmp_dir / "knowledge" / "articles"
    articles.mkdir(parents=True)
    return articles


@pytest.fixture
def sample_rss_sources(tmp_dir):
    """创建示例 RSS 源配置文件。"""
    config = {
        "sources": [
            {
                "name": "Test Source",
                "url": "https://example.com/rss",
                "category": "测试",
                "enabled": True,
            },
            {
                "name": "Disabled Source",
                "url": "https://example.com/disabled",
                "category": "测试",
                "enabled": False,
            },
        ]
    }
    config_file = tmp_dir / "rss_sources.yaml"
    import yaml
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file


@pytest.fixture
def sample_raw_data_file(raw_dir):
    """创建示例原始数据文件。"""
    data = [
        {
            "source": "github",
            "source_id": "123",
            "title": "test/repo1",
            "url": "https://github.com/test/repo1",
            "description": "Test repo 1",
            "collected_at": "2026-05-01T07:43:57Z",
        },
        {
            "source": "rss",
            "source_id": "456",
            "title": "Test Article",
            "url": "https://example.com/article1",
            "description": "Test article description",
            "collected_at": "2026-05-01T07:43:57Z",
        },
    ]
    filepath = raw_dir / "github_20260501_074357.json"
    with open(filepath, "w") as f:
        json.dump(data, f)
    return filepath
