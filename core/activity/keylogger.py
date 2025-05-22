#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
键盘记录器模块 - 用于记录编程相关应用的键盘输入次数
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, date

# 仅在Windows上导入这些模块
try:
    import keyboard
except ImportError:
    pass

# 导入事件系统
from core.events import EventSystem

logger = logging.getLogger(__name__)

class KeyLogger:
    """
    键盘记录器，统计编程时的键盘输入
    注意：该模块只会在编程相关应用激活时工作
    """
    
    def __init__(self, event_system: EventSystem, config: Any):
        """
        初始化键盘记录器
        
        Args:
            event_system: 全局事件系统
            config: 配置管理器实例
        """
        self.event_system = event_system
        self.config = config
        
        # 检查是否启用键盘记录功能
        self.enabled = self.config.get_setting('stats.enable_keylogger', True)
        
        # 统计数据
        self.keypress_count = 0
        self.key_stats = {}  # 记录每个键的按下次数
        self.hourly_stats = {hour: 0 for hour in range(24)}  # 按小时统计
        self.is_programming_mode = False  # 是否处于编程模式
        
        # 线程控制
        self.is_running = False
        self.hook_thread = None
        
        # 注册事件处理
        self.event_system.register('programming_started', self._on_programming_started)
        self.event_system.register('programming_ended', self._on_programming_ended)
        self.event_system.register('programming_idle', self._on_programming_idle)
        
        # 如果启用，立即开始监听
        if self.enabled:
            self.start()
    
    def start(self) -> None:
        """启动键盘记录"""
        if not self.enabled or self.is_running:
            return
        
        self.is_running = True
        self.hook_thread = threading.Thread(target=self._keyboard_hook, daemon=True)
        self.hook_thread.start()
        logger.info("键盘记录器已启动")
    
    def stop(self) -> None:
        """停止键盘记录"""
        self.is_running = False
        # 如果线程在运行，等待它结束
        if self.hook_thread and self.hook_thread.is_alive():
            self.hook_thread.join(timeout=1.0)
        # 尝试取消键盘钩子
        try:
            keyboard.unhook_all()
        except:
            pass
        logger.info("键盘记录器已停止")
    
    def _keyboard_hook(self) -> None:
        """设置键盘钩子监听按键"""
        try:
            # 注册按键回调
            keyboard.on_press(self._on_key_press)
            logger.debug("键盘钩子设置成功")
            
            # 保持线程运行直到停止信号
            while self.is_running:
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"设置键盘钩子时出错: {e}", exc_info=True)
        finally:
            # 清理钩子
            try:
                keyboard.unhook_all()
            except:
                pass
    
    def _on_key_press(self, event) -> None:
        """
        按键按下回调函数
        
        Args:
            event: 键盘事件对象
        """
        # 只有在编程模式下才记录按键
        if not self.is_programming_mode:
            return
        
        # 获取按键名称
        key_name = event.name if hasattr(event, 'name') else "unknown"
        
        # 更新统计数据
        self.keypress_count += 1
        self.key_stats[key_name] = self.key_stats.get(key_name, 0) + 1
        
        # 更新小时统计
        current_hour = datetime.now().hour
        self.hourly_stats[current_hour] += 1
        
        # 每100次按键记录一次日志和发送事件
        if self.keypress_count % 100 == 0:
            logger.debug(f"键盘输入计数: {self.keypress_count}")
            
        # 触发按键事件
        self.event_system.emit('keypress', {
            'key': key_name,
            'count': self.keypress_count,
            'timestamp': time.time()
        })
    
    def _on_programming_started(self, event_data: Dict[str, Any]) -> None:
        """
        编程开始事件处理
        
        Args:
            event_data: 事件数据
        """
        self.is_programming_mode = True
        logger.debug(f"进入编程模式，开始记录按键 - 应用: {event_data.get('app', '')}")
    
    def _on_programming_ended(self, event_data: Dict[str, Any]) -> None:
        """
        编程结束事件处理
        
        Args:
            event_data: 事件数据
        """
        self.is_programming_mode = False
        logger.debug(f"退出编程模式，停止记录按键 - 应用: {event_data.get('app', '')}")
    
    def _on_programming_idle(self, event_data: Dict[str, Any]) -> None:
        """
        编程空闲事件处理
        
        Args:
            event_data: 事件数据
        """
        self.is_programming_mode = False
        logger.debug(f"编程空闲，停止记录按键 - 空闲时间: {event_data.get('idle_time', 0)}秒")
    
    def get_key_stats(self) -> Dict[str, Any]:
        """
        获取按键统计信息
        
        Returns:
            包含按键统计的字典
        """
        # 按频率排序最常用的键
        sorted_keys = sorted(self.key_stats.items(), key=lambda x: x[1], reverse=True)
        top_keys = dict(sorted_keys[:10]) if sorted_keys else {}
        
        return {
            'total_keypresses': self.keypress_count,
            'top_keys': top_keys,
            'hourly_breakdown': self.hourly_stats
        }
    
    def reset_daily_stats(self) -> None:
        """重置每日统计数据"""
        self.keypress_count = 0
        self.key_stats = {}
        self.hourly_stats = {hour: 0 for hour in range(24)}
        logger.info("键盘统计数据已重置")
