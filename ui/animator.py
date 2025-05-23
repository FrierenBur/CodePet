import os
import sys
from PyQt5.QtGui import QPixmap, QColor # QColor 用于填充测试图片
from PyQt5.QtCore import Qt, QSize     # Qt 用于颜色常量
from PyQt5.QtWidgets import QApplication

class Animator:
    # ... (这里是你提供的 Animator 类的完整代码) ...
    def __init__(self, base_pet_path, initial_animation_name="idle", animation_speed_ms=100):
        """
        初始化动画管理器。

        参数:
            base_pet_path (str): 特定宠物角色动画的根目录 (例如: 'assets/pets/cat_alpha/')。
                                 这个目录下应该有对应不同动画状态的子文件夹 (如 'idle', 'walk')。
            initial_animation_name (str): 初始要播放的动画名称 (即 base_pet_path 下的子文件夹名)。
            animation_speed_ms (int): 动画帧之间的默认延迟时间 (毫秒)。
        """
        self.base_pet_path = base_pet_path  # 角色动画资源的根路径
        self.animation_speed_ms = animation_speed_ms  # 动画播放速度

        self._animations = {}  # 字典，用于存储所有加载的动画序列 (键: 动作名, 值: QPixmap帧列表)
        self._current_animation_name = None  # 当前正在播放的动作名
        self._current_frames = []  # 当前动作对应的 QPixmap 帧图片列表
        self._current_frame_index = 0  # 当前播放到第几帧的索引
        self._frame_size = QSize(0, 0)  # 动画帧的尺寸 (从第一张加载的有效图片获取)

        # --- 初始化加载逻辑 ---
        # 1. 优先尝试加载指定的初始动画动作
        if initial_animation_name:
            self.load_animation_sequence(initial_animation_name)

        # 2. 如果指定的初始动画加载不成功 (可能不存在或没有帧)，
        #    或者根本没有指定初始动画名，则尝试加载该角色路径下的所有其他动作。
        #    `.get(initial_animation_name)` 用于安全地检查键是否存在且其值不为None/空列表。
        if not self._animations or not self._animations.get(initial_animation_name):
            print(f"提示: 初始动作 '{initial_animation_name}' 加载不成功或未指定，尝试加载角色 '{os.path.basename(self.base_pet_path)}' 的所有可用动作。")
            self.load_all_animations_from_subfolders() # 加载 base_pet_path (角色路径) 下的所有动作子文件夹

        # 3. 设置当前要播放的动画
        #    首先尝试设置指定的 initial_animation_name
        if initial_animation_name in self._animations and self._animations[initial_animation_name]: # 确保初始动画名有效且有帧
            self.set_current_animation(initial_animation_name)
        elif self._animations:  # 如果指定的初始动画无效，但 _animations 字典中已加载了其他动画
            # 则遍历已加载的动画，选择第一个有有效帧的动画作为当前动画
            for anim_name, frames in self._animations.items():
                if frames:  # 确保这个动画序列里有帧
                    self.set_current_animation(anim_name)
                    break # 找到一个可用的就设置并跳出循环
        
        # 4. 最终检查：如果经过上述加载和设置后，仍然没有任何有效的当前动画帧
        if not self._current_frames:
            print(f"警告: Animator 初始化后，未能设置任何有效动画。角色路径: {self.base_pet_path}, 尝试的初始动作: {initial_animation_name}")


    def load_animation_sequence(self, animation_name): # animation_name 现在是动作名
        """
        加载指定名称的动作动画序列。
        动画帧图片应存放在 self.base_pet_path (角色路径) 下名为 animation_name (动作名) 的子文件夹中。
        """
        action_folder_path = os.path.join(self.base_pet_path, animation_name) # 构建动作文件夹的完整路径
        frames = []  # 用于存放当前动作加载的 QPixmap 帧

        # 检查动作文件夹是否存在
        if not os.path.isdir(action_folder_path):
            print(f"提示: 动作文件夹 '{action_folder_path}' 未找到 (在角色路径 '{self.base_pet_path}' 下)。")
            self._animations[animation_name] = frames  # 即使文件夹不存在，也记录一下这个动作名，对应一个空帧列表
            return

        # 筛选并排序文件夹内的图片文件
        # 要求文件名以 'frame' 开头 (不区分大小写)，并以常见的图片格式结尾
        image_files = sorted([
            f for f in os.listdir(action_folder_path)
            if os.path.isfile(os.path.join(action_folder_path, f)) and \
               f.lower().startswith('frame') and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ])

        # 检查是否找到了符合条件的图片文件
        if not image_files:
            print(f"提示: 在动作文件夹 '{action_folder_path}' 中未找到名为 'frameXX.png' (或类似) 格式的图片文件。")
            self._animations[animation_name] = frames
            return

        # 遍历找到的图片文件，加载为 QPixmap 对象
        for image_file in image_files:
            full_image_path = os.path.join(action_folder_path, image_file)
            pixmap = QPixmap(full_image_path)  # 加载图片
            if not pixmap.isNull():  # 检查图片是否成功加载
                frames.append(pixmap)
                if self._frame_size.isEmpty():  # 如果 Animator 的帧尺寸还未设定
                    self._frame_size = pixmap.size()  # 则使用加载的第一张有效图片的尺寸作为参考尺寸
            else:
                print(f"警告: 无法加载图片 '{full_image_path}'。")
        
        self._animations[animation_name] = frames  # 将加载的帧列表存入 _animations 字典
        if frames:
            # os.path.basename(self.base_pet_path) 用于获取角色名（即 base_pet_path 的最后一个文件夹名）
            print(f"角色 '{os.path.basename(self.base_pet_path)}' 的动作 '{animation_name}' 加载成功，共 {len(frames)} 帧。")
        else:
            print(f"警告: 角色 '{os.path.basename(self.base_pet_path)}' 的动作 '{animation_name}' 加载完成，但没有有效的帧。")


    def load_all_animations_from_subfolders(self):
        """
        扫描 self.base_pet_path (特定角色的动画根目录) 下的所有子文件夹，
        并将每个子文件夹作为一个独立的动作动画序列进行加载。
        """
        # 检查角色动画根目录是否存在
        if not os.path.isdir(self.base_pet_path):
            print(f"错误: 特定角色动画的根目录 '{self.base_pet_path}' 不存在。")
            return

        print(f"为角色 '{os.path.basename(self.base_pet_path)}' 加载所有可用的动作动画...")
        # 遍历角色根目录下的所有文件和文件夹
        for action_folder_name in os.listdir(self.base_pet_path):
            action_folder_path = os.path.join(self.base_pet_path, action_folder_name)
            if os.path.isdir(action_folder_path):  # 只处理子文件夹（这些子文件夹被视为动作）
                self.load_animation_sequence(action_folder_name) # 使用子文件夹名作为动作名进行加载


    # 在 animator.py 的 Animator 类中
    def set_current_animation(self, animation_name):
        print(f"Animator: 请求设置当前动作为 '{animation_name}'. 当前是 '{self._current_animation_name}'.") # 新增日志
        if animation_name not in self._animations or not self._animations.get(animation_name):
            print(f"Animator: 动作 '{animation_name}' 不在已加载或帧列表为空。当前已加载动作: {list(self._animations.keys())}") # 新增日志
            if animation_name not in self._animations:
                print(f"Animator: 尝试按需加载动作 '{animation_name}'...")
                self.load_animation_sequence(animation_name)

            if not self._animations.get(animation_name): # 再次检查
                print(f"Animator ERROR: 无法为角色 '{os.path.basename(self.base_pet_path)}' 设置或加载动作 '{animation_name}'。") # 修改日志
                return False

        # 如果要设置的动作和当前动作相同，并且帧列表也相同，则可能无需重置 (除非需要强制从头播放)
        if self._current_animation_name == animation_name and self._current_frames is self._animations.get(animation_name):
            print(f"Animator: 角色 '{os.path.basename(self.base_pet_path)}' 已在播放动作 '{animation_name}'，帧索引重置为0。")
            self._current_frame_index = 0 # 即使是相同动画，也重置到第一帧，确保重新播放
            return True


        print(f"Animator: 角色 '{os.path.basename(self.base_pet_path)}' 切换动作到: '{animation_name}'")
        self._current_animation_name = animation_name
        self._current_frames = self._animations[animation_name]
        self._current_frame_index = 0
        if self._current_frames and self._frame_size.isEmpty(): # 一般_frame_size在第一次加载时就定了
            self._frame_size = self._current_frames[0].size()
        elif not self._current_frames: # 如果切换到的动作没有帧
            print(f"Animator WARN: 动作 '{animation_name}' 被设置，但它没有帧！")
        return True


    def next_frame(self):
        """
        推进到当前动作序列的下一帧，并返回该帧的 QPixmap。
        如果到达序列末尾，则从头开始循环。
        """
        if not self._current_frames:  # 如果当前没有帧（例如，动作加载失败或动作本身为空）
            return QPixmap()  # 返回一个空的 QPixmap，避免错误

        # 计算下一帧的索引，使用取模运算 (%) 实现循环
        self._current_frame_index = (self._current_frame_index + 1) % len(self._current_frames)
        return self._current_frames[self._current_frame_index] # 返回计算出的下一帧


    def get_current_frame_pixmap(self):
        """
        获取当前动作序列的当前帧图像 (QPixmap)，不改变帧索引 (不推进动画)。
        """
        # 检查当前是否有有效帧，以及索引是否在范围内
        if not self._current_frames or \
           self._current_frame_index < 0 or \
           self._current_frame_index >= len(self._current_frames):
            return QPixmap() # 无效则返回空 QPixmap
        return self._current_frames[self._current_frame_index] # 返回当前索引指向的帧


    def get_frame_size(self):
        """
        获取动画帧的尺寸 (基于第一个成功加载的有效帧的尺寸)。
        """
        return self._frame_size


    def get_animation_speed(self):
        """
        获取当前动画的播放速度 (毫秒/帧)。
        """
        return self.animation_speed_ms

    def set_animation_speed(self, animation_speed_ms):
        """
        设置动画的播放速度。
        """
        if animation_speed_ms > 0:  # 速度值必须是正数
            self.animation_speed_ms = animation_speed_ms
        else:
            print("警告: 动画速度必须大于0。")


