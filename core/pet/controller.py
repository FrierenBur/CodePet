#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
宠物控制器模块 - 管理宠物的行为、状态和动画指令
"""

import os
import time
import random
import logging
import threading
from typing import Dict, List, Any, Optional # Callable 已移除，因为当前版本未使用

# 导入宠物数据模型 和 事件系统
from core.pet.model import PetModel, MoodType, ActionType, StateType #
# from core.events import EventSystem # 实际项目中，你需要确保 EventSystem 类能被正确导入

logger = logging.getLogger(__name__) # 获取当前模块的日志记录器

class PetController:
    """
    宠物控制器，管理宠物的行为、状态，并发出播放动画的指令。
    """
    
    def __init__(self, config: Any, event_system: Any):
        """
        初始化宠物控制器
        
        Args:
            config: 配置管理器实例 (ConfigManager)
            event_system: 事件系统实例 (EventSystem)
        """
        self.config = config
        self.event_system = event_system
        
        # 从配置中加载宠物设置
        pet_name = self.config.get_setting('pet.name', '皮皮') #
        pet_type = self.config.get_setting('pet.type', 'cat') # 这个将作为 character_name
        personality = self.config.get_setting('pet.personality', 'cheerful') #
        
        # 创建宠物模型实例
        self.pet = PetModel(name=pet_name, pet_type=pet_type, personality=personality) #
        
        # 状态更新相关的计时器和间隔
        self.last_state_update = time.time() # 上次宠物属性更新的时间戳
        # 从配置读取状态更新间隔，如果配置中没有，则默认为 10.0 秒
        self.state_update_interval = self.config.get_setting('pet.state_update_interval', 10.0) 
        
        # 用于管理由 set_action(duration=...) 创建的 threading.Timer 实例列表
        self._action_timers: List[threading.Timer] = []

        # 注册 PetController 关心（需要处理）的事件
        self._register_events()
        
        logger.info(f"宠物控制器已初始化: {self.pet.name} (角色类型: {self.pet.pet_type})")
        # 可以在 PetController 初始化完成后，立即设置一个初始状态和动作
        # 例如： self.set_state(StateType.IDLE) 
        # 这会触发一系列的 set_mood, set_action 调用，并最终通过事件系统通知 PetWindow 播放动画。
        # 这个调用也可以放在 main.py 中，在所有组件都初始化完成后。


    def _clear_action_timers(self) -> None:
        """清除所有当前活动的、用于恢复默认动作的定时器。"""
        if self._action_timers:
            logger.debug(f"PetController: 正在清除 {len(self._action_timers)} 个活动的动作定时器。")
        for timer in self._action_timers:
            timer.cancel() # 取消定时器的执行
        self._action_timers = [] # 清空列表


    def _register_events(self) -> None:
        """注册本控制器需要监听和处理的事件及其对应的处理方法。"""
        if not self.event_system:
            logger.error("PetController: EventSystem 未提供，无法注册事件处理器！")
            return
            
        # 监听编程活动相关的事件
        self.event_system.register('programming_started', self._on_programming_started) #
        self.event_system.register('programming_ended', self._on_programming_ended) #
        self.event_system.register('programming_idle', self._on_programming_idle) #
        
        # 监听键盘按键事件
        self.event_system.register('keypress', self._on_keypress) #
        
        # 监听成就和目标达成的事件
        self.event_system.register('achievement_unlocked', self._on_achievement_unlocked)
        self.event_system.register('goal_reached', self._on_goal_reached)
        
        # 监听来自UI的宠物交互事件 (例如点击)
        self.event_system.register('pet_interaction', self._on_pet_interaction)
    

    def set_mood(self, mood: MoodType) -> None: #
        """
        设置宠物的心情。
        
        Args:
            mood: 新的心情状态 (MoodType 枚举成员)。
        """
        # 参数类型检查，确保传入的是 MoodType 枚举成员
        if not isinstance(mood, MoodType): #
            logger.warning(f"PetController: 尝试设置无效的心情类型: {mood}。将使用默认 MoodType.NORMAL。")
            mood = MoodType.NORMAL # # 回退到默认心情
            
        prev_mood = self.pet.mood # 获取之前的心情
        if prev_mood == mood: # 如果心情没有实际改变
            # logger.debug(f"PetController: 宠物 '{self.pet.name}' 心情已经是 '{mood.value}'，无需更改。")
            return # 则不执行后续操作

        self.pet.mood = mood # 更新宠物模型中的心情
        logger.info(f"PetController: 宠物 '{self.pet.name}' 心情从 '{prev_mood.value}' 变为 '{mood.value}'。") # 使用 INFO 级别记录重要状态变化
        
        # 通过事件系统发出心情变化的通知
        self.event_system.emit('pet_mood_changed', {
            'character_name': self.pet.pet_type, # 当前宠物的角色类型
            'previous_mood': prev_mood.value,    # 改变前的心情
            'current_mood': mood.value         # 改变后的当前心情
        })
        # 注意：通常单纯改变心情不会立即触发新的动画播放，
        # 心情更多是作为一种状态，影响后续动作动画的选择 (如果动画资源支持按心情区分) 或宠物的其他行为。
    
    def set_action(self, action: ActionType, duration: Optional[float] = None) -> None: #
        """
        设置宠物当前的主要动作，并发出事件通知UI层播放对应动画。
        如果提供了 duration，则该动作被视为临时动作，在持续时间结束后会自动尝试恢复到 IDLE 动作。
        
        Args:
            action: 新的动作 (ActionType 枚举成员)。
            duration: 此动作的持续时间（秒）。如果为 None，则该动作为持续性动作。
        """
        # 参数类型检查
        if not isinstance(action, ActionType): #
            logger.warning(f"PetController: 尝试设置无效的动作类型: {action}。将使用默认 ActionType.IDLE。")
            action = ActionType.IDLE #

        # 如果要设置的是一个有持续时间的临时动作，或者要设置的是一个非临时的持续性动作，
        # 都应该先清除掉之前可能存在的、还未到期的临时动作的恢复定时器。
        # 这样做是为了避免旧的定时器意外地覆盖了新的、更优先的动作指令。
        if (duration is not None and duration > 0) or (duration is None):
            logger.debug(f"PetController: 准备设置新动作 '{action.value}' (持续时间: {duration if duration else '永久'})，正在清除所有旧的临时动作定时器。")
            self._clear_action_timers()

        prev_action = self.pet.current_action # 获取之前的动作

        # 如果要设置的动作与当前动作相同，并且没有指定持续时间 (即不是要重置一个临时动作的计时器)
        # 那么可能不需要做任何事情，除非希望强制从该动作的第一帧开始重播。
        if prev_action == action and duration is None:
            logger.debug(f"PetController: 宠物 '{self.pet.name}' 已在执行持续性动作 '{action.value}'，无需重复设置。")
            # 如果确实需要强制重播，可以在这里也发出 'ui_play_animation' 事件。
            # 目前逻辑是，如果动作相同且非临时，则不重新触发。
            return

        self.pet.current_action = action # 更新宠物模型中的当前动作
        
        logger.info(f"PetController: 宠物 '{self.pet.name}' 动作从 '{prev_action.value}' 变为 '{action.value}'。")
        
        # 准备要发送给UI层的数据包
        event_data_for_ui = {
            'character_name': self.pet.pet_type,    # 当前宠物的角色名/类型
            'action_name': action.value,            # 要播放的动作的名称 (应与动画文件夹名对应)
            'mood_name': self.pet.mood.value        # 当前心情 (UI层可选，用于选择动画变种)
        }
        logger.debug(f"PetController: 发出 'ui_play_animation' 事件，数据: {event_data_for_ui}")
        self.event_system.emit('ui_play_animation', event_data_for_ui) # 通过事件系统通知UI播放动画
        
        # 触发一个更通用的“宠物动作已改变”事件，供其他可能需要监听此变化的模块使用
        self.event_system.emit('pet_action_changed', {
            'character_name': self.pet.pet_type,
            'previous_action': prev_action.value,
            'current_action': action.value
        })
        
        # 如果为这个动作设置了持续时间 (duration > 0)，则创建一个定时器
        # 在持续时间结束后，自动将宠物动作恢复到 IDLE。
        if duration is not None and duration > 0:
            # 捕获外部的 action 变量的值 (即当前被设置为临时动作的 action)，
            # 以便在定时器回调函数 restore_default_action 中进行比较。
            action_that_was_set_as_temporary = action 
            
            def restore_default_action():
                logger.debug(f"PetController (Timer Callback): 进入 restore_default_action。预期的临时动作为 '{action_that_was_set_as_temporary.value}'，当前实际动作为 '{self.pet.current_action.value}'。")
                # 核心检查：只有当宠物的当前动作仍然是当初设置的那个临时动作时，才执行恢复。
                # 这是为了防止这个过期的定时器错误地覆盖了在这期间由其他事件触发的、更新的、更优先的动作。
                if self.pet.current_action == action_that_was_set_as_temporary: 
                    logger.info(f"PetController (Timer Callback): 临时动作 '{action_that_was_set_as_temporary.value}' (持续 {duration}s) 已结束，准备恢复到 IDLE 状态。")
                    self.set_action(ActionType.IDLE) # # 恢复到 IDLE 动作 (这将再次调用 set_action)
                else:
                    logger.info(f"PetController (Timer Callback): 临时动作 '{action_that_was_set_as_temporary.value}' 的恢复被忽略，因为当前动作已变为 '{self.pet.current_action.value}' (可能已被新指令覆盖)。")
            
            logger.debug(f"PetController: 为动作 '{action.value}' 创建了一个 {duration} 秒后调用 restore_default_action 的定时器。")
            new_timer = threading.Timer(duration, restore_default_action)
            new_timer.daemon = True # 设置为守护线程，确保主程序退出时此定时器线程也会随之结束
            new_timer.start() # 启动定时器
            self._action_timers.append(new_timer) # 将新创建的定时器加入管理列表
    
    def set_state(self, state: StateType) -> None: #
        """
        设置宠物的主要状态 (如 IDLE, WORKING, SLEEPING)，
        并根据新状态自动调整其心情和默认执行的动作。
        
        Args:
            state: 新的状态 (StateType 枚举成员)。
        """
        # 参数类型检查
        if not isinstance(state, StateType): #
            logger.warning(f"PetController: 尝试设置无效的状态类型: {state}。将使用默认 StateType.IDLE。")
            state = StateType.IDLE #

        prev_state = self.pet.state # 获取之前的状态
        if prev_state == state: # 如果请求设置的状态与当前状态相同
            logger.debug(f"PetController: 宠物 '{self.pet.name}' 已处于状态 '{state.value}'。")
            # 即使状态相同，也检查一下当前动作是否是该状态应有的默认主要动作。
            # 如果不是 (例如，之前是一个临时动作)，则强制设置回该状态的默认动作。
            current_default_action_for_state = None
            if state == StateType.IDLE: current_default_action_for_state = ActionType.IDLE #
            elif state == StateType.WORKING: current_default_action_for_state = ActionType.WORK #
            elif state == StateType.SLEEPING: current_default_action_for_state = ActionType.SLEEP #

            if current_default_action_for_state and self.pet.current_action != current_default_action_for_state:
                logger.info(f"PetController: 状态 '{state.value}' 未变，但当前动作 '{self.pet.current_action.value}' 不是默认动作，强制恢复为 '{current_default_action_for_state.value}'。")
                self.set_action(current_default_action_for_state)
            return # 状态未改变，或者已处理了动作恢复，则直接返回

        self.pet.state = state # 更新宠物模型中的状态
        logger.info(f"PetController: 宠物 '{self.pet.name}' 状态从 '{prev_state.value}' 变为 '{state.value}'。")
        
        # 通过事件系统发出状态变化的通知
        self.event_system.emit('pet_state_changed', {
            'character_name': self.pet.pet_type,
            'previous_state': prev_state.value,
            'current_state': state.value
        })
        
        # --- 根据新进入的状态，设置对应的心情和主要动作 ---
        if state == StateType.WORKING: #
            # 进入工作状态时的逻辑
            if self.pet.energy > 70: self.set_mood(MoodType.HAPPY) #
            elif self.pet.energy < 30: self.set_mood(MoodType.TIRED) #
            else: self.set_mood(MoodType.NORMAL) #
            self.set_action(ActionType.WORK) # # 播放工作/打字动画
        
        elif state == StateType.IDLE: #
            # 进入空闲状态时的逻辑
            if self.pet.energy > 70 and self.pet.happiness > 60:
                self.set_mood(MoodType.PLAYFUL) #
                # 随机播放一个“玩耍”的临时动画，持续3到7秒
                self.set_action(ActionType.PLAY, duration=random.uniform(3.0, 7.0)) #
            elif self.pet.energy < 30 :
                self.set_mood(MoodType.TIRED) #
                self.set_action(ActionType.REST) # # 播放休息动画 (可能是持续的，直到状态改变)
            else:
                self.set_mood(MoodType.RELAXED) #
                self.set_action(ActionType.IDLE) # # 播放标准的空闲动画
        
        elif state == StateType.SLEEPING: #
            # 进入睡眠状态时的逻辑
            self.set_mood(MoodType.SLEEPY) # # 设置为困倦的心情
            self.set_action(ActionType.SLEEP) # # 播放睡觉动画
    
    def update_pet_stats_periodically(self) -> None:
        """
        周期性地更新宠物的内部属性（如能量、快乐值等）。
        这个方法应该由一个外部的定时器或主循环定期调用。
        """
        current_time = time.time()
        
        # 检查是否到达了更新间隔
        if current_time - self.last_state_update >= self.state_update_interval:
            self.last_state_update = current_time # 更新上次更新时间戳
            
            logger.debug(f"PetController: 执行周期性宠物属性更新。当前状态: {self.pet.state.value}, 能量: {self.pet.energy}, 快乐: {self.pet.happiness}")

            # 根据当前宠物的主要状态，调整能量和快乐值等属性
            if self.pet.state == StateType.WORKING: #
                # 工作时消耗能量和快乐值 (这些消耗值可以从配置读取)
                self.pet.energy = max(0, self.pet.energy - self.config.get_setting('pet.decay_rates.energy_working', 2))
                self.pet.happiness = max(0, self.pet.happiness - self.config.get_setting('pet.decay_rates.happiness_working', 1))
            elif self.pet.state == StateType.IDLE: #
                # 空闲时缓慢恢复能量
                self.pet.energy = min(100, self.pet.energy + self.config.get_setting('pet.regen_rates.energy_idle', 1))
                # 空闲时快乐值可能缓慢下降 (如果长时间无互动)，或者根据当前心情略微调整
                if self.pet.mood == MoodType.PLAYFUL: #
                    self.pet.happiness = min(100, self.pet.happiness + 1) # 玩耍时快乐值可能略微增加
                else:
                    self.pet.happiness = max(0, self.pet.happiness - self.config.get_setting('pet.decay_rates.happiness_idle', 0.5))
            elif self.pet.state == StateType.SLEEPING: #
                # 睡眠时较快恢复能量和快乐值
                self.pet.energy = min(100, self.pet.energy + self.config.get_setting('pet.regen_rates.energy_sleeping', 5))
                self.pet.happiness = min(100, self.pet.happiness + self.config.get_setting('pet.regen_rates.happiness_sleeping', 2))
            
            # 根据更新后的属性值，重新评估并设置宠物的心情
            self._update_mood_based_on_stats() 
            
            # 检查是否有因属性变化而需要触发的特殊行为或状态转换
            # 例如：如果能量过低并且宠物正在工作，发出警告并可能播放一个临时性的“疲劳”动画
            low_energy_threshold = self.config.get_setting('pet.thresholds.low_energy', 20)
            if self.pet.energy < low_energy_threshold and self.pet.state == StateType.WORKING: #
                # 避免重复触发 ALERT 动画，可以检查当前动作是否已经是 ALERT
                if self.pet.current_action != ActionType.ALERT: #
                    logger.info(f"PetController: 宠物 '{self.pet.name}' 能量过低 ({self.pet.energy})，触发 ALERT 动作。")
                    self.set_action(ActionType.ALERT, duration=self.config.get_setting('pet.durations.alert_low_energy', 5.0)) #
                # 发出一个事件，可以用于UI提示或语音提示
                self.event_system.emit('pet_alert', { 
                    'type': 'low_energy',
                    'message': f'{self.pet.name} 感觉能量不足，建议休息一下！',
                    'energy_level': self.pet.energy
                })
            
            logger.debug(f"PetController: 宠物属性更新后: 状态={self.pet.state.value}, 心情={self.pet.mood.value}, 能量={self.pet.energy}, 快乐={self.pet.happiness}")
            # 发出一个通用的宠物属性已更新的事件，UI层可以监听这个事件来更新相关的显示 (如能量条)
            self.event_system.emit('pet_stats_updated', self.pet.to_dict()) #

    def _update_mood_based_on_stats(self) -> None:
        """根据当前的能量和快乐值等核心属性来更新宠物的心情。"""
        # 这是一个示例性的心情判定逻辑，你可以根据需要设计得更复杂或从配置加载规则
        # 读取配置中的阈值，如果配置中没有则使用默认值
        threshold_energy_tired = self.config.get_setting('pet.thresholds.energy_tired', 20)
        threshold_happiness_sad = self.config.get_setting('pet.thresholds.happiness_sad', 30)
        threshold_energy_happy_excited = self.config.get_setting('pet.thresholds.energy_happy_excited', 80)
        threshold_happiness_happy_excited = self.config.get_setting('pet.thresholds.happiness_happy_excited', 70)
        threshold_energy_normal = self.config.get_setting('pet.thresholds.energy_normal', 60)
        threshold_happiness_normal = self.config.get_setting('pet.thresholds.happiness_normal', 50)

        new_mood = self.pet.mood # 默认为当前心情，只有在满足条件时才改变

        if self.pet.energy < threshold_energy_tired:
            new_mood = MoodType.TIRED #
        elif self.pet.happiness < threshold_happiness_sad:
            new_mood = MoodType.SAD #
        elif self.pet.energy > threshold_energy_happy_excited and self.pet.happiness > threshold_happiness_happy_excited:
            if self.pet.state == StateType.WORKING: #
                new_mood = MoodType.EXCITED # # 工作时精力充沛且开心 -> 兴奋
            else:
                new_mood = MoodType.HAPPY #
        elif self.pet.energy > threshold_energy_normal and self.pet.happiness > threshold_happiness_normal:
             # 只有当心情不是更负面的时候才变为NORMAL，避免覆盖TIRED或SAD
            if self.pet.mood not in [MoodType.TIRED, MoodType.SAD]: #
                 new_mood = MoodType.NORMAL #
        else: 
            # 其他一些中间状态，如果不是特别负面，也倾向于NORMAL
            if self.pet.mood not in [MoodType.TIRED, MoodType.SAD, MoodType.SLEEPY]: #
                 new_mood = MoodType.NORMAL #
        
        if self.pet.mood != new_mood: # 只有当计算出的新心情与当前不同时才调用set_mood
            self.set_mood(new_mood)
    
    # --- 事件处理方法 ---
    # 下面的 _on_... 方法是各种事件的处理器，它们会根据事件类型和当前状态来调用 set_state, set_mood, set_action
    
    def _on_programming_started(self, event_data: Dict[str, Any]) -> None:
        """当检测到用户开始编程活动时调用。"""
        app_name = event_data.get('app', '未知应用')
        logger.info(f"PetController: 事件 - 编程开始 (应用: {app_name})")
        self.set_state(StateType.WORKING) # # 将宠物主状态设为工作
        
        # 初始进入工作状态时，可以根据配置概率性地播放一个鼓励动画
        chance_encourage = self.config.get_setting('pet.chances.encourage_on_work_start', 0.4) # 例如40%概率
        if random.random() < chance_encourage:
            duration_encourage = self.config.get_setting('pet.durations.encourage_work_start', 3.0)
            self.set_action(ActionType.ENCOURAGE, duration=duration_encourage) #
        # else: set_state(StateType.WORKING) 内部已经根据能量等设置了心情和 ActionType.WORK 动作
    
    def _on_programming_ended(self, event_data: Dict[str, Any]) -> None:
        """当检测到用户结束编程活动时调用。"""
        duration = event_data.get('duration', 0)
        logger.info(f"PetController: 事件 - 编程结束 (持续时间: {duration:.0f}秒)")
        self.set_state(StateType.IDLE) # # 恢复到空闲状态
        
        # 根据编程时长给予不同的反馈
        if duration > self.config.get_setting('pet.thresholds.work_long_for_tired', 3600):  # 例如超过1小时
            self.set_mood(MoodType.TIRED) #
            self.set_action(ActionType.TIRED, duration=self.config.get_setting('pet.durations.tired_after_long_work', 5.0)) #
        elif duration > self.config.get_setting('pet.thresholds.work_medium_for_happy', 1800): # 例如超过30分钟
            self.set_mood(MoodType.HAPPY) #
            self.set_action(ActionType.HAPPY, duration=self.config.get_setting('pet.durations.happy_after_medium_work', 3.0)) #
        # 如果工作时间不长，set_state(StateType.IDLE) 内部的逻辑会处理空闲时的默认动作和心情
    
    def _on_programming_idle(self, event_data: Dict[str, Any]) -> None:
        """当检测到用户在编程应用中长时间无操作时调用。"""
        idle_time = event_data.get('idle_time', 0)
        logger.info(f"PetController: 事件 - 编程中空闲 (空闲时间: {idle_time:.0f}秒)")
        
        # 只有当宠物当前确实处于 WORKING 状态时，这个空闲才有意义去改变它的状态
        if self.pet.state == StateType.WORKING: #
            idle_to_sleep_threshold = self.config.get_setting('pet.thresholds.idle_to_sleep_in_work', 1800)  # 例如30分钟
            idle_to_bored_threshold = self.config.get_setting('pet.thresholds.idle_to_bored_in_work', 600) # 例如10分钟

            if idle_time > idle_to_sleep_threshold:
                logger.info(f"PetController: 工作中空闲时间过长 ({idle_time:.0f}s)，宠物进入睡眠状态。")
                self.set_state(StateType.SLEEPING) #
            elif idle_time > idle_to_bored_threshold:
                logger.info(f"PetController: 工作中空闲时间较长 ({idle_time:.0f}s)，宠物休息一下。")
                self.set_mood(MoodType.RELAXED) #
                # 播放一个休息或“发呆”的临时动画
                self.set_action(ActionType.REST, duration=self.config.get_setting('pet.durations.rest_when_bored', 10.0)) #
                # 可以发出一个事件提示用户可能离开或需要休息
                self.event_system.emit('user_maybe_afk', {'idle_duration': idle_time})
            # 短时间空闲可能不需要改变主状态，但 PetController 的 update_pet_stats_periodically 可能会调整心情
    
    def _on_keypress(self, event_data: Dict[str, Any]) -> None:
        """当检测到键盘按键时调用。"""
        # 如果宠物在睡觉，任何按键都可能是一个唤醒信号 (但实际状态转换应由活动追踪器判断用户是否真的回来了)
        if self.pet.state == StateType.SLEEPING: #
            logger.debug(f"PetController: 按键事件发生在宠物睡眠期间。发送 user_activity_resumed 事件。")
            # 发出一个通用事件，表示用户可能有活动了，让其他逻辑（如 ActivityTracker 或状态机本身）判断是否需要唤醒宠物
            self.event_system.emit('user_activity_resumed', {'source': 'keypress_during_sleep'})
            return # 睡眠时不进行下面的概率性互动

        # 如果宠物正在工作，根据配置的概率和按键次数触发短期互动动画
        if self.pet.state == StateType.WORKING: #
            # keypress 事件通常由 keylogger.py 发出，其中可能包含 'count' (当日总按键数)
            # 或 'burst_count' (短期内的按键数) 等信息。这里我们假设它有 'count'。
            keypress_total_count = event_data.get('count', 0) 
            
            reaction_interval = self.config.get_setting('pet.intervals.keypress_reaction', 50) # 每多少次按键检查一次
            reaction_chance = self.config.get_setting('pet.chances.keypress_reaction', 0.1)   # 触发反应的概率
            
            if keypress_total_count > 0 and reaction_interval > 0 and keypress_total_count % reaction_interval == 0:
                if random.random() < reaction_chance:
                    # 从配置或一个预定义的列表中选择一个随机的短期互动动作
                    possible_reactions = self.config.get_setting('pet.reactions.on_keypress', ['SURPRISED', 'HAPPY', 'ENCOURAGE'])
                    # 将字符串转换为 ActionType 枚举成员
                    reaction_action_str = random.choice(possible_reactions)
                    try:
                        chosen_reaction_action = ActionType[reaction_action_str.upper()] #
                        duration = random.uniform(
                            self.config.get_setting('pet.durations.keypress_reaction_min', 1.5),
                            self.config.get_setting('pet.durations.keypress_reaction_max', 3.0)
                        )
                        logger.debug(f"PetController: 按键计数达到 {keypress_total_count}，触发随机反应动作: {chosen_reaction_action.value}，持续 {duration:.1f}s。")
                        self.set_action(chosen_reaction_action, duration=duration)
                    except KeyError:
                        logger.warning(f"PetController: 配置的按键反应动作 '{reaction_action_str}' 不是有效的 ActionType。")
    
    def _on_achievement_unlocked(self, event_data: Dict[str, Any]) -> None:
        """当用户解锁成就时调用。"""
        achievement_name = event_data.get('name', '新成就')
        logger.info(f"PetController: 事件 - 成就解锁 ({achievement_name})")
        self.set_mood(MoodType.EXCITED) # # 心情变得兴奋
        # 播放一个持续时间较长的庆祝动画
        self.set_action(ActionType.CELEBRATE, duration=self.config.get_setting('pet.durations.celebrate_achievement', 5.0)) #
    
    def _on_goal_reached(self, event_data: Dict[str, Any]) -> None:
        """当用户达成每日编程目标时调用。"""
        logger.info(f"PetController: 事件 - 每日目标达成。")
        self.set_mood(MoodType.HAPPY) # # 心情开心
        self.set_action(ActionType.CELEBRATE, duration=self.config.get_setting('pet.durations.celebrate_goal', 4.0)) #
    
    def _on_pet_interaction(self, event_data: Dict[str, Any]) -> None:
        """
        处理来自UI的宠物交互事件 (例如用户点击了宠物)。
        
        Args:
            event_data (dict): 事件数据，应包含 'type' (例如 'click')。
        """
        interaction_type = event_data.get('type', '') # 获取交互类型
        logger.info(f"PetController: 收到宠物交互事件 - 类型: '{interaction_type}' 来自角色 '{event_data.get('character_name', self.pet.pet_type)}'")

        # 确保交互是针对当前 PetController 管理的宠物角色
        if event_data.get('character_name') != self.pet.pet_type:
            logger.debug(f"PetController: 交互事件针对角色 '{event_data.get('character_name')}'，但当前控制器管理的是 '{self.pet.pet_type}'。忽略。")
            return

        if interaction_type == 'click':
            # 如果宠物当前正在睡觉，点击会尝试唤醒它
            if self.pet.state == StateType.SLEEPING: #
                logger.info(f"PetController: 点击事件，宠物 '{self.pet.name}' 从睡眠中被唤醒。")
                self.set_state(StateType.IDLE) # # 转换到空闲状态（这会触发对应的默认动作和心情）
            else: 
                # 如果宠物不是在睡觉，被点击了就给一个反应
                # 随机决定是惊讶还是顽皮的心情
                new_mood_on_click = MoodType.SURPRISED if random.random() < 0.5 else MoodType.PLAYFUL #
                self.set_mood(new_mood_on_click)
                
                # 播放一个持续时间随机的 REACT 动作动画
                react_duration = random.uniform(
                    self.config.get_setting('pet.durations.react_min', 1.0),
                    self.config.get_setting('pet.durations.react_max', 2.5)
                )
                logger.info(f"PetController: 点击交互，宠物 '{self.pet.name}' 将播放 REACT 动作，持续 {react_duration:.2f} 秒。")
                self.set_action(ActionType.REACT, duration=react_duration) #
                
                # 点击宠物可以稍微增加一点快乐值
                self.pet.happiness = min(100, self.pet.happiness + self.config.get_setting('pet.gains.happiness_on_click', 2))
        
        elif interaction_type == 'feed': # 假设未来有喂食交互
            if self.pet.state != StateType.SLEEPING: # # 睡觉的时候不能喂食
                logger.info(f"PetController: 宠物 '{self.pet.name}' 被喂食。")
                self.set_mood(MoodType.HAPPY) #
                self.set_action(ActionType.EAT, duration=self.config.get_setting('pet.durations.eat', 3.0)) #
                # 喂食会增加能量和快乐值
                self.pet.energy = min(100, self.pet.energy + self.config.get_setting('pet.gains.energy_on_feed', 20))
                self.pet.happiness = min(100, self.pet.happiness + self.config.get_setting('pet.gains.happiness_on_feed', 10))
            else:
                logger.info(f"PetController: 宠物 '{self.pet.name}' 正在睡觉，不能被打扰吃东西。")
        
        # 在处理完交互后，重新评估心情（因为属性可能已改变）
        self._update_mood_based_on_stats()
        # 并发出宠物属性更新事件，以便UI等可以刷新显示
        self.event_system.emit('pet_stats_updated', self.pet.to_dict()) #

    
    def get_random_message(self, context: Optional[str] = None) -> str:
        """
        获取一条随机的宠物对话消息，根据当前宠物的性格、心情和给定的上下文。
        
        Args:
            context (Optional[str]): 消息的上下文情境 (例如 'greeting', 'encouragement', 'rest_reminder')。
                                     如果为 None，则可能返回一个通用的闲聊或当前心情的表达。
            
        Returns:
            str: 一条随机选择的对话文本。
        """
        personality = self.pet.personality
        mood_value = self.pet.mood.value # 获取心情的字符串值，例如 "happy", "normal"
        
        # 尝试从配置中获取对话库 (settings.yaml -> pet_dialogues)
        # 期望的对话库结构示例:
        # pet_dialogues:
        #   cheerful: # 性格
        #     greeting: # 上下文
        #       happy: ["看到你真开心！我们开始吧！", "今天又是元气满满的一天！"] # 心情
        #       normal: ["你好呀！准备好编程了吗？"]
        #     encouragement:
        #       happy: ["你太棒了！简直是天才！"]
        #       normal: ["继续加油，你做的很好！"]
        #   shy:
        #     # ...
        dialogue_library = self.config.get_setting('pet_dialogues', {})
        
        # 逐级获取消息列表
        messages_for_personality = dialogue_library.get(personality, {})
        
        # 优先使用带上下文和心情的消息
        options = messages_for_personality.get(context, {}).get(mood_value, [])
        
        # 如果没有特定心情的消息，尝试该上下文的通用消息
        if not options:
            options = messages_for_personality.get(context, {}).get('any_mood', []) # 'any_mood' 作为回退
            
        # 如果连上下文的通用消息也没有，尝试该性格的通用闲聊消息
        if not options:
            general_context = 'general_idle' if context != 'general_idle' else 'default_fallback'
            options = messages_for_personality.get(general_context, {}).get(mood_value, [])
            if not options:
                options = messages_for_personality.get(general_context, {}).get('any_mood', [])

        # 如果还是没有，使用一个非常通用的回退
        if not options:
            fallback_dialogues = self.config.get_setting('pet_dialogues.default_fallback.any_mood.any_mood', 
                                                        [f"{self.pet.name}正在思考...", "...", "嗯？"])
            options = fallback_dialogues
            
        return random.choice(options) if options else f"{self.pet.name}不知道说什么了。"


    def get_pet_data_for_ui(self) -> Dict[str, Any]:
        """
        获取一个简化的宠物数据字典，方便UI层展示或调试当前宠物状态。
        """
        return {
            "name": self.pet.name,
            "character_type": self.pet.pet_type,
            "state": self.pet.state.value,
            "action": self.pet.current_action.value,
            "mood": self.pet.mood.value,
            "energy": self.pet.energy,
            "happiness": self.pet.happiness
        }

    def shutdown(self):
        """在程序退出前，清理所有活动的定时器。"""
        logger.info(f"PetController for '{self.pet.name}' 正在关闭，清理动作定时器...")
        self._clear_action_timers()