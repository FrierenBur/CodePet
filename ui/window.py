import sys
import os
import time 
import logging
import threading
from typing import Any 

# PyQt5 相关导入
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer

from typing import Optional, Dict, List, Any 
# 从同目录下的 animator.py 文件导入 Animator 类
from .animator import Animator #

logger = logging.getLogger(__name__)

# --- 全局常量定义 ---
FIXED_WINDOW_WIDTH = 150  # 宠物窗口的固定宽度
FIXED_WINDOW_HEIGHT = 150 # 宠物窗口的固定高度
# DEFAULT_ANIMATION_SPEED_MS = 100 # 这个全局默认现在主要作为 Animator 的后备默认速度
DEFAULT_ACTION_ANIMATION = "idle" # 约定每个宠物角色都应该有的默认/初始动作的动画名
# 可以为 Animator 提供一个最终的后备速度，如果它内部也无法确定速度
ANIMATOR_FALLBACK_DEFAULT_SPEED_MS = 100 

class PetWindow(QWidget):
    # PetWindow 类负责创建和管理桌宠的显示窗口、加载角色和播放动画。
    def __init__(self, initial_pet_character_name, event_system: Any, parent=None): # 构造函数，接收初始宠物角色名和事件系统实例
        super().__init__(parent) # 调用父类 QWidget 的构造函数

        self.event_system = event_system # 保存 EventSystem 实例，用于收发事件

        # --- 基础路径设置 ---
        self.script_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前脚本(window.py)的绝对路径的目录部分
        self.project_root = os.path.abspath(os.path.join(self.script_dir, '..')) # 从脚本目录向上跳一级到项目根目录 (codepet/)
        self.all_pets_base_path = os.path.join(self.project_root, 'assets', 'pets') # 指向存放所有宠物角色资源的顶级目录 (assets/pets/)

        # --- 成员变量初始化 ---
        self.current_pet_character_name = None # 当前加载的宠物角色名，会在 load_character 中设置
        self.animator: Optional[Animator] = None # Animator 类的实例，会在 load_character 中创建，用于管理当前角色的动画
        self.animation_timer = QTimer(self) # 创建一个 QTimer 对象，用于驱动动画的定时播放
        self.animation_timer.timeout.connect(self.update_animation) # 将定时器的 timeout 信号连接到 update_animation 方法

        # --- 初始化窗口视觉属性和拖动逻辑 ---
        self._init_window_properties() # 设置窗口的特殊样式 (无边框、置顶、透明)
        self._init_ui_elements()       # 初始化UI元素 (主要是用于显示动画的 QLabel)
        self.dragging = False          # 标记窗口当前是否被拖动
        self.drag_position = QPoint()  # 记录鼠标按下时相对于窗口左上角的偏移，用于平滑拖动
        self.setFixedSize(FIXED_WINDOW_WIDTH, FIXED_WINDOW_HEIGHT) # 设置窗口为固定大小
        self.move(100, 100) # 设置窗口的初始屏幕位置

        # --- 注册事件监听器 ---
        if self.event_system: #
            # 监听由 PetController 发出的 'ui_play_animation' 事件，并指定处理方法
            self.event_system.register('ui_play_animation', self.handle_play_animation_event) #
            logger.info("PetWindow: 已注册 'ui_play_animation' 事件监听器。") #
        else: #
            logger.warning("PetWindow 警告: EventSystem 未提供，无法监听来自 PetController 的动画播放事件。") #

        # --- 加载并显示初始宠物角色 ---
        # 调用 load_character 方法尝试加载指定的初始宠物角色
        if not self.load_character(initial_pet_character_name): #
            # 如果初始角色加载失败 (例如，角色文件夹不存在或动画资源有问题)
            # 在 QLabel 上显示错误信息
            self.pet_label.setText(f"无法加载角色:\n{initial_pet_character_name}") #
            self.pet_label.setAlignment(Qt.AlignCenter) # 文本居中显示
            logger.error(f"错误: 初始宠物角色 '{initial_pet_character_name}' 加载失败。") # 使用 logger
        # 初始动画的播放现在将由 PetController 通过发出 'ui_play_animation' 事件来触发


    def _init_window_properties(self): #
        """设置窗口的特殊属性：无边框、置顶、背景透明。"""
        self.setWindowFlags( #
            Qt.FramelessWindowHint |      # 设置窗口无边框
            Qt.WindowStaysOnTopHint |   # 设置窗口总是在其他窗口之上
            Qt.Tool                     # 提示窗口系统这是一个工具窗口
        ) #
        self.setAttribute(Qt.WA_TranslucentBackground) # 设置窗口背景为透明


    def _init_ui_elements(self): #
        """
        初始化界面元素，主要是创建一个 QLabel 用于显示宠物动画。
        """
        self.pet_label = QLabel(self)  # 创建 QLabel 对象，作为显示动画帧的“画布”
        self.pet_label.setScaledContents(True) # 关键设置：允许 QLabel 缩放其内容 (QPixmap) 以填满自身区域
        
        # 使用 QVBoxLayout (垂直布局) 来管理 QLabel，确保 QLabel 能填满整个窗口
        layout = QVBoxLayout() #
        layout.addWidget(self.pet_label) # 将 QLabel 添加到布局中
        layout.setContentsMargins(0, 0, 0, 0) # 设置布局的边距为0，使 QLabel 紧贴窗口边缘
        self.setLayout(layout) # 将此布局应用到 PetWindow


    def load_character(self, character_name: str) -> bool: #
        """
        加载指定名称的宠物角色及其动画。
        会重新创建 Animator 实例。
        成功加载角色后，会显示该角色默认动作的第一帧，等待 PetController 的播放指令。
        """
        logger.info(f"PetWindow: 尝试加载角色 '{character_name}'...") #
        specific_character_path = os.path.join(self.all_pets_base_path, character_name) #

        if not os.path.isdir(specific_character_path): #
            logger.error(f"错误: 角色 '{character_name}' 的目录未找到: {specific_character_path}") #
            if self.animation_timer.isActive(): self.animation_timer.stop() #
            self.pet_label.setText(f"角色 {character_name}\n未找到!") #
            self.pet_label.setAlignment(Qt.AlignCenter) #
            self.current_pet_character_name = None #
            self.animator = None #
            return False #

        if self.animation_timer.isActive(): self.animation_timer.stop() #

        self.current_pet_character_name = character_name #
        
        # 创建 Animator 时，传递一个后备的默认速度
        self.animator = Animator( #
            base_pet_path=specific_character_path, #
            initial_animation_name=DEFAULT_ACTION_ANIMATION,  #
            default_speed_ms=ANIMATOR_FALLBACK_DEFAULT_SPEED_MS # <<< 使用后备速度
        ) 

        if self.animator and self.animator._current_frames:  #
            logger.info(f"PetWindow: 角色 '{character_name}' 的 Animator 创建成功。") #
            # 显示 Animator 加载的初始动作的第一帧，等待 Controller 的播放指令
            first_frame = self.animator.get_current_frame_pixmap() #
            if not first_frame.isNull(): #
                self.pet_label.setPixmap(first_frame) #
            else: #
                self.pet_label.setText(f"{character_name}\n(等待指令)") #
                self.pet_label.setAlignment(Qt.AlignCenter) #
            return True #
        else: #
            logger.error(f"错误: 为角色 '{character_name}' 创建 Animator 或加载默认动作 '{DEFAULT_ACTION_ANIMATION}' 失败。") #
            self.pet_label.setText(f"角色 {character_name}\n动画加载失败!") #
            self.pet_label.setAlignment(Qt.AlignCenter) #
            self.animator = None #
            return False #

    def handle_play_animation_event(self, event_data: dict): #
        """
        处理从 EventSystem 收到的 'ui_play_animation' 事件。
        此方法本身可能在非GUI线程中被调用（如果事件由非GUI线程发出）。
        因此，它将实际的处理工作调度到主GUI线程执行。
        """
        logger.info(f"PetWindow.handle_play_animation_event: 事件已接收 (线程: {threading.current_thread().name if 'threading' in sys.modules else 'N/A'}), 数据: {event_data}") # 加上线程信息
        
        if not event_data or not isinstance(event_data, dict): #
            logger.warning("PetWindow: 收到的 'ui_play_animation' 事件数据格式无效或为空。") #
            return #

        data_copy = event_data.copy() #
        QTimer.singleShot(0, lambda d=data_copy: self._process_play_animation_event(d)) # 使用 lambda 正确捕获变量

    def _process_play_animation_event(self, event_data: dict): #
        """
        这个方法总是在主GUI线程中被调用 (通过 QTimer.singleShot 从 handle_play_animation_event 调度)。
        它负责安全地停止旧的动画定时器，并调用 play_animation 来启动新的动画。
        """
        character_name_from_event = event_data.get('character_name') #
        action_name_from_event = event_data.get('action_name') #
        
        # 加上线程信息，确认是在主线程
        logger.info(f"PetWindow (_process_play_animation_event): 正在主线程 (当前线程: {threading.current_thread().name if 'threading' in sys.modules else 'N/A'}) 处理播放指令 - 角色: {character_name_from_event}, 动作: {action_name_from_event}")

        if self.current_pet_character_name == character_name_from_event and action_name_from_event: #
            if self.animation_timer.isActive(): #
                current_anim_name = self.animator._current_animation_name if self.animator and hasattr(self.animator, '_current_animation_name') else '未知' #
                logger.debug(f"PetWindow (_process_play_animation_event): 停止当前活动的定时器 (原动作: '{current_anim_name}')，准备播放新动作: '{action_name_from_event}'.") #
                self.animation_timer.stop() # 现在这个 stop() 调用是线程安全的 #
            
            self.play_animation(action_name_from_event) # 调用 play_animation，它也会在主线程 #
        
        elif not self.current_pet_character_name: #
             logger.warning(f"PetWindow (_process_play_animation_event): 当前未加载任何角色，无法响应播放 '{action_name_from_event}' (目标角色 '{character_name_from_event}') 的指令。") #
        elif character_name_from_event and self.current_pet_character_name != character_name_from_event: #
            logger.info(f"PetWindow (_process_play_animation_event): 收到针对角色 '{character_name_from_event}' 的动画指令，但当前显示的角色是 '{self.current_pet_character_name}'。事件已忽略。") #
        elif not action_name_from_event: #
            logger.warning(f"PetWindow (_process_play_animation_event): 收到的 'ui_play_animation' 事件中缺少 'action_name'。") #

    def play_animation(self, animation_name: str): #
        """命令当前加载的宠物角色播放指定的动作动画。"""
        if not self.animator: #
            logger.error(f"PetWindow 错误: Animator 未初始化，无法播放动作 '{animation_name}' (当前角色: {self.current_pet_character_name})。") #
            return #

        logger.info(f"PetWindow: 角色 '{self.current_pet_character_name}' 尝试播放动作 '{animation_name}'") #
        if self.animator.set_current_animation(animation_name): #
            if self.animator._current_frames: #
                first_frame = self.animator.get_current_frame_pixmap() #
                if not first_frame.isNull(): #
                    self.pet_label.setPixmap(first_frame) #
                    logger.debug(f"PetWindow.play_animation: 已设置 '{animation_name}' 的第一帧。 " #
                                 f"帧尺寸: {first_frame.size()}, 窗口可见: {self.isVisible()}, " #
                                 f"Label可见: {self.pet_label.isVisible()}, Label尺寸: {self.pet_label.size()}") #
                else: #
                    self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(首帧错误)") #
                    self.pet_label.setAlignment(Qt.AlignCenter) #
                    if self.animation_timer.isActive(): self.animation_timer.stop() #
                    return #

                # === 关键修改：从 Animator 获取当前动作的专属速度 ===
                current_speed = self.animator.get_animation_speed() #
                # ==============================================
                
                if self.animation_timer.interval() != current_speed or not self.animation_timer.isActive(): #
                    self.animation_timer.setInterval(current_speed) # <<< 使用获取到的专属速度 #
                    self.animation_timer.start() #
                
                logger.info(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 已启动/切换，速度 {current_speed}ms/帧。") # <<< 更新日志中的速度
            else: #
                logger.warning(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 没有帧，动画定时器停止。") #
                if self.animation_timer.isActive(): self.animation_timer.stop() #
                self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(无帧)") #
                self.pet_label.setAlignment(Qt.AlignCenter) #
        else: #
            logger.warning(f"PetWindow: Animator 未能为角色 '{self.current_pet_character_name}' 设置动作 '{animation_name}'。") #
            if self.animation_timer.isActive(): self.animation_timer.stop() #
            self.pet_label.setText(f"无法播放\n{self.current_pet_character_name}\n{animation_name}") #
            self.pet_label.setAlignment(Qt.AlignCenter) #


    def update_animation(self): #
        """由 QTimer 定期调用，用于更新动画的下一帧。"""
        if self.animator and self.animator._current_frames: #
            current_action_name = self.animator.get_current_animation_name() # 使用新方法获取名字
            current_frame_idx = self.animator._current_frame_index    
            next_pixmap = self.animator.next_frame() #
            
            is_pixmap_null = next_pixmap.isNull() #
            pixmap_size = next_pixmap.size() if not is_pixmap_null else 'N/A' #
            logger.debug(f"PetWindow.update_animation: 动作='{current_action_name}', " #
                         f"原索引={current_frame_idx}, 新索引={self.animator._current_frame_index}, " #
                         f"下一帧IsNull={is_pixmap_null}, 下一帧尺寸={pixmap_size}, " #
                         f"定时器激活={self.animation_timer.isActive()}, 窗口可见={self.isVisible()}") #

            if not is_pixmap_null: #
                self.pet_label.setPixmap(next_pixmap) #
            else: #
                logger.warning(f"PetWindow.update_animation: 警告 - 动作 '{current_action_name}' 的 next_frame() 返回了空 Pixmap。动画可能中断。") #
                if self.animation_timer.isActive(): #
                    self.animation_timer.stop() #
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
        if self.dragging and event.buttons() & Qt.LeftButton: #
            self.move(event.globalPos() - self.drag_position) #
            event.accept() #

    def mouseReleaseEvent(self, event): #
        """当鼠标在窗口上松开时调用。"""
        if event.button() == Qt.LeftButton: # 如果是左键松开 #
            self.dragging = False # 退出拖动状态 #
            event.accept() #

    def close_application(self): #
        """安全地关闭整个应用程序。"""
        logger.info("正在关闭应用程序...") #
        if hasattr(self, 'animation_timer') and self.animation_timer.isActive(): #
            self.animation_timer.stop() #
        QApplication.instance().quit() #

    def contextMenuEvent(self, event): #
        """当在窗口上右键单击时调用，用于显示上下文菜单。"""
        context_menu = QMenu(self) #
        exit_action = QAction("退出宠物", self) #
        exit_action.triggered.connect(self.close_application) #
        context_menu.addAction(exit_action) #
        context_menu.exec_(event.globalPos()) #


# --- 主代码块，用于直接运行 window.py 进行测试 ---
if __name__ == '__main__':
    # 配置基础日志 (如果直接运行此文件，而不是通过 main.py)
    if not logging.getLogger().hasHandlers(): # 检查是否已经配置过 logger，避免重复
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s')

    app = QApplication(sys.argv)

    class MockEventSystem: # 模拟的事件系统
        def __init__(self): #
            self._listeners = {} #
            logger.info("MockEventSystem: 已创建，用于 PetWindow 单独测试。") #
        def register(self, event_name, handler): #
            if event_name not in self._listeners: #
                self._listeners[event_name] = [] #
            self._listeners[event_name].append(handler) #
            logger.info(f"MockEventSystem: 事件 '{event_name}' 已注册处理器 -> {handler.__name__ if hasattr(handler, '__name__') else handler}") #
        def emit(self, event_name, data=None): #
            logger.info(f"MockEventSystem: 正在发出事件 '{event_name}'，数据: {data}") #
            if event_name in self._listeners: #
                for handler in self._listeners[event_name]: #
                    try: #
                        handler(data or {}) #
                    except Exception as e: #
                        logger.error(f"MockEventSystem: 调用处理器 {handler.__name__ if hasattr(handler, '__name__') else handler} 时发生错误: {e}", exc_info=True) #
            else: #
                logger.debug(f"MockEventSystem: 事件 '{event_name}' 没有注册的监听器。") #
    
    mock_event_system = MockEventSystem() #

    initial_character = "test"  #
    
    pet_window = PetWindow( #
        initial_pet_character_name=initial_character, #
        event_system=mock_event_system # 传递模拟的事件系统 #
    ) #
    pet_window.show() #

    if pet_window.animator and pet_window.animator._current_frames: #
        initial_action_data_for_ui = { #
            'character_name': initial_character, #
            'action_name': DEFAULT_ACTION_ANIMATION  #
        } #
        logger.info(f"__main__ (PetWindow测试): 手动模拟 PetController 发出初始播放事件: {initial_action_data_for_ui}") #
        mock_event_system.emit('ui_play_animation', initial_action_data_for_ui) #
    else: #
        logger.error(f"__main__ (PetWindow测试): PetWindow 或 Animator 未能为角色 '{initial_character}' 正确初始化，无法模拟初始动画事件。") #

    sys.exit(app.exec_()) #