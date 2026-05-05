"""定时任务调度器 - 自动采集和分析流水线。

用法:
    python scripts/scheduler.py                  # 启动调度器
    python scripts/scheduler.py --test           # 测试模式（立即执行一次）
    python scripts/scheduler.py --daemon         # 后台运行
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import schedule
except ImportError:
    print("请安装 schedule: pip install schedule")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_SCRIPT = PROJECT_ROOT / "pipeline" / "pipeline.py"
LOGS_DIR = PROJECT_ROOT / "logs"


def run_pipeline(steps: list[int], job_name: str, date_filter: str = None):
    """运行流水线指定步骤。

    Args:
        steps: 要运行的步骤列表
        job_name: 任务名称
        date_filter: 日期过滤器，格式 YYYYMMDD
            - None: 处理所有未处理的数据（推荐用于定时任务）
            - "20260501": 只处理该日期的数据（用于手动补处理）
    """
    logger.info(f"开始执行: {job_name} (steps={steps}, date={date_filter or '全部'})")

    try:
        # 构建命令
        cmd = [
            sys.executable,  # 当前 Python 解释器
            str(PIPELINE_SCRIPT),
            "--step",
        ]
        
        # 添加所有步骤
        cmd.extend([str(s) for s in steps])

        # 添加日期过滤（可选）
        if date_filter:
            cmd.extend(["--date", date_filter])

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 执行命令
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=3600,  # 1小时超时
        )

        if result.returncode == 0:
            logger.info(f"{job_name} 执行成功")
            if result.stdout:
                logger.debug(f"输出: {result.stdout[-500:]}")
        else:
            logger.error(f"{job_name} 执行失败 (返回码: {result.returncode})")
            if result.stderr:
                logger.error(f"错误: {result.stderr[-500:]}")

    except subprocess.TimeoutExpired:
        logger.error(f"{job_name} 执行超时")
    except Exception as e:
        logger.error(f"{job_name} 执行异常: {e}")


def job_collect():
    """定时任务：采集数据。"""
    run_pipeline(steps=[1], job_name="数据采集")


def job_analyze():
    """定时任务：分析数据。"""
    run_pipeline(steps=[2, 3, 4], job_name="数据分析+整理+保存")


def job_full_pipeline():
    """定时任务：完整流水线（采集+分析+整理+保存）。"""
    run_pipeline(steps=[1, 2, 3, 4], job_name="完整流水线")


def job_collect_and_analyze():
    """定时任务：采集新数据并处理所有未分析的数据。"""
    logger.info("=" * 50)
    logger.info("开始定时任务：采集 + 分析 + 整理 + 保存")
    logger.info("=" * 50)
    
    # 运行完整流水线（处理所有未处理的数据）
    run_pipeline(steps=[1, 2, 3, 4], job_name="定时流水线")
    
    logger.info("定时任务执行完毕")


def setup_schedule():
    """配置定时任务。"""
    # 每天 08:00 采集 + 分析
    schedule.every().day.at("08:00").do(job_collect_and_analyze).tag("采集+分析", "每日")

    # 可选：每 6 小时采集一次
    # schedule.every(6).hours.do(job_collect).tag("采集", "频繁")

    logger.info("定时任务配置完成:")
    for job in schedule.get_jobs():
        logger.info(f"  - {job}")


def run_scheduler():
    """运行调度器。"""
    logger.info("=" * 50)
    logger.info("定时任务调度器启动")
    logger.info("=" * 50)

    setup_schedule()

    logger.info("调度器运行中，按 Ctrl+C 停止...")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("调度器已停止")


def test_mode(date_filter: str = None):
    """测试模式：立即执行一次流水线。

    Args:
        date_filter: 日期过滤器，格式 YYYYMMDD
            - None: 处理所有未处理的数据
            - "20260501": 只处理该日期的数据
    """
    logger.info(f"测试模式：立即执行流水线 (日期: {date_filter or '全部'})...")
    run_pipeline(steps=[1, 2, 3, 4], job_name="测试流水线", date_filter=date_filter)
    logger.info("测试完成")


def main():
    parser = argparse.ArgumentParser(description="定时任务调度器")
    parser.add_argument("--test", action="store_true", help="测试模式（立即执行一次）")
    parser.add_argument("--date", type=str, help="日期过滤，格式 YYYYMMDD（默认为当天）")
    parser.add_argument("--daemon", action="store_true", help="后台运行模式")
    args = parser.parse_args()

    # 确保日志目录存在
    LOGS_DIR.mkdir(exist_ok=True)

    if args.test:
        test_mode(date_filter=args.date)
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
