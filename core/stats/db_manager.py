#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理器模块 - 用于管理SQLite数据库的操作
"""

import os
import sqlite3
import logging
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    SQLite数据库管理器，负责数据库操作和维护
    """
    
    def __init__(self, db_path: str):
        """
        初始化数据库管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 测试数据库连接并初始化
        self._test_connection()
    
    def _test_connection(self) -> None:
        """测试数据库连接并初始化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            conn.close()
            logger.debug(f"数据库连接测试成功: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"数据库连接测试失败: {e}", exc_info=True)
            raise
    
    def _get_connection(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        获取数据库连接和游标
        
        Returns:
            数据库连接和游标对象的元组
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 让结果以字典形式返回
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        return conn, cursor
    
    def create_tables_if_not_exist(self) -> None:
        """创建必要的数据表（如果不存在）"""
        conn, cursor = self._get_connection()
        
        try:
            # 每日统计表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_time REAL,
                keypress_count INTEGER,
                app_breakdown TEXT,
                hourly_breakdown TEXT,
                top_keys TEXT,
                start_mood TEXT,
                end_mood TEXT,
                achievements TEXT,
                goals_met BOOLEAN,
                notes TEXT
            )
            ''')
            
            # 成就表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                icon TEXT,
                unlock_date TEXT,
                conditions TEXT
            )
            ''')
            
            # 设置表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
            ''')
            
            conn.commit()
            logger.debug("已创建数据库表")
        except sqlite3.Error as e:
            logger.error(f"创建数据库表失败: {e}", exc_info=True)
        finally:
            conn.close()
    
    def insert_day_stats(self, stats: Dict[str, Any]) -> bool:
        """
        插入每日统计数据
        
        Args:
            stats: 统计数据字典
            
        Returns:
            操作是否成功
        """
        conn, cursor = self._get_connection()
        
        try:
            # 序列化JSON字段，如果它们不是字符串
            for field in ['app_breakdown', 'hourly_breakdown', 'top_keys', 'achievements']:
                if field in stats and not isinstance(stats[field], str):
                    stats[field] = json.dumps(stats[field])
            
            cursor.execute('''
            INSERT INTO daily_stats (
                date, total_time, keypress_count, app_breakdown, 
                hourly_breakdown, top_keys, start_mood, end_mood,
                achievements, goals_met, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats.get('date'),
                stats.get('total_time', 0),
                stats.get('keypress_count', 0),
                stats.get('app_breakdown', '{}'),
                stats.get('hourly_breakdown', '{}'),
                stats.get('top_keys', '{}'),
                stats.get('start_mood', 'normal'),
                stats.get('end_mood'),
                stats.get('achievements', '[]'),
                stats.get('goals_met', False),
                stats.get('notes', '')
            ))
            
            conn.commit()
            logger.debug(f"插入日期 {stats.get('date')} 的统计数据")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"插入统计数据失败: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def update_day_stats(self, stats: Dict[str, Any]) -> bool:
        """
        更新每日统计数据
        
        Args:
            stats: 统计数据字典
            
        Returns:
            操作是否成功
        """
        conn, cursor = self._get_connection()
        
        try:
            # 序列化JSON字段，如果它们不是字符串
            for field in ['app_breakdown', 'hourly_breakdown', 'top_keys', 'achievements']:
                if field in stats and not isinstance(stats[field], str):
                    stats[field] = json.dumps(stats[field])
            
            cursor.execute('''
            UPDATE daily_stats SET
                total_time = ?,
                keypress_count = ?,
                app_breakdown = ?,
                hourly_breakdown = ?,
                top_keys = ?,
                start_mood = ?,
                end_mood = ?,
                achievements = ?,
                goals_met = ?,
                notes = ?
            WHERE date = ?
            ''', (
                stats.get('total_time', 0),
                stats.get('keypress_count', 0),
                stats.get('app_breakdown', '{}'),
                stats.get('hourly_breakdown', '{}'),
                stats.get('top_keys', '{}'),
                stats.get('start_mood', 'normal'),
                stats.get('end_mood'),
                stats.get('achievements', '[]'),
                stats.get('goals_met', False),
                stats.get('notes', ''),
                stats.get('date')
            ))
            
            conn.commit()
            logger.debug(f"更新日期 {stats.get('date')} 的统计数据")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"更新统计数据失败: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def get_day_stats(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的统计数据
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            统计数据字典，如果不存在则返回None
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (date_str,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"获取日期 {date_str} 的统计数据失败: {e}", exc_info=True)
            return None
        finally:
            conn.close()
    
    def get_stats_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        获取日期范围内的统计数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            统计数据字典列表
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute(
                'SELECT * FROM daily_stats WHERE date BETWEEN ? AND ? ORDER BY date',
                (start_date, end_date)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"获取日期范围 {start_date} 到 {end_date} 的统计数据失败: {e}", exc_info=True)
            return []
        finally:
            conn.close()
    
    def get_total_days(self) -> int:
        """
        获取总记录天数
        
        Returns:
            数据库中的总天数
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM daily_stats')
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"获取总记录天数失败: {e}", exc_info=True)
            return 0
        finally:
            conn.close()
    
    def save_achievement(self, achievement: Dict[str, Any]) -> bool:
        """
        保存成就信息
        
        Args:
            achievement: 成就数据
            
        Returns:
            操作是否成功
        """
        conn, cursor = self._get_connection()
        
        try:
            # 序列化条件字段，如果它不是字符串
            if 'conditions' in achievement and not isinstance(achievement['conditions'], str):
                achievement['conditions'] = json.dumps(achievement['conditions'])
            
            cursor.execute('''
            INSERT OR REPLACE INTO achievements (
                id, name, description, icon, unlock_date, conditions
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                achievement.get('id'),
                achievement.get('name', ''),
                achievement.get('description', ''),
                achievement.get('icon', ''),
                achievement.get('unlock_date', datetime.now().isoformat()),
                achievement.get('conditions', '{}')
            ))
            
            conn.commit()
            logger.debug(f"保存成就 {achievement.get('id')}")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"保存成就失败: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def get_achievement(self, achievement_id: str) -> Optional[Dict[str, Any]]:
        """
        获取成就信息
        
        Args:
            achievement_id: 成就ID
            
        Returns:
            成就数据字典，如果不存在则返回None
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('SELECT * FROM achievements WHERE id = ?', (achievement_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"获取成就 {achievement_id} 失败: {e}", exc_info=True)
            return None
        finally:
            conn.close()
    
    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """
        获取所有成就
        
        Returns:
            成就数据字典列表
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('SELECT * FROM achievements ORDER BY unlock_date')
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"获取所有成就失败: {e}", exc_info=True)
            return []
        finally:
            conn.close()
    
    def save_setting(self, key: str, value: Any) -> bool:
        """
        保存设置键值对
        
        Args:
            key: 设置键
            value: 设置值（将被转换为JSON字符串）
            
        Returns:
            操作是否成功
        """
        conn, cursor = self._get_connection()
        
        try:
            # 将值转换为JSON字符串
            if not isinstance(value, str):
                value = json.dumps(value)
            
            cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ''', (
                key,
                value,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            logger.debug(f"保存设置 {key}")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"保存设置失败: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取设置值
        
        Args:
            key: 设置键
            default: 默认值，如果键不存在
            
        Returns:
            设置值（尝试解析JSON），如果不存在则返回默认值
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                value = row[0]
                # 尝试解析JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return default
        except sqlite3.Error as e:
            logger.error(f"获取设置 {key} 失败: {e}", exc_info=True)
            return default
        finally:
            conn.close()
    
    def delete_setting(self, key: str) -> bool:
        """
        删除设置
        
        Args:
            key: 设置键
            
        Returns:
            操作是否成功
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute('DELETE FROM settings WHERE key = ?', (key,))
            conn.commit()
            logger.debug(f"删除设置 {key}")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"删除设置失败: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径，如果为None则使用默认路径
            
        Returns:
            备份是否成功
        """
        if backup_path is None:
            db_dir = os.path.dirname(self.db_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(db_dir, f'stats_backup_{timestamp}.db')
        
        try:
            # 创建备份目录
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # 使用SQLite的备份API
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            logger.info(f"数据库已备份到: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}", exc_info=True)
            return False