# --- 用于直接运行和测试 animator.py 的主代码块 (演示加载角色下的多个动作) ---
if __name__ == '__main__':
    # 任何 PyQt 图形操作 (如创建 QPixmap) 都需要一个 QApplication 实例首先存在
    app = QApplication(sys.argv)

    # --- 路径设置 ---
    script_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前脚本 (animator.py) 所在的目录
    project_root = os.path.abspath(os.path.join(script_dir, '..')) # 从脚本目录向上跳一级到项目根目录 (codepet/)
    
    # --- 模拟一个特定角色的动画目录结构进行测试 ---
    # temp_character_root_path 指向一个临时的 "角色名" 目录，用于存放测试动画资源
    # 例如 G:\CodePet\assets\temp_character_anim_dir\
    temp_character_root_path = os.path.join(project_root, 'assets', 'temp_character_anim_dir')
    
    # 定义测试角色的不同动作及其对应的（模拟）帧信息
    # 键是动作名 (会成为子文件夹名)，值是另一个字典 (键: 帧文件名, 值: 用于填充的颜色)
    character_actions_data = {
        "idle": { # 动作名 "idle"
            "frame01.png": QColor(Qt.cyan),     # idle 动作的第一帧用青色填充
            "frame02.png": QColor(Qt.darkCyan)  # idle 动作的第二帧用深青色填充
        },
        "walk": { # 动作名 "walk"
            "frame01.png": QColor(Qt.magenta),
            "frame02.png": QColor(Qt.darkMagenta),
            "frame03.png": QColor(Qt.red)
        },
        "empty_action": {} # 一个没有帧的动作，用于测试 Animator 对空动作的处理
    }

    # 循环创建临时的动作文件夹和帧图片
    for action_name, frames_info in character_actions_data.items():
        action_folder = os.path.join(temp_character_root_path, action_name) # 构建动作文件夹路径
        os.makedirs(action_folder, exist_ok=True) # 创建动作文件夹，如果已存在则不报错
        for frame_filename, color in frames_info.items(): # 遍历该动作的每一帧信息
            temp_frame_path = os.path.join(action_folder, frame_filename) # 构建帧图片文件的完整路径
            if not os.path.exists(temp_frame_path): # 只在文件不存在时创建，避免重复创建
                pix = QPixmap(70, 70) # 创建一个 70x70 像素的 QPixmap 对象作为帧图片
                pix.fill(color)       # 用指定的颜色填充这个 QPixmap
                pix.save(temp_frame_path, "PNG") # 将 QPixmap 保存为 PNG 图片文件
                print(f"创建了临时测试图片: {temp_frame_path}")

    print(f"\nAnimator 测试开始，目标角色动画的根目录: '{temp_character_root_path}'")
    
    # --- 实例化 Animator 进行测试 ---
    # base_pet_path 设置为我们刚创建的临时角色动画根目录
    # initial_animation_name 设置为 "idle"，让 Animator 尝试首先加载并播放 "idle" 动作
    animator = Animator(
        base_pet_path=temp_character_root_path, 
        initial_animation_name="idle", 
        animation_speed_ms=200  # 动画速度设为 200 毫秒/帧
    )

    # 检查 Animator 是否成功加载了任何动画和当前帧
    if not animator._animations or not animator._current_frames:
        print("错误：Animator 未能成功加载初始动作。请检查路径和资源文件。")
    else:
        # 打印加载成功后的信息
        print(f"\n初始动作: '{animator._current_animation_name}' (应为 'idle')")
        print(f"帧数量: {len(animator._current_frames)}")
        print(f"帧尺寸: {animator.get_frame_size().width()}x{animator.get_frame_size().height()}")
        print(f"动画速度: {animator.get_animation_speed()} ms/帧")

        # 测试播放 "idle" 动作，循环播放4帧 (因为 idle 只有2帧，所以会循环)
        print(f"\n测试播放 'idle' 动作 4 帧:")
        for i in range(4):
            current_pixmap = animator.get_current_frame_pixmap() # 获取当前帧但不推进
            print(f"动作 'idle', 帧 {i+1} (内部索引 {animator._current_frame_index}): "
                  f"Pixmap Not Null = {not current_pixmap.isNull()}")
            animator.next_frame() # 推进到下一帧
        
        # 测试切换到 "walk" 动作
        print(f"\n尝试切换到动作 'walk':")
        if animator.set_current_animation("walk"): # 调用切换方法
            print(f"当前动作: '{animator._current_animation_name}'")
            print(f"帧数量: {len(animator._current_frames)}")
            # 测试播放 "walk" 动作，循环播放5帧 (walk 有3帧)
            print(f"测试播放 'walk' 动作 5 帧:")
            for i in range(5):
                current_pixmap = animator.get_current_frame_pixmap()
                print(f"动作 'walk', 帧 {i+1} (内部索引 {animator._current_frame_index}): "
                      f"Pixmap Not Null = {not current_pixmap.isNull()}")
                animator.next_frame()
        else:
            print("错误：切换到动作 'walk' 失败。")

        # 测试切换到没有帧的 "empty_action"
        print(f"\n尝试切换到动作 'empty_action':")
        if animator.set_current_animation("empty_action"):
            print(f"当前动作: '{animator._current_animation_name}'")
            if not animator._current_frames: # 检查是否确实没有帧
                 print("符合预期，'empty_action' 没有帧。")
            next_p = animator.next_frame() # 尝试获取下一帧
            if next_p.isNull(): # 对于空动作，next_frame() 应该返回空 QPixmap
                print("调用 next_frame() 在空动作上返回空 Pixmap，符合预期。")
        else:
            # 如果 set_current_animation 对空动作返回 False，也会走到这里
            print(f"切换到 'empty_action' 的行为符合预期（可能设置成功但无帧，或直接设置失败）。当前动作名: {animator._current_animation_name}")

        # 测试切换到完全不存在的动作 "jump"
        print(f"\n尝试切换到不存在的动作 'jump':")
        if animator.set_current_animation("jump"): # "jump" 文件夹我们没有创建
            print(f"错误：不应能切换到不存在的动作 'jump'。")
        else:
            # Animator 应该无法切换到 "jump"，并保持之前的状态或一个有效的回退状态
            print(f"切换到不存在的动作 'jump' 失败，符合预期。当前动作仍为: '{animator._current_animation_name}'")


    print("\nAnimator 测试结束。")
    # 清理临时文件夹 (可选, 如果想在每次测试后都移除临时文件，可以取消注释下面几行)
    # import shutil
    # if os.path.exists(temp_character_root_path):
    #     shutil.rmtree(temp_character_root_path) # 递归删除整个临时角色文件夹
    #     print(f"已清理临时测试文件夹: {temp_character_root_path}")