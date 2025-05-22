import sys
import os
# PyQt5 相关导入
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer
# 从同目录下的 animator.py 文件导入 Animator 类
from .animator import Animator

# --- 全局常量定义 ---
FIXED_WINDOW_WIDTH = 150  # 宠物窗口的固定宽度
FIXED_WINDOW_HEIGHT = 150 # 宠物窗口的固定高度
DEFAULT_ANIMATION_SPEED_MS = 100  # 默认的动画播放速度 (毫秒/帧)
DEFAULT_ACTION_ANIMATION = "idle" # 约定每个宠物角色都应该有的默认/初始动作的动画名 (例如 "idle")

class PetWindow(QWidget):
    # PetWindow 类负责创建和管理桌宠的显示窗口、加载角色和播放动画。
    def __init__(self, initial_pet_character_name, parent=None): # 构造函数，接收初始宠物角色名
        super().__init__(parent) # 调用父类 QWidget 的构造函数

        # --- 基础路径设置 ---
        self.script_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前脚本(window.py)的绝对路径的目录部分
        self.project_root = os.path.abspath(os.path.join(self.script_dir, '..')) # 从脚本目录向上跳一级到项目根目录 (codepet/)
        self.all_pets_base_path = os.path.join(self.project_root, 'assets', 'pets') # 指向存放所有宠物角色资源的顶级目录 (assets/pets/)

        # --- 成员变量初始化 ---
        self.current_pet_character_name = None # 当前加载的宠物角色名，会在 load_character 中设置
        self.animator = None # Animator 类的实例，会在 load_character 中创建，用于管理当前角色的动画
        self.animation_timer = QTimer(self) # 创建一个 QTimer 对象，用于驱动动画的定时播放
        self.animation_timer.timeout.connect(self.update_animation) # 将定时器的 timeout 信号连接到 update_animation 方法

        # --- 初始化窗口视觉属性和拖动逻辑 ---
        self._init_window_properties() # 设置窗口的特殊样式 (无边框、置顶、透明)
        self._init_ui_elements()       # 初始化UI元素 (主要是用于显示动画的 QLabel)
        self.dragging = False          # 标记窗口当前是否被拖动
        self.drag_position = QPoint()  # 记录鼠标按下时相对于窗口左上角的偏移，用于平滑拖动
        self.setFixedSize(FIXED_WINDOW_WIDTH, FIXED_WINDOW_HEIGHT) # 设置窗口为固定大小
        self.move(100, 100) # 设置窗口的初始屏幕位置

        # --- 加载并显示初始宠物角色 ---
        # 调用 load_character 方法尝试加载指定的初始宠物角色
        if not self.load_character(initial_pet_character_name):
            # 如果初始角色加载失败 (例如，角色文件夹不存在或动画资源有问题)
            # 在 QLabel 上显示错误信息
            self.pet_label.setText(f"无法加载角色:\n{initial_pet_character_name}")
            self.pet_label.setAlignment(Qt.AlignCenter) # 文本居中显示
            print(f"错误: 初始宠物角色 '{initial_pet_character_name}' 加载失败。")


    def _init_window_properties(self):
        """设置窗口的特殊属性：无边框、置顶、背景透明。"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |      # 设置窗口无边框
            Qt.WindowStaysOnTopHint |   # 设置窗口总是在其他窗口之上
            Qt.Tool                     # 提示窗口系统这是一个工具窗口 (可能影响任务栏显示等)
        )
        self.setAttribute(Qt.WA_TranslucentBackground) # 设置窗口背景为透明


    def _init_ui_elements(self):
        """
        初始化界面元素，主要是创建一个 QLabel 用于显示宠物动画。
        具体的 QPixmap (图片帧) 由 load_character 和 play_animation 方法来设置。
        """
        self.pet_label = QLabel(self)  # 创建 QLabel 对象，作为显示动画帧的“画布”
        self.pet_label.setScaledContents(True) # 关键设置：允许 QLabel 缩放其内容 (QPixmap) 以填满自身区域
        
        # 使用 QVBoxLayout (垂直布局) 来管理 QLabel，确保 QLabel 能填满整个窗口
        layout = QVBoxLayout()
        layout.addWidget(self.pet_label) # 将 QLabel 添加到布局中
        layout.setContentsMargins(0, 0, 0, 0) # 设置布局的边距为0，使 QLabel 紧贴窗口边缘
        self.setLayout(layout) # 将此布局应用到 PetWindow


    def load_character(self, character_name):
        """
        加载指定名称的宠物角色及其动画。
        这个方法会停止当前可能在播放的动画，然后为新角色创建一个全新的 Animator 实例。
        成功加载后会播放该角色的默认初始动作 (DEFAULT_ACTION_ANIMATION)。

        参数:
            character_name (str): 要加载的宠物角色的名称 (对应 assets/pets/ 下的文件夹名)。
        
        返回:
            bool: 如果角色和其默认动画成功加载则返回 True，否则返回 False。
        """
        print(f"PetWindow: 尝试加载角色 '{character_name}'...")
        
        # 构建特定角色动画资源的根目录路径
        specific_character_path = os.path.join(self.all_pets_base_path, character_name)

        # 检查角色目录是否存在
        if not os.path.isdir(specific_character_path):
            print(f"错误: 角色 '{character_name}' 的目录未找到: {specific_character_path}")
            # 如果角色目录不存在，停止当前可能在运行的动画定时器
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            # 在 QLabel 上显示错误提示
            self.pet_label.setText(f"角色 {character_name}\n未找到!")
            self.pet_label.setAlignment(Qt.AlignCenter)
            # 重置当前角色名和 Animator 实例
            self.current_pet_character_name = None
            self.animator = None
            return False # 加载失败

        # 如果定时器当前正在运行 (可能在播放上一个角色的动画)，先停止它
        # 因为我们将要更换 Animator 实例
        if self.animation_timer.isActive():
            self.animation_timer.stop()

        # 更新当前加载的宠物角色名
        self.current_pet_character_name = character_name
        # 为新加载的角色创建一个新的 Animator 实例
        # base_pet_path 指向这个特定角色的动画文件夹
        # initial_animation_name 让 Animator 尝试加载这个角色的默认动作
        self.animator = Animator(
            base_pet_path=specific_character_path,
            initial_animation_name=DEFAULT_ACTION_ANIMATION, 
            animation_speed_ms=DEFAULT_ANIMATION_SPEED_MS
        )

        # 检查新的 Animator 是否成功创建并且其内部已加载了有效的帧
        # (Animator 在 __init__ 中会尝试加载 initial_animation_name)
        if self.animator and self.animator._current_frames: 
            print(f"PetWindow: 角色 '{character_name}' 的 Animator 创建成功。")
            # Animator 初始化时会尝试加载 initial_animation_name (即 DEFAULT_ACTION_ANIMATION)
            # animator._current_animation_name 应该是 Animator 成功设置的初始动作名
            # 如果 Animator 因故未能设置 _current_animation_name，则回退到 DEFAULT_ACTION_ANIMATION
            self.play_animation(self.animator._current_animation_name or DEFAULT_ACTION_ANIMATION)
            return True # 角色和默认动画加载并播放成功
        else:
            # Animator 创建失败或未能加载任何帧
            print(f"错误: 为角色 '{character_name}' 创建 Animator 或加载默认动作 '{DEFAULT_ACTION_ANIMATION}' 失败。")
            self.pet_label.setText(f"角色 {character_name}\n动画加载失败!")
            self.pet_label.setAlignment(Qt.AlignCenter)
            self.animator = None # Animator 无效，重置
            return False # 加载失败


    def play_animation(self, animation_name):
        """
        命令当前加载的宠物角色播放指定的动作动画。

        参数:
            animation_name (str): 要播放的动作的名称 (对应角色动画文件夹下的子文件夹名)。
        """
        # 确保 Animator 实例存在
        if not self.animator:
            print(f"PetWindow 错误: Animator 未初始化，无法播放动作 '{animation_name}' (当前角色: {self.current_pet_character_name})。")
            return

        print(f"PetWindow: 角色 '{self.current_pet_character_name}' 接收指令播放动作 '{animation_name}'")
        # 命令 Animator 切换到指定的动作序列
        if self.animator.set_current_animation(animation_name):
            # 如果 Animator 成功切换了动作，并且新动作确实有帧
            if self.animator._current_frames:
                # 获取新动作的第一帧以立即显示
                first_frame = self.animator.get_current_frame_pixmap()
                if not first_frame.isNull(): # 确保第一帧有效
                    self.pet_label.setPixmap(first_frame)
                else:
                    # 如果第一帧无效 (例如图片文件损坏或 Animator 内部问题)
                    self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(首帧错误)")
                    self.pet_label.setAlignment(Qt.AlignCenter)
                    if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器
                    return # 无法播放，提前退出

                # 获取当前动画的速度 (可能每个动作的速度不同，如果 Animator 支持的话)
                current_speed = self.animator.get_animation_speed()
                # 如果定时器的当前间隔与新动画的速度不同，或者定时器未激活，则更新并启动/重启定时器
                if self.animation_timer.interval() != current_speed or not self.animation_timer.isActive():
                    self.animation_timer.setInterval(current_speed) # 设置定时器的新间隔
                    self.animation_timer.start() # 启动或重新启动定时器

                print(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 已启动，速度 {current_speed}ms/帧。")
            else:
                # Animator 成功设置了动作名，但该动作没有有效的帧
                print(f"PetWindow: 角色 '{self.current_pet_character_name}' 的动作 '{animation_name}' 没有帧，动画定时器停止。")
                if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器
                self.pet_label.setText(f"{self.current_pet_character_name}\n{animation_name}\n(无帧)")
                self.pet_label.setAlignment(Qt.AlignCenter)
        else:
            # Animator 未能成功设置 (切换到) 指定的动作 (例如，动作名不存在且无法加载)
            print(f"PetWindow: Animator 未能为角色 '{self.current_pet_character_name}' 设置动作 '{animation_name}'。")
            if self.animation_timer.isActive(): self.animation_timer.stop() # 停止定时器
            self.pet_label.setText(f"无法播放\n{self.current_pet_character_name}\n{animation_name}")
            self.pet_label.setAlignment(Qt.AlignCenter)


    def update_animation(self):
        """
        此方法由 self.animation_timer 的 timeout 信号定期调用。
        负责从 Animator 获取下一帧并更新到 QLabel 上，从而形成动画。
        """
        # 确保 Animator 存在且当前有有效的动画帧在播放
        if self.animator and self.animator._current_frames:
            next_pixmap = self.animator.next_frame() # 从 Animator 获取下一帧
            if not next_pixmap.isNull(): # 确保获取到的帧是有效的
                self.pet_label.setPixmap(next_pixmap) # 更新 QLabel 显示的图片


    # --- 鼠标事件处理方法，用于实现窗口拖动 ---
    def mousePressEvent(self, event):
        """当鼠标在窗口上按下时调用。"""
        if event.button() == Qt.LeftButton: # 只响应鼠标左键
            self.dragging = True # 进入拖动状态
            # 计算鼠标按下点相对于窗口左上角的偏移 (drag_position)
            # event.globalPos() 是鼠标在屏幕上的全局坐标
            # self.pos() 是窗口左上角在屏幕上的坐标
            self.drag_position = event.globalPos() - self.pos()
            event.accept() # 事件已被处理

    def mouseMoveEvent(self, event):
        """当鼠标在窗口上按下并移动时调用。"""
        # 检查是否处于拖动状态 (self.dragging) 并且鼠标左键仍然被按住
        if self.dragging and event.buttons() & Qt.LeftButton:
            # 移动窗口到新的位置：当前鼠标全局位置 - 之前记录的偏移量
            self.move(event.globalPos() - self.drag_position)
            event.accept() # 事件已被处理

    def mouseReleaseEvent(self, event):
        """当鼠标在窗口上松开时调用。"""
        if event.button() == Qt.LeftButton: # 如果是左键松开
            self.dragging = False # 退出拖动状态
            event.accept() # 事件已被处理

    # --- 应用程序关闭逻辑 ---
    def close_application(self):
        """安全地关闭整个应用程序。"""
        print("正在关闭应用程序...")
        # 检查动画定时器是否存在且正在运行，如果是，则先停止它
        if hasattr(self, 'animation_timer') and self.animation_timer.isActive():
            self.animation_timer.stop()
        QApplication.instance().quit() # 请求 Qt 应用程序退出事件循环

    # --- 右键上下文菜单 ---
    def contextMenuEvent(self, event):
        """当在窗口上右键单击时调用，用于显示上下文菜单。"""
        context_menu = QMenu(self) # 创建一个 QMenu 对象
        
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
        exit_action = QAction("退出宠物", self)
        exit_action.triggered.connect(self.close_application) # 连接到关闭应用程序的方法
        context_menu.addAction(exit_action) # 将退出动作添加到菜单

        context_menu.exec_(event.globalPos()) # 在鼠标光标的全局位置显示菜单

    # --- (未来功能占位) 获取可用角色列表的方法 ---
    # def get_available_characters(self):
    #     """扫描 self.all_pets_base_path 目录，返回所有子文件夹名作为可用角色列表。"""
    #     if not os.path.isdir(self.all_pets_base_path):
    #         return [] # 如果基础路径不存在，返回空列表
    #     # 列表推导式：遍历基础路径下的所有条目，如果是文件夹，则将其名称加入列表
    #     return [d for d in os.listdir(self.all_pets_base_path) 
    #             if os.path.isdir(os.path.join(self.all_pets_base_path, d))]


# --- 主代码块，用于直接运行 window.py 进行测试 ---
if __name__ == '__main__':
    app = QApplication(sys.argv) # 创建 QApplication 实例，这是任何 PyQt 程序运行的前提

    # --- 指定初始加载的宠物角色名 ---
    # 你需要确保在 G:\CodePet\assets\pets\ 目录下有一个与此名称同名的文件夹，
    # 并且该文件夹内有符合 DEFAULT_ACTION_ANIMATION (例如 "idle") 名称的子文件夹及帧图片。
    # 例如，如果 initial_character = "cat_alpha"，
    # 则需要 G:\CodePet\assets\pets\cat_alpha\idle\frameXX.png 这样的结构。
    initial_character = "test" # 你可以改成你实际创建的第一个角色名，比如 "cat_alpha" 或 "dog_beta"

    # 创建 PetWindow 实例，传入初始角色名
    pet_window = PetWindow(initial_pet_character_name=initial_character)
    pet_window.show() # 显示宠物窗口

    sys.exit(app.exec_()) # 启动 Qt 应用程序的事件循环，程序会在此阻塞直到退出