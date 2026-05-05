# WeWrite Makefile

.PHONY: help install test lint format sync-docs run web clean

# 默认目标
help:
	@echo "WeWrite - AI 知识库助手"
	@echo ""
	@echo "可用命令："
	@echo "  make install      安装依赖"
	@echo "  make test         运行测试"
	@echo "  make lint         代码检查"
	@echo "  make format       代码格式化"
	@echo "  make sync-docs    文档同步检查"
	@echo "  make run          运行一次流水线"
	@echo "  make web          启动 Web UI"
	@echo "  make schedule     启动定时调度"
	@echo "  make clean        清理临时文件"
	@echo "  make pre-commit   安装 pre-commit hooks"

# 安装依赖
install:
	@echo "安装依赖..."
	pip install -r requirements.txt
	@echo "安装完成！"

# 运行测试
test:
	@echo "运行测试..."
	pytest tests/ -v

# 代码检查
lint:
	@echo "代码检查..."
	ruff check .

# 代码格式化
format:
	@echo "代码格式化..."
	ruff format .
	ruff check . --fix

# 文档同步检查
sync-docs:
	@echo "文档同步检查..."
	python scripts/sync_docs.py

# 运行一次流水线
run:
	@echo "运行流水线..."
	python pipeline/pipeline.py

# 启动 Web UI
web:
	@echo "启动 Web UI..."
	python web/app.py

# 启动定时调度
schedule:
	@echo "启动定时调度..."
	python scripts/scheduler.py

# 清理临时文件
clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "清理完成！"

# 安装 pre-commit hooks
pre-commit:
	@echo "安装 pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "安装完成！"

# 运行 pre-commit
check:
	@echo "运行 pre-commit 检查..."
	pre-commit run --all-files

# 构建检查（CI 用）
ci: lint test sync-docs
	@echo "CI 检查完成！"

# 开发环境设置
dev: install pre-commit
	@echo "开发环境设置完成！"
	@echo "运行 'make help' 查看可用命令"
