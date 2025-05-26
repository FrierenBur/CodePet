import sys
import os
import time 
import logging # 确保导入 logging
from typing import Any 

# PyQt5 相关导入
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer # QTimer.singleShot 需要 QTimer
# 从同目录下的 animator.py 文件导入 Animator 类
from .animator import Animator

logger = logging.getLogger(__name__) # 获取 logger 实例

# --- 全局常量定义 ---
FIXED_WINDOW_WIDTH = 150
FIXED_WINDOW_HEIGHT = 150
DEFAULT_ANIMATION_SPEED_MS = 20
DEFAULT_ACTION_ANIMATION = "idle"

class PetWindow(QWidget):
    # ... (构造函数 __init__ 和其他大部分方法保持不变) ...
    def __init__(self, initial_pet_character_name, event_system: Any, parent=None): #
        super().__init__(parent) #

        self.event_system = event_system #

        self.script_dir = os.path.dirname(os.path.abspath(__file__)) #
        self.project_root = os.path.abspath(os.path.join(self.script_dir, '..')) #
        self.all_pets_base_path = os.path.join(self.project_root, 'assets', 'pets') #

        self.current_pet_character_name = None #
        self.animator = None #
        self.animation_timer = QTimer(self) #
        self.animation_timer.timeout.connect(self.update_animation) #

        self._init_window_properties() #
        self._init_ui_elements() #
        self.dragging = False #
        self.drag_position = QPoint() #
        self.setFixedSize(FIXED_WINDOW_WIDTH, FIXED_WINDOW_HEIGHT) #
        self.move(100, 100) #

        if self.event_system: #
            self.event_system.register('ui_play_animation', self.handle_play_animation_event) #
            logger.info("PetWindow: 已注册 'ui_play_animation' 事件监听器。") #
        else: #
            logger.warning("PetWindow 警告: EventSystem 未提供，无法监听来自 PetController 的动画播放事件。") #

        if not self.load_character(initial_pet_character_name): #
            self.pet_label.setText(f"无法加载角色:\n{initial_pet_character_name}") #
            self.pet_label.setAlignment(Qt.AlignCenter) #
            logger.error(f"错误: 初始宠物角色 '{initial_pet_character_name}' 加载失败。") # 使用 logger

    # === 修改 handle_play_animation_event 方法 ===
    def handle_play_animation_event(self, event_data: dict):
        """
        处理从 EventSystem 收到的 'ui_play_animation' 事件。
        此方法本身可能在非GUI线程中被调用（如果事件由非GUI线程发出）。
        因此，它将实际的处理工作调度到主GUI线程执行。
        """
        if not event_data or not isinstance(event_data, dict):
            logger.warning("PetWindow: 收到的 'ui_play_animation' 事件数据格式无效或为空。")
            return

        # 复制一份数据，以防原始字典在lambda延迟执行前被修改
        # 对于简单的字典结构，浅拷贝通常足够
        data_copy = event_data.copy()
        
        # 使用 QTimer.singleShot 将 _process_play_animation_event 的调用调度到主GUI线程
        QTimer.singleShot(0, lambda: self._process_play_animation_event(data_copy))
        # logger.debug(f"PetWindow: 已将 'ui_play_animation' 事件 (目标动作: {data_copy.get('action_name')}) 的处理调度到主线程。") # 这行日志可能太频繁

    def _process_play_animation_event(self, event_data: dict):
        """
        这个方法总是在主GUI线程中被调用 (通过 QTimer.singleShot 从 handle_play_animation_event 调度)。
        它负责安全地停止旧的动画定时器，并调用 play_animation 来启动新的动画。
        """
        
        character_name_from_event = event_data.get('character_name')
        action_name_from_event = event_data.get('action_name')
        print("这里是window......"+action_name_from_event)
        
        logger.info(f"PetWindow (_process_play_animation_event): 正在主线程处理播放指令 - 角色: {character_name_from_event}, 动作: {action_name_from_event}")

        if self.current_pet_character_name == character_name_from_event and action_name_from_event:
            # 现在可以安全地操作 self.animation_timer，因为它在主线程中
            if self.animation_timer.isActive():
                current_anim_name = self.animator._current_animation_name if self.animator and hasattr(self.animator, '_current_animation_name') else '未知'
                logger.debug(f"PetWindow (_process_play_animation_event): 停止当前活动的定时器 (原动作: '{current_anim_name}')，准备播放新动作: '{action_name_from_event}'.")
                self.animation_timer.stop() # 现在这个 stop() 调用是线程安全的
            
            self.play_animation(action_name_from_event) # 调用 play_animation，它也会在主线程
        
        elif not self.current_pet_character_name:
             logger.warning(f"PetWindow (_process_play_animation_event): 当前未加载任何角色，无法响应播放 '{action_name_from_event}' (目标角色 '{character_name_from_event}') 的指令。")
        elif character_name_from_event and self.current_pet_character_name != character_name_from_event:
            logger.info(f"PetWindow (_process_play_animation_event): 收到针对角色 '{character_name_from_event}' 的动画指令，但当前显示的角色是 '{self.current_pet_character_name}'。事件已忽略。")
        elif not action_name_from_event:
            logger.warning(f"PetWindow (_process_play_animation_event): 收到的 'ui_play_animation' 事件中缺少 'action_name'。")


    # play_animation, update_animation, load_character 等其他方法保持不变，
    # 因为它们内部对 QTimer 的操作现在会因为 play_animation 是在主线程被调用而变得安全。
    # _init_window_properties, _init_ui_elements, mousePressEvent (除了发出事件的部分), 
    # mouseMoveEvent, mouseReleaseEvent, close_application, contextMenuEvent 也基本不变。
    # 确保 mousePressEvent 中的 self.event_system.emit 也是可以的，因为emit本身不直接操作UI，
    # 而是它的处理器 handle_play_animation_event 现在能正确处理线程问题。

    def _init_window_properties(self): #
        """设置窗口的特殊属性：无边框、置顶、背景透明。"""
        self.setWindowFlags( #
            Qt.FramelessWindowHint |      # 设置窗口无边框 #
            Qt.WindowStaysOnTopHint |   # 设置窗口总是在其他窗口之上 #
            Qt.Tool                     # 提示窗口系统这是一个工具窗口 (可能影响任务栏显示等) #
        ) #
        self.setAttribute(Qt.WA_TranslucentBackground) # 设置窗口背景为透明 #


    def _init_ui_elements(self): #
        """
        初始化界面元素，主要是创建一个 QLabel 用于显示宠物动画。
        具体的 QPixmap (图片帧) 由 load_character 和 play_animation 方法来设置。
        """
        self.pet_label = QLabel(self)  # 创建 QLabel 对象，作为显示动画帧的“画布” #
        self.pet_label.setScaledContents(True) # 关键设置：允许 QLabel 缩放其内容 (QPixmap) 以填满自身区域 #
        
        # 使用 QVBoxLayout (垂直布局) 来管理 QLabel，确保 QLabel 能填满整个窗口
        layout = QVBoxLayout() #
        layout.addWidget(self.pet_label) # 将 QLabel 添加到布局中 #
        layout.setContentsMargins(0, 0, 0, 0) # 设置布局的边距为0，使 QLabel 紧贴窗口边缘 #
        self.setLayout(layout) # 将此布局应用到 PetWindow #


    def load_character(self, character_name): #
        """
        加载指定名称的宠物角色及其动画。
        这个方法会停止当前可能在播放的动画，然后为新角色创建一个全新的 Animator 实例。
        成功加载后会播放该角色的默认初始动作 (DEFAULT_ACTION_ANIMATION)。

        参数:
            character_name (str): 要加载的宠物角色的名称 (对应 assets/pets/ 下的文件夹名)。
        
        返回:
            bool: 如果角色和其默认动画成功加载则返回 True，否则返回 False。
        """
        logger.info(f"PetWindow: 尝试加载角色 '{character_name}'...") #
        
        # 构建特定角色动画资源的根目录路径
        specific_character_path = os.path.join(self.all_pets_base_path, character_name) #

        # 检查角色目录是否存在
        if not os.path.isdir(specific_character_path): #
            logger.error(f"错误: 角色 '{character_name}' 的目录未找到: {specific_character_path}") #
            # 如果角色目录不存在，停止当前可能在运行的动画定时器
            if self.animation_timer.isActive(): #
                self.animation_timer.stop() #
            # 在 QLabel 上显示错误提示
            self.pet_label.setText(f"角色 {character_name}\n未找到!") #
            self.pet_label.setAlignment(Qt.AlignCenter) #
            # 重置当前角色名和 Animator 实例
            self.current_pet_character_name = None #
            self.animator = None #
            return False # 加载失败 #

        # 如果定时器当前正在运行 (可能在播放上一个角色的动画)，先停止它
        # 因为我们将要更换 Animator 实例
        if self.animation_timer.isActive(): #
            self.animation_timer.stop() #

        # 更新当前加载的宠物角色名
        self.current_pet_character_name = character_name #
        # 为新加载的角色创建一个新的 Animator 实例
        # base_pet_path 指向这个特定角色的动画文件夹
        # initial_animation_name 让 Animator 尝试加载这个角色的默认动作
        self.animator = Animator( #
            base_pet_path=specific_character_path, #
            initial_animation_name=DEFAULT_ACTION_ANIMATION,  #
            animation_speed_ms=DEFAULT_ANIMATION_SPEED_MS #
        ) #

        # 检查新的 Animator 是否成功创建并且其内部已加载了有效的帧
        # (Animator 在 __init__ 中会尝试加载 initial_animation_name)
        if self.animator and self.animator._current_frames:  #
            logger.info(f"PetWindow: 角色 '{character_name}' 的 Animator 创建成功。") #
            # Animator 初始化时会尝试加载 initial_animation_name (即 DEFAULT_ACTION_ANIMATION)
            # animator._current_animation_name 应该是 Animator 成功设置的初始动作名
            # 如果 Animator 因故未能设置 _current_animation_name，则回退到 DEFAULT_ACTION_ANIMATION
            # self.play_animation(self.animator._current_animation_name or DEFAULT_ACTION_ANIMATION) # 这行被移到 __init__ 中通过事件触发
            # 为了在角色加载后立即显示些东西，而不是等事件，可以显示第一帧
            first_frame = self.animator.get_current_frame_pixmap()
            if not first_frame.isNull():
                self.pet_label.setPixmap(first_frame)
            else:
                self.pet_label.setText(f"{character_name}\n(等待指令)")
                self.pet_label.setAlignment(Qt.AlignCenter)
            return True # 角色和默认动画加载并播放成功 #
        else: #
            # Animator 创建失败或未能加载任何帧
            logger.error(f"错误: 为角色 '{character_name}' 创建 Animator 或加载默认动作 '{DEFAULT_ACTION_ANIMATION}' 失败。") #
            self.pet_label.setText(f"角色 {character_name}\n动画加载失败!") #
            self.pet_label.setAlignment(Qt.AlignCenter) #
            self.animator = None # Animator 无效，重置 #
            return False # 加载失败 #


    def play_animation(self, animation_name): #
        """
        命令当前加载的宠物角色播放指定的动作动画。

        参数:
            animation_name (str): 要播放的动作的名称 (对应角色动画文件夹下的子文件夹名)。
        """
        # 确保 Animator 实例存在
        if not self.animator: #
            logger.error(f"PetWindow 错误: Animator 未初始化，无法播放动作 '{animation_name}' (当前角色: {self.current_pet_character_name})。") #
            return #

        logger.info(f"PetWindow: 角色 '{self.current_pet_character_name}' 尝试播放动作 '{animation_name}'") #
        # 命令 Animator 切换到指定的动作序列
        if self.animator.set_current_animation(animation_name): #
            # 如果 Animator 成功切换了动作，并且新动作确实有帧
            if self.animator._current_frames: #
                # 获取新动作的第一帧以立即显示
                first_frame = self.animator.get_current_frame_pixmap() #
                if not first_frame.isNull(): # 确保第一帧有效 #
                    self.pet_label.setPixmap(first_frame) #
                    logger.debug(f"PetWindow.play_animation: 已设置 '{animation_name}' 的第一帧。 " #
                                 f"帧尺寸: {first_frame.size()}, 窗口可见: {self.isVisible()}, " #
                                 f"Label可见: {self.pet_label.isVisible()}, Label尺寸: {self.pet_label.size()}") #
                else: #
                    # 如果第一帧无效 (例如图片文件损坏或 Animator 内部问题)
                    self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(首帧错误)") #
                    self.pet_label.setAlignment(Qt.AlignCenter) #
                    if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器 #
                    return # 无法播放，提前退出 #

                # 获取当前动画的速度 (可能每个动作的速度不同，如果 Animator 支持的话)
                current_speed = self.animator.get_animation_speed() #
                # 如果定时器的当前间隔与新动画的速度不同，或者定时器未激活，则更新并启动/重启定时器
                if self.animation_timer.interval() != current_speed or not self.animation_timer.isActive(): #
                    self.animation_timer.setInterval(current_speed) # 设置定时器的新间隔 #
                    self.animation_timer.start() # 启动或重新启动定时器 #

                logger.info(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 已启动/切换，速度 {current_speed}ms/帧。") #
            else: #
                # Animator 成功设置了动作名，但该动作没有有效的帧
                logger.warning(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 没有帧，动画定时器停止。") #
                if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器 #
                self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(无帧)") #
                self.pet_label.setAlignment(Qt.AlignCenter) #
        else: #
            # Animator 未能成功设置 (切换到) 指定的动作 (例如，动作名不存在且无法按需加载)
            logger.warning(f"PetWindow: Animator 未能为角色 '{self.current_pet_character_name}' 设置动作 '{animation_name}'。") #
            if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器 #
            self.pet_label.setText(f"无法播放\n{self.current_pet_character_name}\n{animation_name}") #
            self.pet_label.setAlignment(Qt.AlignCenter) #


    def update_animation(self): #
        """
        此方法由 self.animation_timer 的 timeout 信号定期调用。
        负责从 Animator 获取下一帧并更新到 QLabel 上，从而形成动画。
        """
        # 确保 Animator 存在且当前有有效的动画帧在播放
        if self.animator and self.animator._current_frames: #
            current_action_name = self.animator._current_animation_name  #
            current_frame_idx = self.animator._current_frame_index    #
            next_pixmap = self.animator.next_frame() # 从 Animator 获取下一帧 #

            is_pixmap_null = next_pixmap.isNull() #
            pixmap_size = next_pixmap.size() if not is_pixmap_null else 'N/A' #
            logger.debug(f"PetWindow.update_animation: 动作='{current_action_name}', " #
                         f"原索引={current_frame_idx}, 新索引={self.animator._current_frame_index}, " #
                         f"下一帧IsNull={is_pixmap_null}, 下一帧尺寸={pixmap_size}, " #
                         f"定时器激活={self.animation_timer.isActive()}, 窗口可见={self.isVisible()}") #

            if not is_pixmap_null: # 确保获取到的帧是有效的 #
                self.pet_label.setPixmap(next_pixmap) # 更新 QLabel 显示的图片 #
            else: #
                logger.warning(f"PetWindow.update_animation: 警告 - 动作 '{current_action_name}' 的 next_frame() 返回了空 Pixmap。动画可能中断。") #
                if self.animation_timer.isActive(): #
                    self.animation_timer.stop() # 停止定时器避免持续错误 #
                self.pet_label.setText(f"{self.current_pet_character_name}\n{current_action_name}\n(动画帧错误)") #
                self.pet_label.setAlignment(Qt.AlignCenter) #


    def mousePressEvent(self, event): #
        """当鼠标在窗口上按下时调用。"""
        if event.button() == Qt.LeftButton: # 只响应鼠标左键 #
            if self.event_system: # 确保 event_system 已设置 #
                 logger.info("PetWindow: 检测到左键点击，发出 'pet_interaction' 事件。") #
                 # 发出事件，携带交互类型和当前角色信息
                 self.event_system.emit('pet_interaction', { #
                     'type': 'click', # 定义交互类型为 'click' #
                     'character_name': self.current_pet_character_name, # 告知是哪个角色被点击了 #
                     'timestamp': time.time() # （可选）事件发生的时间戳 #
                 }) #
            else: #
                logger.warning("PetWindow: 左键点击，但 EventSystem 未设置，无法发出交互事件。") #
            
            self.dragging = True # 进入拖动状态 #
            self.drag_position = event.globalPos() - self.pos() #
            event.accept() # 事件已被处理 #

    def mouseMoveEvent(self, event): #
        """当鼠标在窗口上按下并移动时调用。"""
        # 检查是否处于拖动状态 (self.dragging) 并且鼠标左键仍然被按住
        if self.dragging and event.buttons() & Qt.LeftButton: #
            # 移动窗口到新的位置：当前鼠标全局位置 - 之前记录的按下点偏移量
            self.move(event.globalPos() - self.drag_position) #
            event.accept() # 事件已被处理 #

    def mouseReleaseEvent(self, event): #
        """当鼠标在窗口上松开时调用。"""
        if event.button() == Qt.LeftButton: # 如果是左键松开 #
            self.dragging = False # 退出拖动状态 #
            event.accept() # 事件已被处理 #

    def close_application(self): #
        """安全地关闭整个应用程序。"""
        logger.info("正在关闭应用程序...") #
        # 检查动画定时器是否存在且正在运行，如果是，则先停止它
        if hasattr(self, 'animation_timer') and self.animation_timer.isActive(): #
            self.animation_timer.stop() #
        QApplication.instance().quit() # 请求 Qt 应用程序退出事件循环 #

    def contextMenuEvent(self, event): #
        """当在窗口上右键单击时调用，用于显示上下文菜单。"""
        context_menu = QMenu(self) # 创建一个 QMenu 对象 #
        
        # --- (未来功能占位) 可以在这里动态添加切换角色的菜单项 ---
        # # 假设有一个 get_available_characters 方法可以扫描 assets/pets 目录获取所有角色名
        # available_characters = self.get_available_characters() 
        # if available_characters:
        #     character_menu = context_menu.addMenu("切换角色") # 添加一个子菜单 "切换角色"
        #     for char_name in available_characters:
        #         action = QAction(char_name, self) # 为每个角色创建一个 QAction
        #         # 使用 lambda 来传递角色名参数给 self.load_character 方法
        #         # checked=False 是因为 QAction.triggered 信号有时会带一个布尔参数
        #         action.triggered.connect(lambda checked=False, name=char_name: self.load_character(name))
        #         character_menu.addAction(action) # 将动作添加到子菜单
        #     context_menu.addSeparator() # 添加一条分隔线

        # 创建一个 "退出宠物" 的动作
        exit_action = QAction("退出宠物", self) #
        exit_action.triggered.connect(self.close_application) # 连接到关闭应用程序的方法 #
        context_menu.addAction(exit_action) # 将退出动作添加到菜单 #

        context_menu.exec_(event.globalPos()) # 在鼠标光标的全局位置显示菜单 #

    # (未来可能需要，用于 contextMenuEvent 中的角色切换)
    # def get_available_characters(self):
    #     """扫描 self.all_pets_base_path 目录，返回所有子文件夹名作为可用角色列表。"""
    #     if not os.path.isdir(self.all_pets_base_path):
    #         return []
    #     return [d for d in os.listdir(self.all_pets_base_path) 
    #             if os.path.isdir(os.path.join(self.all_pets_base_path, d))]


# --- 主代码块，用于直接运行 window.py 进行测试 ---
if __name__ == '__main__':
    # 配置基础日志 (如果直接运行此文件，而不是通过 main.py)
    if not logging.getLogger().handlers: # 避免重复配置
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s')

    app = QApplication(sys.argv)

    # 为了独立测试 PetWindow 的事件响应，我们需要一个模拟的 EventSystem
    class MockEventSystem:
        def __init__(self):
            self._listeners = {}
            logger.info("MockEventSystem: 已创建，用于 PetWindow 单独测试。")
        def register(self, event_name, handler):
            if event_name not in self._listeners:
                self._listeners[event_name] = []
            self._listeners[event_name].append(handler)
            logger.info(f"MockEventSystem: 事件 '{event_name}' 已注册处理器 -> {handler.__name__ if hasattr(handler, '__name__') else handler}")
        def emit(self, event_name, data=None):
            logger.info(f"MockEventSystem: 正在发出事件 '{event_name}'，数据: {data}")
            if event_name in self._listeners:
                for handler in self._listeners[event_name]:
                    try:
                        handler(data or {})
                    except Exception as e:
                        logger.error(f"MockEventSystem: 调用处理器 {handler.__name__ if hasattr(handler, '__name__') else handler} 时发生错误: {e}", exc_info=True)
            else:
                logger.debug(f"MockEventSystem: 事件 '{event_name}' 没有注册的监听器。")
    
    mock_event_system = MockEventSystem()

    initial_character = "test" 
    # 确保 G:\CodePet\assets\pets\test\idle\ (或其他 DEFAULT_ACTION_ANIMATION) 路径和帧文件存在

    pet_window = PetWindow(
        initial_pet_character_name=initial_character,
        event_system=mock_event_system # 传递模拟的事件系统
    )
    pet_window.show()

    # 模拟 PetController 发出初始动画播放事件
    if pet_window.animator and pet_window.animator._current_frames:
        initial_action_data_for_ui = {
            'character_name': initial_character,
            'action_name': DEFAULT_ACTION_ANIMATION 
        }
        logger.info(f"__main__ (PetWindow测试): 手动模拟 PetController 发出初始播放事件: {initial_action_data_for_ui}")
        mock_event_system.emit('ui_play_animation', initial_action_data_for_ui)
    else:
        logger.error(f"__main__ (PetWindow测试): PetWindow 或 Animator 未能为角色 '{initial_character}' 正确初始化，无法模拟初始动画事件。")

    sys.exit(app.exec_())