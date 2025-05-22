#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodePet - 测试版本
"""

import os
import sys
import logging
import tkinter as tk
from PIL import Image, ImageTk

# 设置基本日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建简单事件系统
class SimpleEventSystem:
    def __init__(self):
        self.handlers = {}
    
    def register(self, event_name, handler):
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)
    
    def trigger(self, event_name, data=None):
        if data is None:
            data = {}
        if event_name in self.handlers:
            for handler in self.handlers[event_name]:
                handler(data)

# 简单配置管理器
class SimpleConfig:
    def __init__(self):
        self.settings = {
            'pet': {
                'name': '皮皮',
                'type': 'test'
            },
            'window': {
                'position_x': 100,
                'position_y': 100
            },
            'ui': {
                'animation': {
                    'fps': 24
                }
            }
        }
    
    def get_setting(self, key, default=None):
        parts = key.split('.')
        current = self.settings
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return default
        return current
    
    def set_setting(self, key, value):
        parts = key.split('.')
        current = self.settings
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

# 简单状态枚举类
class SimpleEnum:
    def __init__(self, value):
        self.value = value

# 简单宠物模型
class SimplePet:
    def __init__(self, name, pet_type):
        self.name = name
        self.pet_type = pet_type
        # 使用包含value属性的对象替代简单字符串
        self.state = SimpleEnum('idle')
        self.mood = SimpleEnum('normal')
        self.current_action = SimpleEnum('idle')
        
        # 添加动画相关属性
        self.animation_speed = 10.0  # 每秒帧数
        
        # 添加其他可能需要的属性
        self.energy = 100.0
        self.happiness = 80.0
        self.experience = 0.0
        self.level = 1
        
        # 统计数据
        self.stats = {
            "total_active_time": 0,
            "code_lines": 0,
            "achievements": [],
            "daily_sessions": {}
        }

# 简单宠物控制器
class SimplePetController:
    def __init__(self):
        self.pet = SimplePet('皮皮', 'test')
    
    # 添加一些可能需要的方法
    def get_pet(self):
        return self.pet
    
    def get_pet_type(self):
        return self.pet.pet_type
    
    def get_current_action(self):
        return self.pet.current_action.value
    
    def get_current_mood(self):
        return self.pet.mood.value

def main():
    """测试主函数"""
    try:
        logger.info("启动 CodePet 测试版本")
        
        # 创建简单事件系统
        event_system = SimpleEventSystem()
        
        # 创建简单配置
        config = SimpleConfig()
        
        # 创建简单宠物控制器
        pet_controller = SimplePetController()
        
        # 导入 MainWindow 类
        from ui.window import MainWindow
        
        # 创建主窗口
        window = MainWindow(pet_controller, event_system, config)
        
        # 运行窗口
        logger.info("CodePet 测试版本启动完成")
        window.run()
        
    except ImportError as e:
        logger.error(f"导入错误: {e}")
        
        # 如果导入失败，显示一个提示窗口
        root = tk.Tk()
        root.title("CodePet 错误")
        tk.Label(
            root, 
            text="运行失败，确保已创建所需的文件:\n" + 
                 "- ui/window.py\n" + 
                 "- ui/animator.py",
            padx=20, 
            pady=20
        ).pack()
        root.mainloop()
        
    except Exception as e:
        logger.error(f"程序错误: {e}", exc_info=True)
        return 1
    
    return 0

# 以下是原始导入，全部注释掉
"""
# 导入核心模块
#from core.activity.tracker import ActivityTracker
#from core.stats.logger import StatsLogger
#from core.pet.controller import PetController
#from core.events import EventSystem
#from core.scheduler.jobs import JobScheduler

# 导入界面相关模块
#from ui.window import MainWindow
#from ui.tray import SystemTray

# 导入配置
#from utils.system_utils import setup_environment, check_first_run
#from config.config_manager import ConfigManager
"""

if __name__ == "__main__":
    sys.exit(main())