#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodePet - 你的编程桌宠助手
主程序入口
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import time

# 导入核心模块
from core.activity.tracker import ActivityTracker
from core.stats.logger import StatsLogger
from core.pet.controller import PetController
from core.events import EventSystem
from core.scheduler.jobs import JobScheduler

# 导入界面相关模块
from ui.window import MainWindow
from ui.tray import SystemTray

# 导入配置
from utils.system_utils import setup_environment, check_first_run
from config.config_manager import ConfigManager


def setup_logging():
    """设置日志系统"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'codepet.log')
    
    # 设置日志格式和级别
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 文件处理器 (10MB大小，保留5个备份)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger


def main():
    """程序主入口"""
    # 设置日志
    logger = setup_logging()
    logger.info("CodePet 正在启动...")
    
    # 检查环境
    setup_environment()
    
    # 加载配置
    config = ConfigManager()
    
    # 首次运行检查
    if check_first_run():
        logger.info("首次运行，执行初始化配置...")
        config.create_default_config()
    
    # 初始化事件系统
    event_system = EventSystem()
    
    # 初始化统计记录
    stats_logger = StatsLogger(config)
    
    # 初始化活动跟踪
    activity_tracker = ActivityTracker(event_system, config)
    
    # 初始化宠物控制器
    pet_controller = PetController(config, event_system)
    
    # 初始化定时任务
    job_scheduler = JobScheduler(event_system, config)
    
    # 启动UI
    main_window = MainWindow(pet_controller, event_system, config)
    system_tray = SystemTray(main_window, event_system)
    
    # 启动所有组件
    activity_tracker.start()
    job_scheduler.start()
    
    # 启动UI事件循环
    try:
        logger.info("CodePet 已成功启动")
        main_window.run()
    except KeyboardInterrupt:
        logger.info("接收到终止信号，正在关闭程序...")
    except Exception as e:
        logger.error(f"运行过程中出现错误: {e}", exc_info=True)
    finally:
        # 清理资源和保存数据
        activity_tracker.stop()
        job_scheduler.stop()
        stats_logger.save_daily_stats()
        logger.info("CodePet 已安全关闭")


if __name__ == "__main__":
    main()
