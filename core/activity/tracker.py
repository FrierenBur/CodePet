#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
活动追踪器模块 - 监控编程应用的活动窗口
"""

import os
import time
import logging
import threading
from typing import List, Dict, Any, Optional

# 仅在Windows上导入这些模块
try:
    import win32gui
    import win32process
    import win32api
    import psutil
except ImportError:
    pass

# 从事件中心导入事件系统
from core.events import EventSystem

logger = logging.getLogger(__name__)

class ActivityTracker:
    """
    程序使用活动追踪器，监控用户正在使用的窗口应用程序
    """
    
    def __init__(self, event_system: EventSystem, config: Any):
        """
        初始化活动跟踪器
        
        Args:
            event_system: 全局事件系统
            config: 配置管理器实例
        """
        self.event_system = event_system
        self.config = config
        
        # 从配置中获取监控的应用列表
        self.programming_apps = self.config.get_setting('stats.programming_apps', [])
        self.idle_threshold = self.config.get_setting('stats.record_idle_threshold', 300)
        
        # 追踪状态
        self.is_running = False
        self.is_programming = False
        self.current_app = ""
        self.current_window_title = ""
        self.last_activity_time = time.time()
        self.total_programming_time = 0
        self.programming_sessions = []
        
        # 线程
        self.tracker_thread = None
        
        # 注册事件监听
        self.event_system.register('keypress', self._on_keypress)
    
    def start(self) -> None:
        """启动活动追踪"""
        if self.is_running:
            return
        
        self.is_running = True
        self.tracker_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracker_thread.start()
        logger.info("活动追踪器已启动")
        
    def stop(self) -> None:
        """停止活动追踪"""
        self.is_running = False
        if self.tracker_thread and self.tracker_thread.is_alive():
            self.tracker_thread.join(timeout=1.0)
        logger.info("活动追踪器已停止")
        
    def _tracking_loop(self) -> None:
        """追踪循环主函数"""
        check_interval = 1.0  # 窗口检查间隔(秒)
        
        while self.is_running:
            try:
                self._check_active_window()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"窗口追踪错误: {e}", exc_info=True)
                time.sleep(check_interval * 2)  # 出错时增加延迟
    
    def _check_active_window(self) -> None:
        """
        检查当前活动窗口，判断是否为编程相关应用
        仅适用于Windows系统
        """
        try:
            # 获取当前活动窗口
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            # 获取进程信息
            try:
                process = psutil.Process(pid)
                process_name = process.name().lower()
                window_title = win32gui.GetWindowText(hwnd)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = ""
                window_title = ""
            
            # 判断是否为编程应用
            was_programming = self.is_programming
            self.current_app = process_name
            self.current_window_title = window_title
            
            # 检查是否是我们要追踪的应用程序
            self.is_programming = any(app.lower() in process_name.lower() for app in self.programming_apps)
            
            # 如果是浏览器，检查网页标题是否包含编程相关网站
            if process_name.endswith(('chrome.exe', 'msedge.exe', 'firefox.exe')) and not self.is_programming:
                programming_sites = ['github', 'stackoverflow', 'gitlab', 'bitbucket', 'docs.python', 'developer.mozilla']
                self.is_programming = any(site in window_title.lower() for site in programming_sites)
            
            # 如果状态改变，发送事件
            if was_programming != self.is_programming:
                if self.is_programming:
                    # 切换到编程状态
                    self.event_system.emit('programming_started', {
                        'app': self.current_app,
                        'title': self.current_window_title
                    })
                    logger.debug(f"编程会话开始: {self.current_app} - {self.current_window_title}")
                    self._start_programming_session()
                else:
                    # 离开编程状态
                    duration = self._end_programming_session()
                    self.event_system.emit('programming_ended', {
                        'app': self.current_app,
                        'title': self.current_window_title,
                        'duration': duration
                    })
                    logger.debug(f"编程会话结束: {self.current_app} - 持续时间: {duration:.2f}秒")
            
            # 检查空闲状态
            idle_time = self._get_system_idle_time()
            if idle_time > self.idle_threshold:
                if self.is_programming:
                    # 如果超过空闲阈值，结束编程会话
                    duration = self._end_programming_session()
                    self.is_programming = False
                    self.event_system.emit('programming_idle', {
                        'idle_time': idle_time,
                        'duration': duration
                    })
                    logger.debug(f"编程会话因空闲结束 - 空闲时间: {idle_time}秒, 会话时间: {duration:.2f}秒")
            
        except Exception as e:
            logger.error(f"检查活动窗口时出错: {e}", exc_info=True)
    
    def _get_system_idle_time(self) -> float:
        """
        获取系统空闲时间（秒）
        仅适用于Windows系统
        
        Returns:
            系统空闲时间（秒）
        """
        try:
            # 获取上次输入信息
            last_input_info = win32api.GetLastInputInfo()
            current_tick = win32api.GetTickCount()
            idle_time = (current_tick - last_input_info) / 1000.0  # 转换为秒
            return idle_time
        except Exception as e:
            logger.error(f"获取系统空闲时间出错: {e}", exc_info=True)
            return 0.0
    
    def _on_keypress(self, event_data: Dict[str, Any]) -> None:
        """
        键盘输入事件回调，更新最后活动时间
        
        Args:
            event_data: 事件数据，包含按键信息
        """
        self.last_activity_time = time.time()
    
    def _start_programming_session(self) -> None:
        """开始一个新的编程会话"""
        self.programming_sessions.append({
            'start_time': time.time(),
            'app': self.current_app,
            'title': self.current_window_title,
            'end_time': None,
            'duration': 0
        })
    
    def _end_programming_session(self) -> float:
        """
        结束当前编程会话
        
        Returns:
            会话持续时间（秒）
        """
        current_time = time.time()
        duration = 0.0
        
        # 如果有活跃的会话，结束它
        if self.programming_sessions and self.programming_sessions[-1]['end_time'] is None:
            session = self.programming_sessions[-1]
            session['end_time'] = current_time
            duration = current_time - session['start_time']
            session['duration'] = duration
            self.total_programming_time += duration
        
        return duration
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """
        获取当日统计数据
        
        Returns:
            包含统计信息的字典
        """
        # 如果有未结束的会话，先结束它
        if self.is_programming and self.programming_sessions and self.programming_sessions[-1]['end_time'] is None:
            self._end_programming_session()
            # 重新开始当前会话
            self._start_programming_session()
        
        # 计算会话统计信息
        app_times = {}
        for session in self.programming_sessions:
            if session['end_time'] is not None:
                app = session['app']
                duration = session['duration']
                app_times[app] = app_times.get(app, 0) + duration
        
        return {
            'total_time': self.total_programming_time,
            'total_hours': self.total_programming_time / 3600,
            'session_count': len(self.programming_sessions),
            'app_breakdown': app_times
        }
    
    def reset_daily_stats(self) -> None:
        """重置每日统计数据"""
        self.total_programming_time = 0
        self.programming_sessions = []
        # 如果当前正在编程，创建一个新会话
        if self.is_programming:
            self._start_programming_session()
        logger.info("每日统计数据已重置")
