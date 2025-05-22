#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理器 - 用于加载和管理应用配置
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Union, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config'
        )
        self.settings_path = os.path.join(self.config_dir, 'settings.yaml')
        self.model_config_path = os.path.join(self.config_dir, 'model_config.json')
        
        self.settings = {}
        self.model_config = {}
        
        self.load_config()
    
    def load_config(self) -> None:
        """加载所有配置文件"""
        self.load_settings()
        self.load_model_config()
    
    def load_settings(self) -> None:
        """加载YAML配置文件"""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    self.settings = yaml.safe_load(f) or {}
                logger.info(f"已加载设置文件: {self.settings_path}")
            else:
                logger.warning(f"设置文件不存在: {self.settings_path}")
                self.create_default_config()
        except Exception as e:
            logger.error(f"加载设置文件失败: {e}", exc_info=True)
            self.settings = {}
    
    def load_model_config(self) -> None:
        """加载模型配置JSON文件"""
        try:
            if os.path.exists(self.model_config_path):
                with open(self.model_config_path, 'r', encoding='utf-8') as f:
                    self.model_config = json.load(f)
                logger.info(f"已加载模型配置文件: {self.model_config_path}")
            else:
                logger.warning(f"模型配置文件不存在: {self.model_config_path}")
        except Exception as e:
            logger.error(f"加载模型配置文件失败: {e}", exc_info=True)
            self.model_config = {}
    
    def create_default_config(self) -> None:
        """创建默认配置文件"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 创建默认设置文件
        default_settings = {
            'user': {
                'name': '程序员',
                'workspace': ['C:/Projects']
            },
            'pet': {
                'name': '皮皮',
                'type': 'cat',
                'personality': 'cheerful',
                'voice': {
                    'enable': True,
                    'volume': 0.8,
                    'speed': 1.0
                }
            },
            'ui': {
                'theme': 'light',
                'transparency': 0.9,
                'always_on_top': True,
                'position': {'x': -1, 'y': -1},
                'animation': {'fps': 24, 'scale': 1.0}
            },
            'stats': {
                'record_idle_threshold': 300,
                'daily_goal': 6,
                'enable_keylogger': True,
                'programming_apps': [
                    'code.exe', 'pycharm64.exe', 'idea64.exe', 
                    'sublime_text.exe', 'atom.exe', 'eclipse.exe',
                    'powershell.exe', 'cmd.exe', 'WindowsTerminal.exe'
                ]
            },
            'notifications': {
                'enable': True,
                'rest_reminder': 55,
                'daily_summary': True,
                'achievement_alerts': True
            },
            'plugins': {
                'achievement': True,
                'pomodoro': True,
                'github_stats': False
            }
        }
        
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"已创建默认设置文件: {self.settings_path}")
            self.settings = default_settings
        except Exception as e:
            logger.error(f"创建默认设置文件失败: {e}", exc_info=True)
        
        # 创建默认模型配置文件
        default_model_config = {
            'model_config': {
                'llm': {
                    'provider': 'volcengine',
                    'model': 'eb-instant',
                    'api_key': '',
                    'api_secret': '',
                    'temperature': 0.7,
                    'max_tokens': 1024,
                    'system_prompt': '你是一个名叫{pet_name}的友好的编程桌宠。你充满活力、性格{personality}，喜欢帮助你的主人编程。你可以回答编程问题、提供鼓励，或者进行日常闲聊。你应该表现得拟人化，有时候会用emoji表情，并使用简洁的回复。'
                },
                'asr': {
                    'provider': 'volcengine',
                    'language': 'zh',
                    'api_key': '',
                    'api_secret': '',
                    'app_id': '',
                    'format': 'wav',
                    'sample_rate': 16000
                },
                'tts': {
                    'provider': 'volcengine',
                    'api_key': '',
                    'api_secret': '',
                    'app_id': '',
                    'voice_type': 'zh_female_qingxuan',
                    'format': 'mp3',
                    'sample_rate': 24000
                }
            },
            'voice_detection': {
                'silence_threshold': 500,
                'min_silence_duration': 1.0,
                'speech_timeout': 5.0,
                'chunk_size': 1024,
                'wake_words': ['嘿，皮皮', '你好，皮皮']
            },
            'advanced_options': {
                'use_streaming_mode': True,
                'cache_audio': True,
                'cache_dir': './data/temp',
                'network_timeout': 10.0
            }
        }
        
        try:
            with open(self.model_config_path, 'w', encoding='utf-8') as f:
                json.dump(default_model_config, f, indent=2, ensure_ascii=False)
            logger.info(f"已创建默认模型配置文件: {self.model_config_path}")
            self.model_config = default_model_config
        except Exception as e:
            logger.error(f"创建默认模型配置文件失败: {e}", exc_info=True)
    
    def save_settings(self) -> bool:
        """
        保存设置到YAML文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"已保存设置到文件: {self.settings_path}")
            return True
        except Exception as e:
            logger.error(f"保存设置文件失败: {e}", exc_info=True)
            return False
    
    def save_model_config(self) -> bool:
        """
        保存模型配置到JSON文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(self.model_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.model_config, f, indent=2, ensure_ascii=False)
            logger.info(f"已保存模型配置到文件: {self.model_config_path}")
            return True
        except Exception as e:
            logger.error(f"保存模型配置文件失败: {e}", exc_info=True)
            return False
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """
        获取指定路径的设置值
        
        Args:
            key_path: 点分隔的键路径，如'pet.voice.volume'
            default: 如果路径不存在时返回的默认值
            
        Returns:
            找到的设置值，或默认值
        """
        keys = key_path.split('.')
        value = self.settings
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_model_config(self, key_path: str, default: Any = None) -> Any:
        """
        获取指定路径的模型配置值
        
        Args:
            key_path: 点分隔的键路径，如'model_config.llm.api_key'
            default: 如果路径不存在时返回的默认值
            
        Returns:
            找到的配置值，或默认值
        """
        keys = key_path.split('.')
        value = self.model_config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def update_setting(self, key_path: str, value: Any, auto_save: bool = True) -> bool:
        """
        更新指定路径的设置值
        
        Args:
            key_path: 点分隔的键路径，如'pet.voice.volume'
            value: 要设置的新值
            auto_save: 是否自动保存到文件
            
        Returns:
            更新是否成功
        """
        keys = key_path.split('.')
        target = self.settings
        
        # 遍历到最后一个键的父对象
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # 设置最后一个键的值
        target[keys[-1]] = value
        
        # 如果需要，保存到文件
        if auto_save:
            return self.save_settings()
        return True
    
    def update_model_config(self, key_path: str, value: Any, auto_save: bool = True) -> bool:
        """
        更新指定路径的模型配置值
        
        Args:
            key_path: 点分隔的键路径，如'model_config.llm.api_key'
            value: 要设置的新值
            auto_save: 是否自动保存到文件
            
        Returns:
            更新是否成功
        """
        keys = key_path.split('.')
        target = self.model_config
        
        # 遍历到最后一个键的父对象
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # 设置最后一个键的值
        target[keys[-1]] = value
        
        # 如果需要，保存到文件
        if auto_save:
            return self.save_model_config()
        return True
