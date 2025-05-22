#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
宠物控制器模块 - 管理宠物的行为、状态和动画
"""

import os
import time
import random
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

# 导入宠物数据模型
from core.pet.model import PetModel, MoodType, ActionType, StateType

logger = logging.getLogger(__name__)

class PetController:
    """
    宠物控制器，管理宠物的行为、状态和动画
    """
    
    def __init__(self, config: Any, event_system: Any):
        """
        初始化宠物控制器
        
        Args:
            config: 配置管理器实例
            event_system: 事件系统实例
        """
        self.config = config
        self.event_system = event_system
        
        # 从配置中加载宠物设置
        pet_name = self.config.get_setting('pet.name', '皮皮')
        pet_type = self.config.get_setting('pet.type', 'cat')
        personality = self.config.get_setting('pet.personality', 'cheerful')
        
        # 创建宠物模型
        self.pet = PetModel(name=pet_name, pet_type=pet_type, personality=personality)
        
        # 动画路径
        self.base_anim_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'assets', 'pets'
        )
        
        # 动画帧缓存
        self.animation_frames = {}
        
        # 状态更新计时器
        self.last_state_update = time.time()
        self.state_update_interval = 10.0  # 每10秒更新一次状态
        
        # 注册事件处理
        self._register_events()
        
        # 加载动画
        self._load_animations()
        
        logger.info(f"宠物控制器已初始化: {pet_name} ({pet_type})")
    
    def _register_events(self) -> None:
        """注册事件处理器"""
        # 编程开始/结束事件
        self.event_system.register('programming_started', self._on_programming_started)
        self.event_system.register('programming_ended', self._on_programming_ended)
        self.event_system.register('programming_idle', self._on_programming_idle)
        
        # 按键事件
        self.event_system.register('keypress', self._on_keypress)
        
        # 成就和目标事件
        self.event_system.register('achievement_unlocked', self._on_achievement_unlocked)
        self.event_system.register('goal_reached', self._on_goal_reached)
        
        # 交互事件
        self.event_system.register('pet_interaction', self._on_pet_interaction)
    
    def _load_animations(self) -> None:
        """加载宠物动画帧"""
        try:
            # 获取宠物类型特定的动画文件夹
            pet_anim_path = os.path.join(self.base_anim_path, self.pet.pet_type)
            
            if os.path.exists(pet_anim_path):
                # 加载所有动作的动画
                for action in ActionType:
                    action_path = os.path.join(pet_anim_path, action.value)
                    if os.path.exists(action_path):
                        frames = []
                        # 加载此动作的所有帧
                        for mood in MoodType:
                            mood_path = os.path.join(action_path, mood.value)
                            if os.path.exists(mood_path):
                                # 为每个心情加载帧
                                mood_frames = self._load_frames(mood_path)
                                if mood_frames:
                                    self.animation_frames[(action.value, mood.value)] = mood_frames
                
                logger.info(f"已加载宠物动画: {self.pet.pet_type}, {len(self.animation_frames)} 个动作-心情组合")
            else:
                logger.warning(f"宠物动画路径不存在: {pet_anim_path}")
        except Exception as e:
            logger.error(f"加载宠物动画失败: {e}", exc_info=True)
    
    def _load_frames(self, folder_path: str) -> List[str]:
        """
        加载指定文件夹中的所有动画帧
        
        Args:
            folder_path: 动画帧文件夹路径
            
        Returns:
            帧文件路径列表
        """
        frames = []
        
        try:
            if os.path.exists(folder_path):
                # 获取所有图像文件
                for file in sorted(os.listdir(folder_path)):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        frame_path = os.path.join(folder_path, file)
                        frames.append(frame_path)
        except Exception as e:
            logger.error(f"加载动画帧失败: {folder_path}, 错误: {e}", exc_info=True)
        
        return frames
    
    def get_current_frame(self) -> Optional[str]:
        """
        获取当前显示帧
        
        Returns:
            当前帧图像路径
        """
        action = self.pet.current_action.value
        mood = self.pet.mood.value
        
        # 尝试获取特定动作和心情的帧
        frames = self.animation_frames.get((action, mood))
        
        # 如果没有找到特定心情的帧，回退到普通心情
        if not frames:
            frames = self.animation_frames.get((action, MoodType.NORMAL.value))
        
        # 如果仍未找到，回退到默认动作
        if not frames:
            frames = self.animation_frames.get((ActionType.IDLE.value, mood))
        
        # 最后回退到完全默认
        if not frames:
            frames = self.animation_frames.get((ActionType.IDLE.value, MoodType.NORMAL.value))
        
        # 如果有帧，返回当前动画索引的帧
        if frames:
            # 获取动画帧索引（循环播放）
            frame_index = int(time.time() * self.pet.animation_speed) % len(frames)
            return frames[frame_index]
        
        return None
    
    def get_all_frames_for_animation(self, action: ActionType, mood: MoodType) -> List[str]:
        """
        获取指定动作和心情的所有帧
        
        Args:
            action: 动作类型
            mood: 心情类型
            
        Returns:
            帧路径列表
        """
        # 尝试获取特定动作和心情的帧
        frames = self.animation_frames.get((action.value, mood.value), [])
        
        # 如果没有找到特定心情的帧，回退到普通心情
        if not frames:
            frames = self.animation_frames.get((action.value, MoodType.NORMAL.value), [])
        
        return frames
    
    def set_mood(self, mood: MoodType) -> None:
        """
        设置宠物心情
        
        Args:
            mood: 新的心情状态
        """
        prev_mood = self.pet.mood
        self.pet.mood = mood
        
        logger.debug(f"宠物心情从 {prev_mood.value} 变为 {mood.value}")
        
        # 触发心情变化事件
        self.event_system.emit('pet_mood_changed', {
            'previous': prev_mood.value,
            'current': mood.value
        })
    
    def set_action(self, action: ActionType, duration: Optional[float] = None) -> None:
        """
        设置宠物当前动作
        
        Args:
            action: 新的动作
            duration: 持续时间（秒），如果为None则会一直保持此动作
        """
        prev_action = self.pet.current_action
        self.pet.current_action = action
        
        logger.debug(f"宠物动作从 {prev_action.value} 变为 {action.value}")
        
        # 触发动作变化事件
        self.event_system.emit('pet_action_changed', {
            'previous': prev_action.value,
            'current': action.value
        })
        
        # 如果设置了持续时间，创建定时器以恢复默认动作
        if duration is not None:
            def restore_default():
                self.pet.current_action = ActionType.IDLE
                logger.debug(f"宠物动作恢复为默认: {ActionType.IDLE.value}")
                
                # 触发动作变化事件
                self.event_system.emit('pet_action_changed', {
                    'previous': action.value,
                    'current': ActionType.IDLE.value
                })
            
            # 创建定时器
            timer = threading.Timer(duration, restore_default)
            timer.daemon = True
            timer.start()
    
    def set_state(self, state: StateType) -> None:
        """
        设置宠物状态
        
        Args:
            state: 新的状态
        """
        prev_state = self.pet.state
        self.pet.state = state
        
        logger.debug(f"宠物状态从 {prev_state.value} 变为 {state.value}")
        
        # 触发状态变化事件
        self.event_system.emit('pet_state_changed', {
            'previous': prev_state.value,
            'current': state.value
        })
        
        # 根据状态调整心情和动作
        if state == StateType.WORKING:
            if self.pet.energy > 70:
                self.set_mood(MoodType.HAPPY)
            elif self.pet.energy < 30:
                self.set_mood(MoodType.TIRED)
            else:
                self.set_mood(MoodType.NORMAL)
        
        elif state == StateType.IDLE:
            if self.pet.energy > 70:
                self.set_mood(MoodType.PLAYFUL)
                self.set_action(ActionType.PLAY, 5.0)
            else:
                self.set_mood(MoodType.RELAXED)
                self.set_action(ActionType.REST)
        
        elif state == StateType.SLEEPING:
            self.set_mood(MoodType.TIRED)
            self.set_action(ActionType.SLEEP)
    
    def update_state(self) -> None:
        """更新宠物状态（定期调用）"""
        current_time = time.time()
        
        # 只有在时间间隔达到时才更新
        if current_time - self.last_state_update >= self.state_update_interval:
            self.last_state_update = current_time
            
            # 更新能量
            if self.pet.state == StateType.WORKING:
                # 工作时能量减少
                self.pet.energy = max(0, self.pet.energy - 2)
            elif self.pet.state == StateType.IDLE:
                # 空闲时能量缓慢恢复
                self.pet.energy = min(100, self.pet.energy + 1)
            elif self.pet.state == StateType.SLEEPING:
                # 睡眠时能量恢复较快
                self.pet.energy = min(100, self.pet.energy + 3)
            
            # 更新心情
            self._update_mood()
            
            # 如果能量太低，提醒休息
            if self.pet.energy < 20 and self.pet.state == StateType.WORKING:
                self.set_action(ActionType.ALERT)
                self.event_system.emit('pet_alert', {
                    'type': 'low_energy',
                    'message': '能量不足，建议休息一下！'
                })
            
            logger.debug(f"宠物状态已更新: 状态={self.pet.state.value}, 心情={self.pet.mood.value}, 能量={self.pet.energy}")
    
    def _update_mood(self) -> None:
        """根据当前状态和能量更新心情"""
        if self.pet.energy < 20:
            self.set_mood(MoodType.TIRED)
        elif self.pet.energy > 80:
            if self.pet.state == StateType.WORKING:
                self.set_mood(MoodType.HAPPY)
            else:
                self.set_mood(MoodType.PLAYFUL)
        else:
            # 默认心情
            self.set_mood(MoodType.NORMAL)
    
    def _on_programming_started(self, event_data: Dict[str, Any]) -> None:
        """
        编程开始事件处理
        
        Args:
            event_data: 事件数据
        """
        self.set_state(StateType.WORKING)
        self.set_action(ActionType.WORK)
        
        # 随机决定是否播放鼓励动画
        if random.random() < 0.3:  # 30%的概率
            self.set_action(ActionType.ENCOURAGE, 3.0)
    
    def _on_programming_ended(self, event_data: Dict[str, Any]) -> None:
        """
        编程结束事件处理
        
        Args:
            event_data: 事件数据
        """
        self.set_state(StateType.IDLE)
        
        # 如果编程时间很长，显示"累了"的状态
        duration = event_data.get('duration', 0)
        if duration > 3600:  # 超过1小时
            self.set_action(ActionType.TIRED, 5.0)
        else:
            self.set_action(ActionType.IDLE)
    
    def _on_programming_idle(self, event_data: Dict[str, Any]) -> None:
        """
        编程空闲事件处理
        
        Args:
            event_data: 事件数据
        """
        idle_time = event_data.get('idle_time', 0)
        
        # 如果空闲时间很长，则切换到睡眠状态
        if idle_time > 1800:  # 超过30分钟
            self.set_state(StateType.SLEEPING)
        else:
            self.set_state(StateType.IDLE)
    
    def _on_keypress(self, event_data: Dict[str, Any]) -> None:
        """
        按键事件处理
        
        Args:
            event_data: 事件数据
        """
        # 每按100次键，有概率触发动作
        count = event_data.get('count', 0)
        
        if count % 100 == 0 and random.random() < 0.3:  # 30%的概率
            # 根据不同键数触发不同反应
            if count % 500 == 0:
                # 每500次按键，显示惊讶表情
                self.set_action(ActionType.SURPRISED, 2.0)
            elif count % 300 == 0:
                # 每300次按键，显示开心表情
                self.set_action(ActionType.HAPPY, 2.0)
            else:
                # 其他时候，显示鼓励
                self.set_action(ActionType.ENCOURAGE, 2.0)
    
    def _on_achievement_unlocked(self, event_data: Dict[str, Any]) -> None:
        """
        成就解锁事件处理
        
        Args:
            event_data: 事件数据
        """
        # 显示庆祝动画
        self.set_action(ActionType.CELEBRATE, 5.0)
        self.set_mood(MoodType.HAPPY)
    
    def _on_goal_reached(self, event_data: Dict[str, Any]) -> None:
        """
        目标达成事件处理
        
        Args:
            event_data: 事件数据
        """
        # 显示庆祝动画
        self.set_action(ActionType.CELEBRATE, 3.0)
        self.set_mood(MoodType.HAPPY)
    
    def _on_pet_interaction(self, event_data: Dict[str, Any]) -> None:
        """
        宠物交互事件处理（如点击宠物）
        
        Args:
            event_data: 事件数据
        """
        interaction_type = event_data.get('type', '')
        
        if interaction_type == 'click':
            # 点击宠物
            self.set_action(ActionType.REACT, 1.0)
        elif interaction_type == 'pet':
            # 抚摸宠物
            self.set_action(ActionType.HAPPY, 2.0)
            self.set_mood(MoodType.HAPPY)
            # 增加能量
            self.pet.energy = min(100, self.pet.energy + 5)
        elif interaction_type == 'feed':
            # 喂食宠物
            self.set_action(ActionType.EAT, 3.0)
            # 大幅增加能量
            self.pet.energy = min(100, self.pet.energy + 20)
    
    def get_random_message(self, context: Optional[str] = None) -> str:
        """
        获取随机消息，根据当前心情和上下文
        
        Args:
            context: 消息上下文（如'greeting', 'encouragement', 'rest', 等）
            
        Returns:
            随机消息文本
        """
        # 根据性格、心情和上下文选择合适的消息
        personality = self.pet.personality
        mood = self.pet.mood
        
        # 消息集合（实际应用中应该从更大的集合中选择或使用配置文件）
        messages = {
            'cheerful': {
                'greeting': {
                    'normal': ['嗨！今天准备写什么代码？', '你好啊！我们开始编程吧！'],
                    'happy': ['太棒了！又是美好的编程日！', '哇，看到你真高兴！来写代码吧！'],
                    'tired': ['嘿...虽然我有点累，但还是很高兴见到你！', '唔...今天或许可以写少一点代码？']
                },
                'encouragement': {
                    'normal': ['你做得很好！继续！', '代码看起来不错！'],
                    'happy': ['哇！你简直是编程天才！', '看看你写的这些代码，太棒了！'],
                    'tired': ['你已经写了很多了...也许休息一下？', '还在努力？你真坚持！']
                },
                'rest': {
                    'normal': ['适当休息有助于提高效率！', '短暂休息一下，再回来继续！'],
                    'happy': ['休息时间到！我们一起放松一下吧！', '别忘了休息！健康的程序员才能写出健康的代码！'],
                    'tired': ['终于...休息...', '太需要休息了...眼睛都睁不开了...']
                }
            },
            'shy': {
                'greeting': {
                    'normal': ['嗨...今天要编程吗？', '你好...'],
                    'happy': ['啊，你来了！我一直在等你开始编程...', '今天感觉会是个好日子...'],
                    'tired': ['嗯...你来了...', '今天可能不太有精神...']
                },
                'encouragement': {
                    'normal': ['你的代码...看起来很好...', '继续努力...'],
                    'happy': ['哇...你真的很擅长这个...', '我觉得...你的代码写得很好...'],
                    'tired': ['你已经做了很多了...', '也许...休息一下？']
                },
                'rest': {
                    'normal': ['也许应该休息一下...', '短暂休息是必要的...'],
                    'happy': ['休息时间！...太好了...', '休息是有必要的...'],
                    'tired': ['终于...休息...', '我需要...睡觉...']
                }
            },
            'quirky': {
                'greeting': {
                    'normal': ['哈！又是崭新的编程冒险！', '代码仙人驾到！准备好了吗？'],
                    'happy': ['哇哦！编程时间！代码雨！矩阵来了！', '代码，咖啡，还有我！完美的一天开始了！'],
                    'tired': ['唔...代码模糊中...需要充电...', '今天的编程能量有点低...']
                },
                'encouragement': {
                    'normal': ['哇！代码如泉涌！继续敲击那些神奇的字符！', '代码精灵为你喝彩！'],
                    'happy': ['你就是代码界的超新星！闪闪发光！', '这不是普通的代码，这是艺术品！'],
                    'tired': ['代码马拉松选手...需要偶尔停下来喝水...', '电子世界也需要日落时分...']
                },
                'rest': {
                    'normal': ['休息！充电！然后征服代码世界！', '让我们来一场量子休息，瞬间恢复满格电量！'],
                    'happy': ['休息时间！派对时间！舞动你的思维！', '休息是为了更好的编程！科学证明的！'],
                    'tired': ['系统...关闭中...休眠模式...启动...', '能量不足...请插入咖啡或休息...']
                }
            }
        }
        
        # 获取对应的消息集合
        personality_messages = messages.get(personality, messages['cheerful'])
        context_messages = personality_messages.get(context or 'greeting', personality_messages['greeting'])
        mood_messages = context_messages.get(mood.value, context_messages['normal'])
        
        # 随机选择一条消息
        return random.choice(mood_messages) if mood_messages else "喵~"
