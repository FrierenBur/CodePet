#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json # <<< 新增：导入json模块以处理配置文件
import logging # <<< 新增：导入logging模块
# === 新增：从 typing 模块导入所需的类型提示 ===
from typing import Optional, Dict, List, Any 
from PyQt5.QtGui import QPixmap, QColor # QColor 用于填充测试图片
from PyQt5.QtCore import Qt, QSize     # Qt 用于颜色常量
from PyQt5.QtWidgets import QApplication

# 获取当前模块的日志记录器实例
logger = logging.getLogger(__name__) # <<< 新增：获取logger实例
class Animator:
    # 使用 Optional 进行了类型提示
    def __init__(self, base_pet_path: str, initial_animation_name: Optional[str] = "idle", default_speed_ms: int = 100): #
        # ... (构造函数的其余部分代码保持不变) ...
        self.base_pet_path = base_pet_path #
        self.default_speed_ms = default_speed_ms #

        self._animations: Dict[str, List[QPixmap]] = {} #
        self._action_speeds: Dict[str, int] = {} #

        self._current_animation_name: Optional[str] = None #
        self._current_frames: List[QPixmap] = [] #
        self._current_frame_index: int = 0 #
        self._current_action_speed_ms: int = self.default_speed_ms #

        self._frame_size: QSize = QSize(0, 0) #

        self.load_all_animations_from_subfolders() #

        if initial_animation_name and self.set_current_animation(initial_animation_name): #
            pass 
        elif self._animations: #
            for anim_name, frames in self._animations.items(): #
                if frames: #
                    if self.set_current_animation(anim_name): #
                        break 
        
        if not self._current_frames: #
            logger.warning(f"Animator 初始化后，未能设置任何有效动画。角色路径: {self.base_pet_path}, 尝试的初始动作: {initial_animation_name}") #


    def load_animation_sequence(self, animation_name: str) -> bool: #
        action_folder_path = os.path.join(self.base_pet_path, animation_name) #
        loaded_speed_for_this_action = self.default_speed_ms #
        config_file_path = os.path.join(action_folder_path, "animation_config.json") #
        if os.path.exists(config_file_path): #
            try: #
                with open(config_file_path, 'r', encoding='utf-8') as f: #
                    config_data = json.load(f) #
                speed_val = config_data.get("speed_ms") #
                if isinstance(speed_val, int) and speed_val > 0: #
                    loaded_speed_for_this_action = speed_val #
                    logger.debug(f"Animator: 为动作 '{animation_name}' 从 '{config_file_path}' 加载专属速度: {loaded_speed_for_this_action}ms。") #
                else: #
                    logger.warning(f"Animator: 在 '{config_file_path}' 中找到的 'speed_ms' 值 ({speed_val}) 无效或非正数。将对动作 '{animation_name}' 使用默认速度 {self.default_speed_ms}ms。") #
            except json.JSONDecodeError: #
                logger.error(f"Animator: 解析动作 '{animation_name}' 的配置文件 '{config_file_path}' 失败 (JSON格式错误)。将使用默认速度 {self.default_speed_ms}ms。") #
            except Exception as e: #
                logger.error(f"Animator: 读取动作 '{animation_name}' 的配置文件 '{config_file_path}' 时发生未知错误: {e}。将使用默认速度 {self.default_speed_ms}ms。", exc_info=True) #
        else: #
            logger.debug(f"Animator: 未找到动作 '{animation_name}' 的专属速度配置文件 ('animation_config.json')。将使用默认速度 {self.default_speed_ms}ms。") #
        self._action_speeds[animation_name] = loaded_speed_for_this_action #
        if animation_name in self._animations: #
            logger.debug(f"Animator: 动作 '{animation_name}' 的帧已存在于缓存中，跳过帧加载。") #
            if self._current_animation_name == animation_name: #
                self._current_action_speed_ms = self._action_speeds[animation_name] #
            return True if self._animations[animation_name] else False #
        frames = []  #
        if not os.path.isdir(action_folder_path): #
            logger.warning(f"Animator: 动作文件夹 '{action_folder_path}' 未找到 (在角色路径 '{self.base_pet_path}' 下)。无法加载帧。") #
            self._animations[animation_name] = [] #
            return False #
        image_files = sorted([ #
            f for f in os.listdir(action_folder_path) #
            if os.path.isfile(os.path.join(action_folder_path, f)) and  #
               f.lower().startswith('frame') and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')) #
        ]) #
        if not image_files: #
            logger.warning(f"Animator: 在动作文件夹 '{action_folder_path}' 中未找到名为 'frameXX.png' (或类似) 格式的图片文件。") #
            self._animations[animation_name] = [] #
            return False #
        for image_file in image_files: #
            full_image_path = os.path.join(action_folder_path, image_file) #
            pixmap = QPixmap(full_image_path) #
            if not pixmap.isNull(): #
                frames.append(pixmap) #
                if self._frame_size.isEmpty(): #
                    self._frame_size = pixmap.size() #
            else: #
                logger.warning(f"Animator: 无法加载图片帧 '{full_image_path}'。") #
        self._animations[animation_name] = frames #
        if frames: #
            logger.info(f"Animator: 角色 '{os.path.basename(self.base_pet_path)}' 的动作 '{animation_name}' 加载成功，共 {len(frames)} 帧，速度 {loaded_speed_for_this_action}ms。") #
            return True #
        else: #
            logger.warning(f"Animator: 角色 '{os.path.basename(self.base_pet_path)}' 的动作 '{animation_name}' 加载完成，但没有有效的帧。") #
            return False #



    def load_all_animations_from_subfolders(self): #
        if not os.path.isdir(self.base_pet_path): #
            logger.error(f"Animator 错误: 特定角色动画的根目录 '{self.base_pet_path}' 不存在。") #
            return #
        logger.info(f"Animator: 为角色 '{os.path.basename(self.base_pet_path)}' 加载所有可用动作动画...") #
        for action_folder_name in os.listdir(self.base_pet_path): #
            action_folder_path = os.path.join(self.base_pet_path, action_folder_name) #
            if os.path.isdir(action_folder_path): #
                self.load_animation_sequence(action_folder_name) #

    def set_current_animation(self, animation_name: str) -> bool: #
        logger.info(f"Animator: 请求设置当前动作为 '{animation_name}'. 当前是 '{self._current_animation_name}'.") #
        if not self.load_animation_sequence(animation_name): #
            logger.error(f"Animator ERROR: 无法为角色 '{os.path.basename(self.base_pet_path)}' 设置或加载动作 '{animation_name}'。") #
            if self._current_frames:  #
                logger.warning(f"Animator: 由于 '{animation_name}' 加载失败，将继续播放当前动作 '{self._current_animation_name}'。") #
                return False #
            else: #
                 self._current_animation_name = None #
                 self._current_frames = [] #
                 self._current_frame_index = 0 #
                 self._current_action_speed_ms = self.default_speed_ms #
                 return False #
        if self._animations.get(animation_name): #
            logger.info(f"Animator: 角色 '{os.path.basename(self.base_pet_path)}' 切换/设置为动作: '{animation_name}'") #
            self._current_animation_name = animation_name #
            self._current_frames = self._animations[animation_name] #
            self._current_frame_index = 0 #
            self._current_action_speed_ms = self._action_speeds.get(animation_name, self.default_speed_ms) #
            if self._current_frames and self._frame_size.isEmpty(): #
                self._frame_size = self._current_frames[0].size() #
            return True #
        else: #
            logger.error(f"Animator ERROR: 动作 '{animation_name}' 加载后没有有效帧。") #
            if not self._current_frames: #
                 self._current_animation_name = None #
                 self._current_action_speed_ms = self.default_speed_ms #
            return False #

    def next_frame(self) -> QPixmap: #
        if not self._current_frames: #
            return QPixmap()  #
        self._current_frame_index = (self._current_frame_index + 1) % len(self._current_frames) #
        return self._current_frames[self._current_frame_index] #

    def get_current_frame_pixmap(self) -> QPixmap: #
        if not self._current_frames or \
           not (0 <= self._current_frame_index < len(self._current_frames)): #
            return QPixmap() #
        return self._current_frames[self._current_frame_index] #

    def get_frame_size(self) -> QSize: #
        return self._frame_size #

    def get_animation_speed(self) -> int: #
        return self._current_action_speed_ms #


    def set_animation_speed(self, animation_speed_ms: int) -> None: #
        if animation_speed_ms > 0: #
            logger.warning("Animator.set_animation_speed: 此方法设置的是默认后备速度，实际播放速度由各动作的 animation_config.json 决定。") #
            self.default_speed_ms = animation_speed_ms #
            if self._current_animation_name and self._action_speeds.get(self._current_animation_name) == self.default_speed_ms: #
                 self._current_action_speed_ms = animation_speed_ms #
        else: #
            logger.warning("Animator: 动画速度必须大于0。") #
            
    def get_current_animation_name(self) -> Optional[str]: #
        return self._current_animation_name #


