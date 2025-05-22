#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统计记录器模块 - 记录并保存每日编程统计数据
"""

import os
import json
import time
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

# 导入数据库管理器
from core.stats.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class StatsLogger:
    """
    统计数据记录器，用于收集和保存编程活动统计信息
    """
    
    def __init__(self, config: Any):
        """
        初始化统计记录器
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
        
        # 获取数据库路径
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'stats.db'
        )
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(self.db_path)
        
        # 当前日期
        self.current_date = date.today().isoformat()
        
        # 确保数据表存在
        self._ensure_tables()
        
        # 加载今日数据
        self.today_stats = self._load_today_stats()
    
    def _ensure_tables(self) -> None:
        """确保所有必要的数据表已创建"""
        self.db_manager.create_tables_if_not_exist()
        logger.debug("数据库表已检查/创建")
    
    def _load_today_stats(self) -> Dict[str, Any]:
        """
        加载今天的统计数据，如果不存在则创建
        
        Returns:
            今天的统计数据
        """
        # 获取今天的数据
        stats = self.db_manager.get_day_stats(self.current_date)
        
        # 如果不存在，初始化新记录
        if not stats:
            logger.info(f"为日期 {self.current_date} 创建新的统计记录")
            stats = {
                'date': self.current_date,
                'total_time': 0,
                'keypress_count': 0,
                'app_breakdown': json.dumps({}),
                'hourly_breakdown': json.dumps({str(h): 0 for h in range(24)}),
                'top_keys': json.dumps({}),
                'start_mood': 'normal',
                'end_mood': None,
                'achievements': json.dumps([]),
                'goals_met': False,
                'notes': ''
            }
            self.db_manager.insert_day_stats(stats)
        else:
            # 解析JSON字段
            for field in ['app_breakdown', 'hourly_breakdown', 'top_keys', 'achievements']:
                if field in stats and stats[field]:
                    try:
                        stats[field] = json.loads(stats[field])
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析字段 {field} 的JSON数据，重置为空")
                        stats[field] = {} if field != 'achievements' else []
        
        return stats
    
    def update_stats(self, activity_stats: Dict[str, Any], key_stats: Dict[str, Any]) -> None:
        """
        更新统计数据
        
        Args:
            activity_stats: 活动统计信息
            key_stats: 键盘统计信息
        """
        today = date.today().isoformat()
        
        # 如果日期变了，创建新的一天记录
        if today != self.current_date:
            self.save_daily_stats()  # 保存昨天的数据
            self.current_date = today
            self.today_stats = self._load_today_stats()
        
        # 更新统计数据
        self.today_stats['total_time'] = activity_stats.get('total_time', 0)
        self.today_stats['keypress_count'] = key_stats.get('total_keypresses', 0)
        self.today_stats['app_breakdown'] = json.dumps(activity_stats.get('app_breakdown', {}))
        self.today_stats['hourly_breakdown'] = json.dumps(key_stats.get('hourly_breakdown', {}))
        self.today_stats['top_keys'] = json.dumps(key_stats.get('top_keys', {}))
        
        # 检查目标是否达成
        daily_goal_hours = self.config.get_setting('stats.daily_goal', 6)
        self.today_stats['goals_met'] = (activity_stats.get('total_hours', 0) >= daily_goal_hours)
        
        # 保存到数据库（临时保存，一天内多次调用）
        self._save_today_stats()
        
        logger.debug(f"统计数据已更新，编程时间: {activity_stats.get('total_time', 0)/3600:.2f}小时")
    
    def _save_today_stats(self) -> None:
        """保存今天的统计数据到数据库（临时保存）"""
        self.db_manager.update_day_stats(self.today_stats)
    
    def save_daily_stats(self) -> None:
        """保存每日统计（在一天结束或程序退出时调用）"""
        if not self.today_stats:
            return
        
        # 设置结束心情（如果尚未设置）
        if not self.today_stats.get('end_mood'):
            # 根据目标完成情况设置默认心情
            self.today_stats['end_mood'] = 'happy' if self.today_stats.get('goals_met', False) else 'tired'
        
        # 最终保存
        self.db_manager.update_day_stats(self.today_stats)
        logger.info(f"日期 {self.current_date} 的统计数据已保存")
    
    def get_streak_info(self) -> Dict[str, Any]:
        """
        获取连续编程的天数信息
        
        Returns:
            连续编程的天数信息
        """
        # 获取过去30天的统计
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        daily_stats = self.db_manager.get_stats_range(start_date.isoformat(), end_date.isoformat())
        
        # 计算当前连续天数
        current_streak = 0
        last_date = end_date
        
        for stat in sorted(daily_stats, key=lambda x: x['date'], reverse=True):
            stat_date = datetime.strptime(stat['date'], '%Y-%m-%d').date()
            
            # 如果日期连续，且当天有活动
            if (last_date - stat_date).days <= 1 and (stat['total_time'] > 0 or stat['keypress_count'] > 0):
                current_streak += 1
                last_date = stat_date
            else:
                break
        
        # 计算最长连续天数
        days_with_activity = [
            datetime.strptime(stat['date'], '%Y-%m-%d').date()
            for stat in daily_stats
            if stat['total_time'] > 0 or stat['keypress_count'] > 0
        ]
        days_with_activity.sort()
        
        longest_streak = 0
        current_longest = 0
        last_day = None
        
        for day in days_with_activity:
            if last_day is None:
                current_longest = 1
            elif (day - last_day).days == 1:
                current_longest += 1
            else:
                current_longest = 1
            
            last_day = day
            longest_streak = max(longest_streak, current_longest)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'active_days_month': len(days_with_activity),
            'total_days_tracked': self.db_manager.get_total_days()
        }
    
    def get_weekly_summary(self) -> Dict[str, Any]:
        """
        获取每周编程统计摘要
        
        Returns:
            每周编程统计摘要
        """
        # 获取过去7天的统计
        end_date = date.today()
        start_date = end_date - timedelta(days=6)  # 7天，包括今天
        daily_stats = self.db_manager.get_stats_range(start_date.isoformat(), end_date.isoformat())
        
        # 初始化天数数据
        days_data = []
        day_map = {(start_date + timedelta(days=i)).isoformat(): i for i in range(7)}
        
        # 填充实际数据
        for stat in daily_stats:
            day_idx = day_map.get(stat['date'])
            if day_idx is not None:
                hours = stat['total_time'] / 3600
                days_data.append({
                    'date': stat['date'],
                    'hours': hours,
                    'keypress': stat['keypress_count'],
                    'goals_met': stat['goals_met']
                })
        
        # 添加缺失的天数
        for date_str, idx in day_map.items():
            if not any(d['date'] == date_str for d in days_data):
                days_data.append({
                    'date': date_str,
                    'hours': 0,
                    'keypress': 0,
                    'goals_met': False
                })
        
        # 按日期排序
        days_data.sort(key=lambda x: x['date'])
        
        # 计算总体统计
        total_hours = sum(day['hours'] for day in days_data)
        total_keypress = sum(day['keypress'] for day in days_data)
        goals_met_count = sum(1 for day in days_data if day['goals_met'])
        
        return {
            'days': days_data,
            'total_hours': total_hours,
            'total_keypress': total_keypress,
            'avg_hours': total_hours / 7,
            'goals_met_count': goals_met_count,
            'week_start': start_date.isoformat(),
            'week_end': end_date.isoformat()
        }
    
    def add_achievement(self, achievement_id: str, achievement_data: Dict[str, Any]) -> None:
        """
        添加成就到今天的统计
        
        Args:
            achievement_id: 成就ID
            achievement_data: 成就数据
        """
        achievements = self.today_stats.get('achievements', [])
        if isinstance(achievements, str):
            try:
                achievements = json.loads(achievements)
            except:
                achievements = []
        
        # 检查是否已存在该成就
        if not any(a.get('id') == achievement_id for a in achievements):
            achievements.append({
                'id': achievement_id,
                'name': achievement_data.get('name', '未命名成就'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'description': achievement_data.get('description', '')
            })
            
            self.today_stats['achievements'] = json.dumps(achievements)
            self._save_today_stats()
            logger.info(f"添加成就 '{achievement_id}' 到统计")
    
    def update_mood(self, mood: str, is_end_mood: bool = False) -> None:
        """
        更新今日心情
        
        Args:
            mood: 心情值 (happy, normal, tired, etc.)
            is_end_mood: 是否为结束时的心情
        """
        field = 'end_mood' if is_end_mood else 'start_mood'
        self.today_stats[field] = mood
        self._save_today_stats()
        logger.debug(f"更新{field}: {mood}")
    
    def add_notes(self, notes: str) -> None:
        """
        添加今日笔记
        
        Args:
            notes: 笔记内容
        """
        self.today_stats['notes'] = notes
        self._save_today_stats()
        logger.debug("更新今日笔记")
