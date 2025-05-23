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
# 确保在创建任何 QApplication 实例之前，sys.argv 是可用的
# from PyQt5.QtWidgets import QApplication # 将在 main_application 函数内导入，以处理可能的导入错误

# --- 项目模块导入 ---
# 为了确保模块能被正确找到，特别是当直接运行 main.py 时，
# 并且 main.py 在项目根目录下，而 core, ui, config 是其子目录。
# Python 通常会自动将脚本所在的目录添加到 sys.path。
# 如果你的项目根目录不是 Python 解释器当前的工作目录，
# 或者你想从其他地方运行，可能需要更复杂的路径管理。
# 假设我们从项目根目录 (G:\CodePet\) 运行 `python main.py`

try:
    from config.config_manager import ConfigManager #
    from core.events import EventSystem #
    from core.pet.controller import PetController #
    from ui.window import PetWindow #
    # Qt 应用类将在函数内导入，以便在导入失败时能用 tkinter 显示错误
except ImportError as e:
    # 如果基础模块导入失败，尝试用 tkinter 显示错误信息并退出
    # 这是因为如果 QApplication 都无法导入，基于 PyQt 的错误处理也无法工作
    print(f"发生严重导入错误，程序可能无法启动: {e}", file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw() # 隐藏主 tkinter 窗口
        messagebox.showerror("CodePet 启动错误", f"关键模块导入失败: {e}\n请确保项目结构完整且依赖已正确安装。")
        root.destroy()
    except ImportError:
        print("无法加载 tkinter 来显示错误信息。", file=sys.stderr)
    sys.exit(1)


# --- 日志基础配置 ---
# 可以根据需要调整日志级别和格式
logging.basicConfig(
    level=logging.INFO, # INFO 级别可以看到更多信息，DEBUG 级别最详细
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 为特定模块设置不同日志级别 (可选)
# logging.getLogger("ui.animator").setLevel(logging.INFO)
# logging.getLogger("core.pet.controller").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__) # 获取 main.py 的日志记录器


def main_application():
    """
    应用程序的主函数，负责初始化和运行所有组件。
    """
    logger.info("CodePet 应用程序启动中...")

    # 确保 PyQt5.QtWidgets.QApplication 只在需要时导入，以便在导入失败时有回退机制
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError as e:
        logger.critical(f"PyQt5 未安装或无法导入 (QApplication): {e}", exc_info=True)
        show_tkinter_error(f"PyQt5 未安装或无法导入。\n请确保已安装 PyQt5: pip install PyQt5\n错误详情: {e}")
        return 1 # 返回错误码

    try:
        # 1. 初始化 QApplication (任何 PyQt 控件创建前都必须有它)
        #    这一步如果失败，通常意味着 PyQt 环境有问题。
        app = QApplication(sys.argv)
        logger.info("QApplication 已初始化。")

        # 2. 初始化配置管理器
        #    ConfigManager 会自动加载 config/settings.yaml 和 config/model_config.json
        #    它的路径是相对于 config_manager.py 文件位置计算的。
        config_mngr = ConfigManager() #
        if not config_mngr.settings or not config_mngr.model_config: # 检查配置是否成功加载
            logger.critical("配置文件加载失败，请检查 config 目录下的 settings.yaml 和 model_config.json 文件。")
            # 即使配置加载失败，ConfigManager 内部的 create_default_config 可能会尝试创建默认配置
            # 但如果关键配置缺失，程序可能无法正常运行，这里可以选择是否退出
            if not config_mngr.settings: # 特别是 settings.yaml 比较关键
                 show_tkinter_error("settings.yaml 加载失败或内容为空！程序无法确定宠物类型等关键信息。请检查或删除后重新运行以生成默认配置。")
                 return 1


        # 3. 初始化事件系统
        event_bus = EventSystem() #
        logger.info("事件系统已初始化。")

        # 4. 初始化宠物控制器
        #    PetController 接收配置和事件系统作为参数
        pet_controller = PetController(config=config_mngr, event_system=event_bus) #
        logger.info(f"宠物控制器已为角色 '{pet_controller.pet.pet_type}' 初始化。")

        # 5. 获取初始宠物角色名称 (从配置中读取 pet.type)
        #    PetController 内部的 self.pet.pet_type 就是从配置加载的，我们可以直接用它
        initial_character_name = pet_controller.pet.pet_type # 例如 "test", "cat_alpha" 等
        logger.info(f"从配置加载的初始宠物角色类型为: '{initial_character_name}'")

        # 6. 初始化宠物窗口 (PetWindow)
        #    将初始角色名和事件系统实例传递给 PetWindow
        pet_window = PetWindow(
            initial_pet_character_name=initial_character_name,
            event_system=event_bus #
        )
        logger.info(f"宠物窗口 (PetWindow) 已为角色 '{initial_character_name}' 初始化。")

        # 7. 启动宠物的核心逻辑/初始状态
        #    我们期望 PetController 在其初始化或一个明确的 start 方法中设置初始状态，
        #    并通过事件系统触发 PetWindow 播放初始动画。
        #    例如，可以在 PetController 中添加一个 start_behavior() 方法：
        #    if hasattr(pet_controller, 'start_behavior'):
        #        pet_controller.start_behavior()
        #    或者，如果 PetController 的 __init__ 已经通过 set_state -> set_action 发出了事件，
        #    并且 PetWindow 的 __init__ 已经注册了监听器，那么初始动画应该已经被触发了。
        #    我们之前在 PetWindow 的 __main__ 测试中模拟了 controller 发出初始事件。
        #    现在 controller 真的存在了，它的 __init__ 调用 set_state(StateType.IDLE)
        #    set_state 又调用 set_action(ActionType.IDLE), set_action 会 emit('ui_play_animation')
        #    PetWindow 在 __init__ 中注册了对 'ui_play_animation' 的监听，所以应该能自动播放。
        #    我们在这里可以主动让 PetController 进入其定义的初始状态（如果其 __init__ 没有自动做这件事）
        if hasattr(pet_controller, 'set_initial_state_and_action'): # 假设 PetController 有这样一个方法
            pet_controller.set_initial_state_and_action()
        elif pet_controller.pet.current_action: # 或者直接触发当前已设定的动作（可能在 PetController.__init__ 中设定）
            # 这个逻辑确保即使 controller 内部 __init__ 设置了动作但事件系统当时未完全连接，这里也能触发一次
            logger.info(f"主程序：尝试触发宠物控制器已设置的初始动作 '{pet_controller.pet.current_action.value}'。")
            event_bus.emit('ui_play_animation', {
                'character_name': pet_controller.pet.pet_type,
                'action_name': pet_controller.pet.current_action.value,
                'mood_name': pet_controller.pet.mood.value
            })
        else: # 保险起见，如果 controller 没有初始动作，强制一个 IDLE
            logger.warning("主程序：宠物控制器未设定初始动作，强制设置为 IDLE。")
            pet_controller.set_action(ActionType.IDLE)


        # 8. 显示宠物窗口
        pet_window.show()
        logger.info("宠物窗口已显示。")

        # 9. 启动 Qt 应用程序的事件循环
        logger.info("启动 Qt 事件循环...")
        exit_code = app.exec_()
        logger.info(f"Qt 事件循环已结束，退出码: {exit_code}")
        sys.exit(exit_code)

    except ImportError as e: # 捕获在 main_application 内部可能发生的 PyQt5 导入错误
        logger.critical(f"PyQt5 模块在运行时导入失败: {e}", exc_info=True)
        show_tkinter_error(f"运行时错误: 无法加载 PyQt5 组件。\n请确保 PyQt5 已正确安装。\n错误: {e}")
        return 1
    except Exception as e:
        logger.critical(f"应用程序发生未捕获的严重错误: {e}", exc_info=True)
        # 尝试用 tkinter 显示错误，如果 QApplication 可能已经崩溃
        show_tkinter_error(f"应用程序遇到严重错误并需要关闭。\n错误详情: {e}")
        return 1 # 返回错误码
    
    return 0 # 正常退出

def show_tkinter_error(message: str) -> None:
    """
    使用 Tkinter 显示一个错误消息对话框，作为 PyQt5 无法加载时的备用方案。
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        # 检查是否已有 Tk 实例在运行 (例如由其他导入引起)
        if tk._default_root is None: # type: ignore
            root = tk.Tk()
            root.withdraw() # 隐藏主 Tkinter 窗口
            messagebox.showerror("CodePet 启动错误", message)
            root.destroy()
        else: # 如果已有 Tk 实例，直接使用 messagebox
            messagebox.showerror("CodePet 启动错误", message)
        logger.info("已通过 Tkinter 显示错误信息。")
    except ImportError:
        # 如果连 Tkinter 也无法导入，则只能在控制台打印错误
        logger.error("Tkinter 未安装，无法显示图形化错误提示。错误信息将仅打印到控制台。")
        print(f"发生严重错误: {message}", file=sys.stderr)
    except Exception as e:
        logger.error(f"显示 Tkinter 错误对话框时发生意外错误: {e}", exc_info=True)
        print(f"显示错误对话框时出错: {message}", file=sys.stderr)


if __name__ == "__main__":
    # 确保从项目根目录运行此脚本，以便相对导入能正常工作，
    # 或者确保 core, ui, config 等目录在 PYTHONPATH 中。
    # 例如，在 G:\CodePet\ 目录下执行 `python main.py`
    main_application_exit_code = main_application()
    # 如果 main_application 返回了非零退出码，也应该传递给 sys.exit
    # sys.exit(main_application_exit_code if main_application_exit_code is not None else 0)
    # main_application 内部已经调用了 sys.exit()，所以这里不需要再次调用。
    # 如果 main_application 正常返回0，表示已通过 sys.exit(app.exec_()) 退出。
    # 如果 main_application 因异常返回1，表示也已通过 sys.exit(1) 或其他方式处理退出。
    # 因此，这里可以直接结束。
    if main_application_exit_code != 0:
        logger.info(f"应用程序以错误码 {main_application_exit_code} 结束。")