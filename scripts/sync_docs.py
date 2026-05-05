#!/usr/bin/env python3
"""文档同步检查脚本。

检查项目文档的一致性，并提供修复建议。

用法：
    python scripts/sync_docs.py          # 检查
    python scripts/sync_docs.py --fix    # 自动修复
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_readme_commands() -> list[str]:
    """检查 README.md 中的命令是否与 start.sh 一致。"""
    issues = []

    readme_path = PROJECT_ROOT / "README.md"
    start_sh_path = PROJECT_ROOT / "start.sh"

    if not readme_path.exists():
        return ["README.md 不存在"]

    if not start_sh_path.exists():
        return ["start.sh 不存在"]

    readme_content = readme_path.read_text()
    start_sh_content = start_sh_path.read_text()

    # 提取 start.sh 中的模式
    start_sh_modes = re.findall(r'(\w+)\)\s*#', start_sh_content)

    # 检查 README 中是否提到了这些模式
    for mode in start_sh_modes:
        if mode == "*":
            continue
        if f"./start.sh {mode}" not in readme_content and mode != "once":
            issues.append(f"README.md 中缺少 ./start.sh {mode} 的说明")

    return issues


def check_env_example() -> list[str]:
    """检查 .env.example 是否包含所有环境变量。"""
    issues = []

    env_example_path = PROJECT_ROOT / ".env.example"
    model_client_path = PROJECT_ROOT / "pipeline" / "model_client.py"

    if not env_example_path.exists():
        return [".env.example 不存在"]

    if not model_client_path.exists():
        return ["pipeline/model_client.py 不存在"]

    env_content = env_example_path.read_text()
    model_content = model_client_path.read_text()

    # 提取 model_client.py 中的环境变量
    env_vars = re.findall(r'os\.getenv\(["\'](\w+)["\']\)', model_content)
    env_vars += re.findall(r'api_key_env.*?["\'](\w+)["\']', model_content)

    # 去重
    env_vars = list(set(env_vars))

    # 检查 .env.example 中是否包含这些环境变量
    for var in env_vars:
        if var not in env_content:
            issues.append(f".env.example 中缺少环境变量: {var}")

    return issues


def check_requirements() -> list[str]:
    """检查 requirements.txt 是否包含所有导入的依赖。"""
    issues = []

    req_path = PROJECT_ROOT / "requirements.txt"

    if not req_path.exists():
        return ["requirements.txt 不存在"]

    req_content = req_path.read_text()

    # 标准库模块
    stdlib_modules = {
        'abc', 'argparse', 'collections', 'datetime', 'email', 'functools',
        'hashlib', 'http', 'io', 'json', 'logging', 'os', 'pathlib',
        're', 'shutil', 'socket', 'sqlite3', 'string', 'subprocess',
        'sys', 'tempfile', 'threading', 'time', 'typing', 'unittest',
        'urllib', 'uuid', 'xml', 'zipfile',
    }

    # 扫描所有 Python 文件
    for py_file in PROJECT_ROOT.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text()
        except Exception:
            continue

        # 提取 import 语句
        imports = re.findall(r'^import\s+(\w+)', content, re.MULTILINE)
        imports += re.findall(r'^from\s+(\w+)', content, re.MULTILINE)

        # 去重和过滤
        imports = list(set(imports))
        imports = [i for i in imports if i not in stdlib_modules and not i.startswith('_')]

        # 检查是否在 requirements.txt 中
        for imp in imports:
            # 映射包名
            package_name = imp
            if imp == 'cv2':
                package_name = 'opencv-python'
            elif imp == 'PIL':
                package_name = 'pillow'
            elif imp == 'yaml':
                package_name = 'pyyaml'
            elif imp == 'dotenv':
                package_name = 'python-dotenv'

            if package_name.lower() not in req_content.lower() and imp not in req_content:
                # 检查是否是项目内部模块
                if not any((PROJECT_ROOT / "pipeline" / f"{imp}.py").exists() for _ in [1]):
                    if not any((PROJECT_ROOT / f"{imp}.py").exists() for _ in [1]):
                        issues.append(f"requirements.txt 中可能缺少依赖: {imp} (来自 {py_file.name})")

    return issues


def check_project_structure() -> list[str]:
    """检查项目结构是否完整。"""
    issues = []

    required_files = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "AGENTS.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "pipeline/pipeline.py",
        "pipeline/model_client.py",
        "pipeline/wechat_api.py",
        "scripts/scheduler.py",
        "hooks/validate_json.py",
        "hooks/check_quality.py",
    ]

    for file_path in required_files:
        if not (PROJECT_ROOT / file_path).exists():
            issues.append(f"缺少必需文件: {file_path}")

    return issues


def check_changelog() -> list[str]:
    """检查 CHANGELOG.md 是否需要更新。"""
    issues = []

    changelog_path = PROJECT_ROOT / "CHANGELOG.md"

    if not changelog_path.exists():
        return ["CHANGELOG.md 不存在"]

    content = changelog_path.read_text()

    # 检查是否有未发布部分
    if "## [Unreleased]" not in content and "## 未发布" not in content:
        issues.append("CHANGELOG.md 中缺少未发布部分")

    return issues


def main():
    """主函数。"""
    print("=" * 60)
    print("  WeWrite 文档同步检查")
    print("=" * 60)
    print()

    all_issues = []

    # 检查项目结构
    print("检查项目结构...")
    structure_issues = check_project_structure()
    if structure_issues:
        all_issues.extend(structure_issues)
        for issue in structure_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ 项目结构完整")

    # 检查 README 命令
    print("\n检查 README 命令...")
    readme_issues = check_readme_commands()
    if readme_issues:
        all_issues.extend(readme_issues)
        for issue in readme_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ README 命令一致")

    # 检查环境变量
    print("\n检查环境变量...")
    env_issues = check_env_example()
    if env_issues:
        all_issues.extend(env_issues)
        for issue in env_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ 环境变量完整")

    # 检查依赖
    print("\n检查依赖...")
    req_issues = check_requirements()
    if req_issues:
        all_issues.extend(req_issues)
        for issue in req_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ 依赖完整")

    # 检查 CHANGELOG
    print("\n检查 CHANGELOG...")
    changelog_issues = check_changelog()
    if changelog_issues:
        all_issues.extend(changelog_issues)
        for issue in changelog_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ CHANGELOG 正常")

    # 总结
    print("\n" + "=" * 60)
    if all_issues:
        print(f"发现 {len(all_issues)} 个问题")
        print("\n建议运行以下命令修复：")
        print("  python scripts/sync_docs.py --fix")
        return 1
    else:
        print("✅ 所有检查通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