# --- 用于直接运行和测试 animator.py 的主代码块 ---
if __name__ == '__main__':
    # 配置基础日志以便在控制台看到 DEBUG 级别以上的输出
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s')

    app = QApplication(sys.argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    
    # 模拟一个特定角色的动画目录结构进行测试
    temp_character_root_path = os.path.join(project_root, 'assets', 'temp_char_anim_for_speed_test')
    
    character_actions_data = {
        "idle": { # 动作名 "idle"
            "frames": {"frame01.png": QColor(Qt.cyan), "frame02.png": QColor(Qt.darkCyan)},
            "config": {"speed_ms": 250} # idle 动画速度 250ms/帧
        },
        "walk": { # 动作名 "walk"
            "frames": {"frame01.png": QColor(Qt.magenta), "frame02.png": QColor(Qt.darkMagenta), "frame03.png": QColor(Qt.red)},
            "config": {"speed_ms": 100} # walk 动画速度 100ms/帧
        },
        "run": { # 动作名 "run"，没有 animation_config.json，将使用默认速度
            "frames": {"frame01.png": QColor(Qt.yellow), "frame02.png": QColor(Qt.black)}
            # 无 config，将使用 Animator 构造时传入的 default_speed_ms
        },
        "empty_action": { # 一个没有帧的动作
            "frames": {},
            "config": {"speed_ms": 50} # 即使有配置，但没帧
        }
    }

    for action_name, action_data in character_actions_data.items():
        action_folder = os.path.join(temp_character_root_path, action_name)
        os.makedirs(action_folder, exist_ok=True)
        
        # 创建帧图片
        for frame_filename, color in action_data.get("frames", {}).items():
            temp_frame_path = os.path.join(action_folder, frame_filename)
            if not os.path.exists(temp_frame_path):
                pix = QPixmap(70, 70)
                pix.fill(color)
                pix.save(temp_frame_path, "PNG")
                logger.debug(f"创建了临时测试图片: {temp_frame_path}")
        
        # 创建 animation_config.json (如果定义了)
        if "config" in action_data:
            config_path = os.path.join(action_folder, "animation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(action_data["config"], f, indent=2)
            logger.debug(f"创建了临时配置文件: {config_path} 内容: {action_data['config']}")

    logger.info(f"\nAnimator 测试开始，目标角色动画的根目录: '{temp_character_root_path}'")
    
    # 实例化 Animator，传入一个默认后备速度
    animator = Animator(
        base_pet_path=temp_character_root_path, 
        initial_animation_name="idle", 
        default_speed_ms=150 # 这个是后备速度，如果 "idle" 有自己的配置，会被覆盖
    )

    if not animator._animations or not animator._current_frames:
        logger.error("错误：Animator 未能成功加载初始动作。")
    else:
        logger.info(f"\n初始动作: '{animator.get_current_animation_name()}'")
        logger.info(f"帧数量: {len(animator._current_frames)}")
        logger.info(f"帧尺寸: {animator.get_frame_size().width()}x{animator.get_frame_size().height()}")
        logger.info(f"动作 '{animator.get_current_animation_name()}' 的播放速度: {animator.get_animation_speed()} ms/帧 (预期 idle 为 250ms)")

        logger.info(f"\n测试播放 'idle' 动作 4 帧 (每帧应该较慢):")
        for i in range(4):
            current_pixmap = animator.get_current_frame_pixmap()
            logger.info(f"动作 'idle', 帧 {i+1} (索引 {animator._current_frame_index}), 速度 {animator.get_animation_speed()}ms")
            # 在实际应用中，你会在这里等待 animator.get_animation_speed() 毫秒
            animator.next_frame()
        
        logger.info(f"\n尝试切换到动作 'walk':")
        if animator.set_current_animation("walk"):
            logger.info(f"当前动作: '{animator.get_current_animation_name()}'")
            logger.info(f"帧数量: {len(animator._current_frames)}")
            logger.info(f"动作 '{animator.get_current_animation_name()}' 的播放速度: {animator.get_animation_speed()} ms/帧 (预期 walk 为 100ms)")
            logger.info(f"测试播放 'walk' 动作 5 帧 (每帧应该较快):")
            for i in range(5):
                current_pixmap = animator.get_current_frame_pixmap()
                logger.info(f"动作 'walk', 帧 {i+1} (索引 {animator._current_frame_index}), 速度 {animator.get_animation_speed()}ms")
                animator.next_frame()
        else:
            logger.error("错误：切换到动作 'walk' 失败。")

        logger.info(f"\n尝试切换到动作 'run' (无专属速度配置):")
        if animator.set_current_animation("run"):
            logger.info(f"当前动作: '{animator.get_current_animation_name()}'")
            logger.info(f"帧数量: {len(animator._current_frames)}")
            logger.info(f"动作 '{animator.get_current_animation_name()}' 的播放速度: {animator.get_animation_speed()} ms/帧 (预期 run 为默认后备速度 150ms)")
            logger.info(f"测试播放 'run' 动作 4 帧:")
            for i in range(4):
                current_pixmap = animator.get_current_frame_pixmap()
                logger.info(f"动作 'run', 帧 {i+1} (索引 {animator._current_frame_index}), 速度 {animator.get_animation_speed()}ms")
                animator.next_frame()
        else:
            logger.error("错误：切换到动作 'run' 失败。")
            
        logger.info(f"\n尝试切换到动作 'empty_action':")
        if animator.set_current_animation("empty_action"):
            logger.info(f"当前动作: '{animator.get_current_animation_name()}'")
            logger.info(f"帧数量: {len(animator._current_frames)} (预期为0)")
            logger.info(f"动作 '{animator.get_current_animation_name()}' 的播放速度: {animator.get_animation_speed()} ms/帧 (预期为配置的 50ms，即使没帧)")
            if not animator._current_frames:
                 logger.info("符合预期，'empty_action' 没有帧。")
            next_p = animator.next_frame()
            if next_p.isNull():
                logger.info("调用 next_frame() 在空动作上返回空 Pixmap，符合预期。")
        else:
            logger.info(f"切换到 'empty_action' 的行为符合预期（可能设置成功但无帧，或直接设置失败）。当前动作名: {animator.get_current_animation_name()}")


    logger.info("\nAnimator 测试结束。")
    # 清理临时文件夹的代码可以取消注释以在测试后自动删除
    # import shutil
    # if os.path.exists(temp_character_root_path):
    #     shutil.rmtree(temp_character_root_path)
    #     logger.info(f"已清理临时测试文件夹: {temp_character_root_path}")