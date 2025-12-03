#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海云媒体积分任务自动化脚本

该脚本用于自动执行上海云媒体的积分任务，包括：
- 读取账号配置信息
- 获取任务列表
- 查询积分和签到信息
- 输出任务完成情况统计

Author: Assistant
Date: 2025-11-06
"""

import json
import logging
import os
import sys
import time
import random
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# 添加当前目录到sys.path以支持直接导入
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 添加父目录到sys.path以支持导入推送模块
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from api import  ShypAPI

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 添加父目录的父目录到sys.path以导入notification模块
notification_dir = os.path.dirname(parent_dir)
if notification_dir not in sys.path:
    sys.path.insert(0, notification_dir)

from notify import send

# ==================== 延迟时间常量配置 (秒) ====================
# 账号级别延迟
DELAY_BETWEEN_ACCOUNTS = (5, 10)     # 账号间切换延迟

# 任务级别延迟
DELAY_BETWEEN_TASKS = (5, 10)         # 大任务间切换延迟（阅读→视频→收藏）

# 操作级别延迟
DELAY_BETWEEN_ARTICLES = (2, 4)      # 文章间延迟（阅读任务）
DELAY_BETWEEN_VIDEOS = (10, 15)        # 视频间延迟（视频任务）
DELAY_BETWEEN_FAVORS = (15, 20)        # 收藏操作间延迟（收藏任务）
DELAY_AFTER_FAVOR = (1, 2)           # 收藏后取消收藏前的延迟
DELAY_BETWEEN_COMMENTS = (30, 35)    # 评论操作间延迟（评论任务）
DELAY_BETWEEN_SHARES = (5, 10)        # 分享操作间延迟（分享任务）

# 评论内容库
COMMENT_CONTENTS = [
    "👍",
    "写得好",
    "支持",
    "不错",
    "很好",
    "赞",
    "有意义",
    "学习了",
    "感谢分享",
    "受益匪浅"
]


class ShypTasks:
    """上海云媒体积分任务自动化执行类"""

    def __init__(self, config_file: str = "token.json", config_path: str = None):
        """
        初始化任务执行器

        Args:
            config_file (str): 配置文件路径，默认为token.json（已弃用，保留用于兼容性）
            config_path (str): 配置文件的完整路径，如果为None则使用项目根目录下的config/token.json
        """
        # 设置配置文件路径
        if config_path is None:
            self.config_path = project_root / "config" / "token.json"
        else:
            self.config_path = Path(config_path)

        self.config_file = config_file  # 保留用于兼容性
        self.accounts: List[Dict[str, Any]] = []
        self.logger = self._setup_logger()
        self._init_accounts()
        # 任务统计数据
        self.account_results: List[Dict[str, Any]] = []

    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        logger = logging.getLogger("ShypTasks")
        logger.setLevel(logging.INFO)

        # 清除已存在的处理器
        if logger.handlers:
            logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 文件处理器
        log_file = os.path.join(os.path.dirname(__file__), "shyp_tasks.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _init_accounts(self):
        """从环境变量或配置文件加载配置"""
        # 优先从环境变量读取配置
        env_config = os.getenv('SHYP_CONFIG')
        if env_config:
            try:
                self.logger.info("从环境变量读取上海云媒体配置")
                config = json.loads(env_config)
                # 如果环境变量是完整的配置对象
                if 'shyp' in config:
                    shyp_config = config.get('shyp', {})
                else:
                    # 如果环境变量直接是 shyp 配置
                    shyp_config = config
                self.accounts = shyp_config.get('accounts', [])
                if self.accounts:
                    self.logger.info(f"从环境变量成功加载 {len(self.accounts)} 个账号配置")
                    return
            except json.JSONDecodeError as e:
                self.logger.warning(f"环境变量配置JSON解析失败: {e}，将尝试从文件读取")
            except Exception as e:
                self.logger.warning(f"读取环境变量配置失败: {e}，将尝试从文件读取")
        
        # 如果环境变量没有配置或解析失败，从文件读取
        try:
            self.logger.info(f"正在读取配置文件: {self.config_path}")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 获取上海云媒体的配置
            shyp_config = config.get('shyp', {})
            self.accounts = shyp_config.get('accounts', [])

            if not self.accounts:
                self.logger.warning("配置文件中没有找到账号信息")
            else:
                self.logger.info(f"从配置文件成功加载 {len(self.accounts)} 个账号配置")

        except FileNotFoundError:
            self.logger.error(f"配置文件不存在: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件JSON格式错误: {e}")
            raise
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise


    def _random_delay(self, delay_range: tuple):
        """
        随机延迟

        Args:
            delay_range (tuple): 延迟时间范围 (最小值, 最大值)
        """
        delay = random.uniform(delay_range[0], delay_range[1])
        time.sleep(delay)

    def do_read_task(self, api: ShypAPI, task_info: Dict[str, Any]) -> int:
        """
        执行阅读文章任务

        Args:
            api: API实例
            task_info: 任务信息

        Returns:
            int: 成功完成的阅读数量
        """
        progress = task_info.get('progress', 0)
        total_progress = task_info.get('total_progress', 15)

        # 计算还需要阅读的文章数
        remaining = total_progress - progress

        if remaining <= 0:
            self.logger.info("📖 阅读任务已完成，无需操作")
            return 0

        self.logger.info(f"📖 开始执行阅读任务，需要阅读 {remaining} 篇文章")

        # 获取文章列表
        article_list = api.get_article_list(page_size=remaining)
        if not article_list:
            self.logger.error("获取文章列表失败")
            return 0

        articles = article_list.get('data', {}).get('records', [])
        if not articles:
            self.logger.warning("文章列表为空")
            return 0

        success_count = 0

        # 阅读文章
        for i, article in enumerate(articles[:remaining], 1):
            article_id = article.get('id')
            article_title = article.get('title', '未知标题')

            self.logger.info(f"[{i}/{remaining}] 正在阅读: {article_title[:30]}...")

            # 增加阅读计数
            if api.increase_read_count(article_id):
                # 完成阅读任务（提交积分）
                if api.complete_read_task():
                    success_count += 1
                    self.logger.info(f"✅ 阅读完成 ({success_count}/{remaining})")
                else:
                    self.logger.warning(f"⚠️ 提交积分失败")
            else:
                self.logger.warning(f"⚠️ 增加阅读计数失败")

            # 文章间延迟
            if i < len(articles):
                delay = random.uniform(DELAY_BETWEEN_ARTICLES[0], DELAY_BETWEEN_ARTICLES[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

        self.logger.info(f"📖 阅读任务完成，成功阅读 {success_count} 篇文章")
        return success_count

    def do_favor_task(self, api: ShypAPI, task_info: Dict[str, Any]) -> int:
        """
        执行收藏任务

        Args:
            api: API实例
            task_info: 任务信息

        Returns:
            int: 成功完成的收藏数量
        """
        progress = task_info.get('progress', 0)
        total_progress = task_info.get('total_progress', 5)

        # 计算还需要收藏的文章数
        remaining = total_progress - progress

        if remaining <= 0:
            self.logger.info("⭐ 收藏任务已完成，无需操作")
            return 0

        self.logger.info(f"⭐ 开始执行收藏任务，需要收藏 {remaining} 篇内容")

        # 获取文章列表
        article_list = api.get_article_list(page_size=remaining)
        if not article_list:
            self.logger.error("获取文章列表失败")
            return 0

        articles = article_list.get('data', {}).get('records', [])
        if not articles:
            self.logger.warning("文章列表为空")
            return 0

        success_count = 0

        # 收藏文章
        for i, article in enumerate(articles[:remaining], 1):
            article_id = article.get('id')
            article_title = article.get('title', '未知标题')

            self.logger.info(f"[{i}/{remaining}] 正在收藏: {article_title[:30]}...")

            # 收藏内容
            if api.favor_content(article_id):
                success_count += 1
                self.logger.info(f"✅ 收藏完成 ({success_count}/{remaining})")

                # 收藏后延迟，然后取消收藏（为了下次还能完成任务）
                delay = random.uniform(DELAY_AFTER_FAVOR[0], DELAY_AFTER_FAVOR[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后取消收藏...")
                time.sleep(delay)

                # 取消收藏
                api.disfavor_content(article_id)
            else:
                self.logger.warning(f"⚠️ 收藏失败")

            # 收藏操作间延迟
            if i < len(articles):
                delay = random.uniform(DELAY_BETWEEN_FAVORS[0], DELAY_BETWEEN_FAVORS[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

        self.logger.info(f"⭐ 收藏任务完成，成功收藏 {success_count} 篇内容")
        return success_count

    def do_comment_task(self, api: ShypAPI, task_info: Dict[str, Any]) -> int:
        """
        执行评论任务

        Args:
            api: API实例
            task_info: 任务信息

        Returns:
            int: 成功完成的评论数量
        """
        progress = task_info.get('progress', 0)
        total_progress = task_info.get('total_progress', 10)

        # 计算还需要评论的数量
        remaining = total_progress - progress

        if remaining <= 0:
            self.logger.info("💬 评论任务已完成，无需操作")
            return 0

        self.logger.info(f"💬 开始执行评论任务，需要评论 {remaining} 篇内容")

        # 获取2页文章列表（20篇）
        all_articles = []
        for page in range(1, 3):  # 获取第1页和第2页
            self.logger.info(f"正在获取第 {page} 页文章...")
            article_list = api.get_article_list(page_no=page, page_size=10)
            if article_list:
                articles = article_list.get('data', {}).get('records', [])
                all_articles.extend(articles)
                self.logger.info(f"获取到 {len(articles)} 篇文章")

            # 翻页间延迟
            if page < 2:
                delay = random.uniform(1, 2)
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后获取下一页...")
                time.sleep(delay)

        if not all_articles:
            self.logger.warning("文章列表为空")
            return 0

        self.logger.info(f"共获取到 {len(all_articles)} 篇文章，随机选择 {remaining} 篇进行评论")

        # 随机选择文章进行评论
        selected_articles = random.sample(all_articles, min(remaining, len(all_articles)))
        success_count = 0

        # 评论文章
        for i, article in enumerate(selected_articles, 1):
            article_id = article.get('id')
            article_title = article.get('title', '未知标题')

            # 随机选择评论内容
            comment_content = random.choice(COMMENT_CONTENTS)

            self.logger.info(f"[{i}/{remaining}] 正在评论: {article_title[:30]}...")
            self.logger.info(f"评论内容: {comment_content}")

            # 添加评论
            if api.add_comment(article_id, comment_content):
                success_count += 1
                self.logger.info(f"✅ 评论完成 ({success_count}/{remaining})")
            else:
                self.logger.warning(f"⚠️ 评论失败")

            # 评论间延迟
            if i < len(selected_articles):
                delay = random.uniform(DELAY_BETWEEN_COMMENTS[0], DELAY_BETWEEN_COMMENTS[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

        self.logger.info(f"💬 评论任务完成，成功评论 {success_count} 篇内容")
        return success_count

    def do_share_task(self, api: ShypAPI, task_info: Dict[str, Any]) -> int:
        """
        执行分享任务

        Args:
            api: API实例
            task_info: 任务信息

        Returns:
            int: 成功完成的分享数量
        """
        progress = task_info.get('progress', 0)
        total_progress = task_info.get('total_progress', 5)

        # 计算还需要分享的文章数
        remaining = total_progress - progress

        if remaining <= 0:
            self.logger.info("📤 分享任务已完成，无需操作")
            return 0

        self.logger.info(f"📤 开始执行分享任务，需要分享 {remaining} 篇文章")

        # 获取文章列表
        article_list = api.get_article_list(page_size=remaining)
        if not article_list:
            self.logger.error("获取文章列表失败")
            return 0

        articles = article_list.get('data', {}).get('records', [])
        if not articles:
            self.logger.warning("文章列表为空")
            return 0

        success_count = 0

        # 分享文章
        for i, article in enumerate(articles[:remaining], 1):
            article_id = article.get('id')
            article_title = article.get('title', '未知标题')

            self.logger.info(f"[{i}/{remaining}] 正在分享: {article_title[:30]}...")

            # 先增加阅读计数（模拟打开文章）
            if api.increase_read_count(article_id):
                # 完成分享任务（提交积分）
                if api.complete_share_task():
                    success_count += 1
                    self.logger.info(f"✅ 分享完成 ({success_count}/{remaining})")
                else:
                    self.logger.warning(f"⚠️ 提交积分失败")
            else:
                self.logger.warning(f"⚠️ 增加阅读计数失败")

            # 分享间延迟
            if i < len(articles):
                delay = random.uniform(DELAY_BETWEEN_SHARES[0], DELAY_BETWEEN_SHARES[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

        self.logger.info(f"📤 分享任务完成，成功分享 {success_count} 篇文章")
        return success_count

    def do_video_task(self, api: ShypAPI, task_info: Dict[str, Any]) -> int:
        """
        执行观看视频任务

        Args:
            api: API实例
            task_info: 任务信息

        Returns:
            int: 成功完成的观看数量
        """
        progress = task_info.get('progress', 0)
        total_progress = task_info.get('total_progress', 10)

        # 计算还需要观看的视频数
        remaining = total_progress - progress

        if remaining <= 0:
            self.logger.info("📺 视频任务已完成，无需操作")
            return 0

        self.logger.info(f"📺 开始执行视频任务，需要观看 {remaining} 个视频")

        # 获取视频列表
        video_list = api.get_video_list(page_size=remaining)
        if not video_list:
            self.logger.error("获取视频列表失败")
            return 0

        videos = video_list.get('data', {}).get('records', [])
        if not videos:
            self.logger.warning("视频列表为空")
            return 0

        success_count = 0

        # 观看视频
        for i, video in enumerate(videos[:remaining], 1):
            video_id = video.get('id')
            video_title = video.get('title', '未知标题')

            self.logger.info(f"[{i}/{remaining}] 正在观看: {video_title[:30]}...")

            # 获取视频详情
            if api.get_video_detail(video_id):
                # 完成视频任务（提交积分）
                if api.complete_video_task():
                    success_count += 1
                    self.logger.info(f"✅ 观看完成 ({success_count}/{remaining})")
                else:
                    self.logger.warning(f"⚠️ 提交积分失败")
            else:
                self.logger.warning(f"⚠️ 获取视频详情失败")

            # 视频间延迟
            if i < len(videos):
                delay = random.uniform(DELAY_BETWEEN_VIDEOS[0], DELAY_BETWEEN_VIDEOS[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

        self.logger.info(f"📺 视频任务完成，成功观看 {success_count} 个视频")
        return success_count

    def check_account_tasks(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查单个账号的任务情况

        Args:
            account (Dict): 账号信息

        Returns:
            Dict: 账号任务执行统计
        """
        account_name = account.get('account_name', '未知账号')
        token = account.get('token')
        device_id = account.get('device_id')
        site_id = account.get('site_id', '310110')

        # 初始化结果统计
        result = {
            'account_name': account_name,
            'success': False,
            'error': None,
            'before_stats': None,
            'after_stats': None,
            'executed_tasks': []
        }

        self.logger.info(f"{'='*60}")
        self.logger.info(f"开始处理账号: {account_name}")
        self.logger.info(f"{'='*60}")

        # 验证必要参数
        if not token:
            self.logger.error(f"账号 {account_name} 缺少token信息")
            result['error'] = '缺少token信息'
            return result

        if not device_id:
            self.logger.error(f"账号 {account_name} 缺少device_id信息")
            result['error'] = '缺少device_id信息'
            return result

        try:
            # 创建API实例
            api = ShypAPI(token=token, device_id=device_id, site_id=site_id, user_agent=account.get('user_agent'))

            # 检查token有效性
            if not api.check_token_validity():
                self.logger.error(f"账号 {account_name} token无效，跳过该账号")
                result['error'] = 'token无效'
                return result

            # 获取积分信息和任务列表
            score_info = api.get_score_info()
            if not score_info:
                self.logger.error(f"账号 {account_name} 获取任务列表失败")
                result['error'] = '获取任务列表失败'
                return result

            # 解析任务信息
            task_summary = api.parse_task_list(score_info)
            result['before_stats'] = task_summary.copy()

            # 输出任务统计
            self._print_task_summary(account_name, task_summary)

            # 查找待执行的任务
            read_task = None
            video_task = None
            favor_task = None
            comment_task = None
            share_task = None
            for task in task_summary.get('all_tasks', []):
                if task.get('id') == '002':  # 阅读文章任务ID
                    read_task = task
                elif task.get('id') == '003':  # 观看视频任务ID
                    video_task = task
                elif task.get('id') == '005':  # 收藏任务ID
                    favor_task = task
                elif task.get('id') == '006':  # 评论任务ID
                    comment_task = task
                elif task.get('id') == '007':  # 分享任务ID
                    share_task = task

            executed_tasks = []  # 记录执行的任务

            # 执行阅读任务
            if read_task and read_task.get('status') != '1':
                self.logger.info(f"\n{'─'*60}")
                count = self.do_read_task(api, read_task)
                self.logger.info(f"{'─'*60}\n")
                executed_tasks.append({'type': 'read', 'count': count})
                result['executed_tasks'].append('阅读')

                # 任务间延迟
                if video_task or favor_task or comment_task or share_task:
                    delay = random.uniform(DELAY_BETWEEN_TASKS[0], DELAY_BETWEEN_TASKS[1])
                    self.logger.info(f"⏳ 等待 {delay:.1f} 秒后执行下一个任务...")
                    time.sleep(delay)

            # 执行视频任务
            if video_task and video_task.get('status') != '1':
                self.logger.info(f"\n{'─'*60}")
                count = self.do_video_task(api, video_task)
                self.logger.info(f"{'─'*60}\n")
                executed_tasks.append({'type': 'video', 'count': count})
                result['executed_tasks'].append('视频')

                # 任务间延迟
                if favor_task or comment_task or share_task:
                    delay = random.uniform(DELAY_BETWEEN_TASKS[0], DELAY_BETWEEN_TASKS[1])
                    self.logger.info(f"⏳ 等待 {delay:.1f} 秒后执行下一个任务...")
                    time.sleep(delay)

            # 执行收藏任务
            if favor_task and favor_task.get('status') != '1':
                self.logger.info(f"\n{'─'*60}")
                count = self.do_favor_task(api, favor_task)
                self.logger.info(f"{'─'*60}\n")
                executed_tasks.append({'type': 'favor', 'count': count})
                result['executed_tasks'].append('收藏')

                # 任务间延迟
                if comment_task or share_task:
                    delay = random.uniform(DELAY_BETWEEN_TASKS[0], DELAY_BETWEEN_TASKS[1])
                    self.logger.info(f"⏳ 等待 {delay:.1f} 秒后执行下一个任务...")
                    time.sleep(delay)

            # 执行评论任务
            if comment_task and comment_task.get('status') != '1':
                self.logger.info(f"\n{'─'*60}")
                count = self.do_comment_task(api, comment_task)
                self.logger.info(f"{'─'*60}\n")
                executed_tasks.append({'type': 'comment', 'count': count})
                result['executed_tasks'].append('评论')

                # 任务间延迟
                if share_task:
                    delay = random.uniform(DELAY_BETWEEN_TASKS[0], DELAY_BETWEEN_TASKS[1])
                    self.logger.info(f"⏳ 等待 {delay:.1f} 秒后执行下一个任务...")
                    time.sleep(delay)

            # 执行分享任务
            if share_task and share_task.get('status') != '1':
                self.logger.info(f"\n{'─'*60}")
                count = self.do_share_task(api, share_task)
                self.logger.info(f"{'─'*60}\n")
                executed_tasks.append({'type': 'share', 'count': count})
                result['executed_tasks'].append('分享')

            # 如果执行了任务，重新获取任务状态
            if executed_tasks:
                self.logger.info("🔄 正在刷新任务状态...")
                delay = random.uniform(DELAY_BETWEEN_TASKS[0], DELAY_BETWEEN_TASKS[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后刷新...")
                time.sleep(delay)
                score_info = api.get_score_info()
                if score_info:
                    task_summary = api.parse_task_list(score_info)
                    result['after_stats'] = task_summary.copy()
                    self.logger.info("📊 更新后的任务状态:")
                    self._print_task_summary(account_name, task_summary)

            self.logger.info(f"账号 {account_name} 处理完成")
            result['success'] = True
            return result

        except Exception as e:
            self.logger.error(f"账号 {account_name} 处理异常: {str(e)}", exc_info=True)
            result['error'] = str(e)
            return result

    def _print_task_summary(self, account_name: str, task_summary: Dict[str, Any]):
        """
        打印任务摘要信息

        Args:
            account_name (str): 账号名称
            task_summary (Dict): 任务摘要信息
        """
        self.logger.info(f"\n{'─'*60}")
        self.logger.info(f"📊 账号【{account_name}】任务统计")
        self.logger.info(f"{'─'*60}")

        # 积分信息
        self.logger.info(f"💰 总积分: {task_summary.get('total_score', 0)}")
        self.logger.info(f"📈 今日积分: {task_summary.get('today_point', 0)} (+{task_summary.get('today_increase_point', 0)})")

        # 签到信息
        sign_status = task_summary.get('sign_status', {})
        self.logger.info(f"📅 签到状态: {sign_status.get('sign_title', '未知')}")

        # 任务完成情况
        completed = len(task_summary.get('completed_tasks', []))
        incomplete = len(task_summary.get('incomplete_tasks', []))
        total = completed + incomplete

        self.logger.info(f"✅ 已完成任务: {completed}/{total}")
        self.logger.info(f"⏳ 未完成任务: {incomplete}/{total}")

        # 已完成任务详情
        if task_summary.get('completed_tasks'):
            self.logger.info(f"\n✅ 已完成任务列表:")
            for task in task_summary['completed_tasks']:
                progress = f"{task['progress']}/{task['total_progress']}"
                self.logger.info(f"  • {task['title']} ({progress}) - {task['summary']}")

        # 未完成任务详情
        if task_summary.get('incomplete_tasks'):
            self.logger.info(f"\n⏳ 未完成任务列表:")
            for task in task_summary['incomplete_tasks']:
                progress = f"{task['progress']}/{task['total_progress']}"
                self.logger.info(f"  • {task['title']} ({progress}) - {task['summary']}")

        self.logger.info(f"{'─'*60}\n")

    def send_task_notification(self, start_time: datetime, end_time: datetime) -> None:
        """
        发送任务执行汇总推送通知

        Args:
            start_time: 任务开始时间
            end_time: 任务结束时间
        """
        try:
            duration = (end_time - start_time).total_seconds()

            # 计算成功和失败数量
            success_count = sum(1 for r in self.account_results if r.get('success'))
            fail_count = len(self.account_results) - success_count

            # 构建推送标题
            if fail_count == 0:
                title = "上海云媒体任务完成 ✅"
            else:
                title = f"上海云媒体任务完成 ⚠️"

            # 构建推送内容
            content_parts = [
                "📊 执行摘要",
                "━━━━━━━━━━━━━━━━",
                f"👥 账号总数: {len(self.account_results)}个",
                f"✅ 成功: {success_count}个",
            ]

            if fail_count > 0:
                content_parts.append(f"❌ 失败: {fail_count}个")

            content_parts.extend([
                f"⏱️ 总耗时: {int(duration)}秒 ({duration/60:.1f}分钟)",
                "",
                "📋 账号详情",
                "━━━━━━━━━━━━━━━━"
            ])

            # 添加每个账号的详细信息
            for i, result in enumerate(self.account_results, 1):
                account_name = result.get('account_name', f'账号{i}')

                if not result.get('success'):
                    # 失败账号
                    error = result.get('error', '未知错误')
                    content_parts.append(f"❌ [{account_name}]")
                    content_parts.append(f"   错误: {error}")
                else:
                    # 成功账号
                    before_stats = result.get('before_stats', {})
                    after_stats = result.get('after_stats', {})
                    executed_tasks = result.get('executed_tasks', [])

                    before_points = before_stats.get('today_point', 0)
                    after_points = after_stats.get('today_point', 0) if after_stats else before_points
                    earned_points = after_points - before_points

                    content_parts.append(f"✅ [{account_name}]")

                    if after_stats:
                        total_score = after_stats.get('total_score', 0)
                        content_parts.append(f"   💰 总积分: {total_score}")
                        content_parts.append(f"   📈 今日获得: +{earned_points}分")

                        # 任务完成情况
                        completed = len(after_stats.get('completed_tasks', []))
                        incomplete = len(after_stats.get('incomplete_tasks', []))
                        total_tasks = completed + incomplete
                        content_parts.append(f"   ✅ 任务进度: {completed}/{total_tasks}")

                    if executed_tasks:
                        content_parts.append(f"   🎯 执行: {', '.join(executed_tasks)}")

                # 账号之间添加空行
                if i < len(self.account_results):
                    content_parts.append("")

            # 添加完成时间
            content_parts.append("━━━━━━━━━━━━━━━━")
            content_parts.append(f"🕐 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

            content = "\n".join(content_parts)

            # 发送推送
            send(title, content)
            self.logger.info("✅ 任务汇总推送发送成功")

        except Exception as e:
            self.logger.error(f"❌ 发送任务汇总推送失败: {str(e)}", exc_info=True)

    def run(self):
        """
        执行所有账号的任务
        """
        if not self.accounts:
            self.logger.error("没有可用的账号，程序退出")
            return

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🚀 上海云媒体积分任务脚本启动")
        self.logger.info(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"👥 账号数量: {len(self.accounts)}")
        self.logger.info(f"{'='*60}\n")

        # 遍历所有账号
        for index, account in enumerate(self.accounts, 1):
            self.logger.info(f"\n处理第 {index}/{len(self.accounts)} 个账号")

            # 执行账号任务并收集结果
            result = self.check_account_tasks(account)
            self.account_results.append(result)

            # 账号间延迟（最后一个账号不需要延迟）
            if index < len(self.accounts):
                delay = random.uniform(DELAY_BETWEEN_ACCOUNTS[0], DELAY_BETWEEN_ACCOUNTS[1])
                self.logger.info(f"⏳ 等待 {delay:.1f} 秒后处理下一个账号...\n")
                time.sleep(delay)

        # 计算成功和失败数量
        success_count = sum(1 for r in self.account_results if r.get('success'))
        fail_count = len(self.account_results) - success_count

        # 输出总结
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📝 执行总结")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"✅ 成功: {success_count} 个账号")
        self.logger.info(f"❌ 失败: {fail_count} 个账号")
        self.logger.info(f"📊 总计: {len(self.accounts)} 个账号")
        self.logger.info(f"{'='*60}\n")



def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    print(f"## 开始执行... {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 创建任务执行器
        tasks = ShypTasks()

        # 执行任务
        tasks.run()

        # 记录结束时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"## 执行结束... {end_time.strftime('%Y-%m-%d %H:%M:%S')} 耗时 {int(duration)} 秒")

        # 发送任务汇总推送
        tasks.send_task_notification(start_time, end_time)

    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

