#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
宠物数据模型模块 - 定义宠物的状态、心情和行为
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

class MoodType(Enum):
    """宠物心情类型枚举"""
    NORMAL = "normal"    # 普通
    HAPPY = "happy"      # 开心
    TIRED = "tired"      # 疲劳
    PLAYFUL = "playful"  # 顽皮
    RELAXED = "relaxed"  # 放松
    EXCITED = "excited"  # 兴奋
    SAD = "sad"          # 悲伤
    SLEEPY = "sleepy"    # 困倦


class ActionType(Enum):
    """宠物动作类型枚举"""
    IDLE = "idle"          # 空闲
    WORK = "work"          # 工作
    REST = "rest"          # 休息
    SLEEP = "sleep"        # 睡觉
    EAT = "eat"            # 吃
    PLAY = "play"          # 玩
    ALERT = "alert"        # 警告
    HAPPY = "happy"        # 开心表情
    CELEBRATE = "celebrate"  # 庆祝
    ENCOURAGE = "encourage"  # 鼓励
    TIRED = "tired"        # 疲劳表情
    SURPRISED = "surprised"  # 惊讶
    REACT = "react"        # 反应


class StateType(Enum):
    """宠物状态类型枚举"""
    IDLE = "idle"          # 空闲
    WORKING = "working"    # 编程中
    SLEEPING = "sleeping"  # 睡眠中


class PetModel:
    """宠物数据模型，存储宠物的状态和属性"""
    
    def __init__(self, name: str = "皮皮", pet_type: str = "cat", personality: str = "cheerful"):
        """
        初始化宠物模型
        
        Args:
            name: 宠物名称
            pet_type: 宠物类型（如cat, dog, penguin等）
            personality: 宠物性格（如cheerful, shy, quirky等）
        """
        # 基本信息
        self.name = name
        self.pet_type = pet_type
        self.personality = personality
        
        # 当前状态
        self.state = StateType.IDLE
        self.mood = MoodType.NORMAL
        self.current_action = ActionType.IDLE
        
        # 属性值 (0-100)
        self.energy = 100
        self.happiness = 60
        self.hygiene = 80
        self.social = 50
        
        # 经验和等级
        self.exp = 0
        self.level = 1
        
        # 解锁的外观
        self.unlocked_appearances = ["default"]
        self.current_appearance = "default"
        
        # 动画属性
        self.animation_speed = 5  # 帧/秒
        
        logger.debug(f"宠物模型已初始化: {name} ({pet_type}, {personality})")
    
    def update_exp(self, amount: int) -> bool:
        """
        更新经验值，如果达到升级条件则升级
        
        Args:
            amount: 增加的经验值
            
        Returns:
            是否升级
        """
        self.exp += amount
        
        # 检查是否达到升级条件
        exp_needed = self.level * 200  # 每级需要的经验值
        
        if self.exp >= exp_needed:
            self.level += 1
            self.exp = 0  # 重置经验值
            logger.info(f"宠物 {self.name} 升级到 {self.level} 级")
            return True
        
        return False
    
    def get_mood_value(self) -> int:
        """
        获取心情数值 (0-100)
        
        Returns:
            心情数值
        """
        # 根据不同心情返回不同数值
        mood_values = {
            MoodType.HAPPY: 90,
            MoodType.PLAYFUL: 85,
            MoodType.EXCITED: 80,
            MoodType.RELAXED: 70,
            MoodType.NORMAL: 60,
            MoodType.SLEEPY: 40,
            MoodType.TIRED: 30,
            MoodType.SAD: 20
        }
        
        return mood_values.get(self.mood, 60)
    
    def unlock_appearance(self, appearance_id: str) -> bool:
        """
        解锁新外观
        
        Args:
            appearance_id: 外观ID
            
        Returns:
            是否成功解锁
        """
        if appearance_id not in self.unlocked_appearances:
            self.unlocked_appearances.append(appearance_id)
            logger.info(f"宠物 {self.name} 解锁新外观: {appearance_id}")
            return True
        
        return False
    
    def set_appearance(self, appearance_id: str) -> bool:
        """
        设置当前外观
        
        Args:
            appearance_id: 外观ID
            
        Returns:
            是否成功设置
        """
        if appearance_id in self.unlocked_appearances:
            self.current_appearance = appearance_id
            logger.info(f"宠物 {self.name} 切换外观: {appearance_id}")
            return True
        
        return False
    
    def to_dict(self) -> dict:
        """
        将宠物模型转换为字典，用于序列化
        
        Returns:
            表示宠物的字典
        """
        return {
            'name': self.name,
            'pet_type': self.pet_type,
            'personality': self.personality,
            'state': self.state.value,
            'mood': self.mood.value,
            'current_action': self.current_action.value,
            'energy': self.energy,
            'happiness': self.happiness,
            'hygiene': self.hygiene,
            'social': self.social,
            'exp': self.exp,
            'level': self.level,
            'unlocked_appearances': self.unlocked_appearances,
            'current_appearance': self.current_appearance,
            'animation_speed': self.animation_speed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PetModel':
        """
        从字典创建宠物模型，用于反序列化
        
        Args:
            data: 表示宠物的字典
            
        Returns:
            创建的宠物模型
        """
        pet = cls(
            name=data.get('name', '皮皮'),
            pet_type=data.get('pet_type', 'cat'),
            personality=data.get('personality', 'cheerful')
        )
        
        # 设置状态和行为
        try:
            pet.state = StateType(data.get('state', 'idle'))
            pet.mood = MoodType(data.get('mood', 'normal'))
            pet.current_action = ActionType(data.get('current_action', 'idle'))
        except ValueError as e:
            logger.error(f"从字典加载状态错误: {e}")
            # 使用默认值
        
        # 设置属性值
        pet.energy = data.get('energy', 100)
        pet.happiness = data.get('happiness', 60)
        pet.hygiene = data.get('hygiene', 80)
        pet.social = data.get('social', 50)
        
        # 设置经验和等级
        pet.exp = data.get('exp', 0)
        pet.level = data.get('level', 1)
        
        # 设置外观
        pet.unlocked_appearances = data.get('unlocked_appearances', ["default"])
        pet.current_appearance = data.get('current_appearance', "default")
        
        # 设置动画属性
        pet.animation_speed = data.get('animation_speed', 5)
        
        return pet
