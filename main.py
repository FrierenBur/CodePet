#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodePet - 你的编程桌宠助手
主应用程序入口。
"""

import sys
import os
import logging

# --- PyQt5 相关导入 ---
# from PyQt5.QtWidgets import QApplication # 将在 main_application 函数内导入
# from PyQt5.QtCore import QTimer # <<< 新增：这个 QTimer 的导入是关键

# --- 项目模块导入 ---
try:
    from config.config_manager import ConfigManager #
    from core.events import EventSystem #
    from core.pet.controller import PetController #
    from core.pet.model import ActionType # <<< 新增导入 ActionType，用于强制设置 IDLE
    from ui.window import PetWindow #
except ImportError as e:
    # ... (错误处理) ...
    print(f"发生严重导入错误，程序可能无法启动: {e}", file=sys.stderr) #
    try: #
        import tkinter as tk #
        from tkinter import messagebox #
        root = tk.Tk() #
        root.withdraw() # 隐藏主 tkinter 窗口 #
        messagebox.showerror("CodePet 启动错误", f"关键模块导入失败: {e}\n请确保项目结构完整且依赖已正确安装。") #
        root.destroy() #
    except ImportError: #
        print("无法加载 tkinter 来显示错误信息。", file=sys.stderr) #
    sys.exit(1) #

# --- 日志基础配置 ---
logging.basicConfig( #
    level=logging.INFO, #
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s', #
    datefmt='%Y-%m-%d %H:%M:%S' #
)
logger = logging.getLogger(__name__) #


def main_application(): #
    logger.info("CodePet 应用程序启动中...") #

    try: #
        from PyQt5.QtWidgets import QApplication #
        from PyQt5.QtCore import QTimer # <<< 确保 QTimer 在这里被导入
    except ImportError as e: #
        logger.critical(f"PyQt5 未安装或无法导入 (QApplication/QTimer): {e}", exc_info=True) #
        show_tkinter_error(f"PyQt5 未安装或无法导入。\n请确保已安装 PyQt5: pip install PyQt5\n错误详情: {e}") #
        return 1 #

    app_instance = None #
    pet_controller_instance = None #

    try: #
        app = QApplication(sys.argv) #
        app_instance = app #
        logger.info("QApplication 已初始化。") #

        config_mngr = ConfigManager() #
        if not config_mngr.settings:  #
            logger.critical("settings.yaml 加载失败或内容为空！程序无法继续。") #
            show_tkinter_error("settings.yaml 加载失败或内容为空！请检查或删除后重新运行以生成默认配置。") #
            return 1 #
        # model_config.json 的检查可以根据实际需要决定是否关键到需要退出
        if not config_mngr.model_config: #
            logger.warning("model_config.json 加载失败或内容为空。如果不需要模型相关功能，可以忽略。") #

        event_bus = EventSystem() #
        logger.info("事件系统已初始化。") #

        pet_controller = PetController(config=config_mngr, event_system=event_bus) #
        pet_controller_instance = pet_controller #
        logger.info(f"宠物控制器已为角色 '{pet_controller.pet.pet_type}' 初始化。") #

        initial_character_name = pet_controller.pet.pet_type #
        logger.info(f"从配置加载的初始宠物角色类型为: '{initial_character_name}'") #

        pet_window = PetWindow( #
            initial_pet_character_name=initial_character_name, #
            event_system=event_bus #
        ) #
        logger.info(f"宠物窗口 (PetWindow) 已为角色 '{initial_character_name}' 初始化。") #

        # === 这是关键的修改/确认点 ===
        # 设置并启动 PetController 的周期性更新定时器
        controller_update_timer = QTimer() 
        # 将 PetController 的更新方法连接到定时器的 timeout 信号
        controller_update_timer.timeout.connect(pet_controller.update_pet_stats_periodically)
        # 从配置读取调用 PetController 更新的频率，如果配置中没有，则默认为 200ms
        # 你需要在 settings.yaml 中定义 'pet.controller_update_call_interval_ms'
        periodic_update_call_interval_ms = config_mngr.get_setting('pet.controller_update_call_interval_ms', 200) 
        controller_update_timer.start(periodic_update_call_interval_ms) 
        logger.info(f"已启动 PetController 的周期性更新调用定时器 (每 {periodic_update_call_interval_ms}ms)。")
        # ==========================

        # 启动宠物的初始状态和动作
        # PetController 的 __init__ 可能已设置初始状态，但为确保动画播放，这里显式触发一次
        if pet_controller.pet.current_action: #
            logger.info(f"主程序：触发宠物控制器已设置（或在初始化时设定）的初始动作 '{pet_controller.pet.current_action.value}'。") #
            # 直接调用 PetController 的 set_action 来确保其内部逻辑（包括事件发出）被执行
            pet_controller.set_action(pet_controller.pet.current_action) # 不再直接 emit，让 controller 自己 emit
        else: #
            logger.warning("主程序：宠物控制器未设定初始动作，强制设置为 IDLE。") #
            pet_controller.set_action(ActionType.IDLE) #

        pet_window.show() #
        logger.info("宠物窗口已显示。") #

        logger.info("启动 Qt 事件循环...") #
        exit_code = app.exec_() #
        logger.info(f"Qt 事件循环已结束，退出码: {exit_code}") #
        
        # 在主事件循环结束后，显式调用 shutdown 方法
        if pet_controller_instance: #
            pet_controller_instance.shutdown() #
        
        sys.exit(exit_code) #

    except ImportError as e: #
        logger.critical(f"PyQt5 模块在运行时导入失败 (内部try): {e}", exc_info=True) #
        show_tkinter_error(f"运行时错误: 无法加载 PyQt5 组件。\n请确保 PyQt5 已正确安装。\n错误: {e}") #
        return 1 #
    except Exception as e: #
        logger.critical(f"应用程序发生未捕获的严重错误: {e}", exc_info=True) #
        show_tkinter_error(f"应用程序遇到严重错误并需要关闭。\n错误详情: {e}") #
        return 1 #
    finally: #
        # 如果 app 对象未成功创建，但 controller 创建了，确保 shutdown 仍被调用
        if pet_controller_instance and not app_instance: #
             pet_controller_instance.shutdown() #
        logger.info("CodePet 应用程序正在关闭。") #
    
    return 0 #

def show_tkinter_error(message: str) -> None: #
    # ... (这个函数保持不变) ...
    try: #
        import tkinter as tk #
        from tkinter import messagebox #
        if tk._default_root is None: # type: ignore #
            root = tk.Tk() #
            root.withdraw() # 隐藏主 Tkinter 窗口 #
            messagebox.showerror("CodePet 启动错误", message) #
            root.destroy() #
        else: # 如果已有 Tk 实例，直接使用 messagebox #
            messagebox.showerror("CodePet 启动错误", message) #
        logger.info("已通过 Tkinter 显示错误信息。") #
    except ImportError: #
        logger.error("Tkinter 未安装，无法显示图形化错误提示。错误信息将仅打印到控制台。") #
        print(f"发生严重错误: {message}", file=sys.stderr) #
    except Exception as e: #
        logger.error(f"显示 Tkinter 错误对话框时发生意外错误: {e}", exc_info=True) #
        print(f"显示错误对话框时出错: {message}", file=sys.stderr) #


if __name__ == "__main__": #
    main_application_exit_code = main_application() #
    if main_application_exit_code != 0: # # 如果 main_application 中途因错误返回了非0值
        sys.exit(main_application_exit_code) # 以该错误码退出
    # 如果 main_application 内部通过 sys.exit(app.exec_()) 正常结束，则这里不会执行
    # 或者如果它正常返回0，这里也可以省略 sys.exit(0) 因为脚本会自然结束