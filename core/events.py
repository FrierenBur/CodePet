#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全局事件系统 (Event Bus / Event Dispatcher)
用于模块间的解耦通信。
"""

import logging
from typing import Callable, Dict, List, Any, Optional

# 获取日志记录器实例
logger = logging.getLogger(__name__)

class EventSystem:
    """
    一个简单的事件系统，允许模块订阅事件和发布事件。
    """

    def __init__(self):
        """
        初始化事件系统。
        _listeners 是一个字典，键是事件名称 (字符串)，值是该事件对应的处理器函数列表。
        """
        self._listeners: Dict[str, List[Callable[[Optional[Dict[str, Any]]], None]]] = {}
        logger.info("事件系统已初始化。")

    def register(self, event_name: str, handler: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        """
        注册一个事件处理器 (监听器)。
        当具有指定名称的事件被发出时，注册的处理器将被调用。

        参数:
            event_name (str): 要监听的事件的名称。
            handler (Callable): 事件发生时要调用的函数或方法。
                                 这个处理器函数应该能接受一个可选的字典参数 (事件数据)。
        """
        if not callable(handler):
            logger.error(f"尝试为事件 '{event_name}' 注册一个不可调用的处理器: {handler}")
            return

        # 如果这是第一次为这个事件名注册处理器，先创建一个空列表
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        
        # 将处理器添加到对应事件的监听器列表中 (如果尚未添加)
        if handler not in self._listeners[event_name]:
            self._listeners[event_name].append(handler)
            logger.debug(f"事件 '{event_name}' 已成功注册处理器: {handler.__name__ if hasattr(handler, '__name__') else handler}")
        else:
            logger.warning(f"处理器 {handler.__name__ if hasattr(handler, '__name__') else handler} 已注册到事件 '{event_name}'，不再重复添加。")

    def unregister(self, event_name: str, handler: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        """
        注销一个已注册的事件处理器。

        参数:
            event_name (str): 事件的名称。
            handler (Callable): 要注销的处理器函数或方法。
        """
        if event_name in self._listeners and handler in self._listeners[event_name]:
            self._listeners[event_name].remove(handler)
            logger.debug(f"事件 '{event_name}' 的处理器 '{handler.__name__ if hasattr(handler, '__name__') else handler}' 已被注销。")
            # 如果某个事件的所有监听器都被移除了，可以选择从字典中删除该事件键
            if not self._listeners[event_name]:
                del self._listeners[event_name]
                logger.debug(f"事件 '{event_name}' 已没有活动的监听器，从系统中移除。")
        else:
            logger.warning(f"尝试注销一个未注册或不存在的处理器: 事件='{event_name}', 处理器='{handler.__name__ if hasattr(handler, '__name__') else handler}'")

    def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        发出（或触发/发布）一个事件。
        所有注册监听该事件的处理器都将被调用，并传递事件数据。

        参数:
            event_name (str): 要发出的事件的名称。
            data (Optional[Dict[str, Any]]): 伴随事件一起传递的数据，通常是一个字典。默认为 None。
        """
        if data is None:
            data = {} # 确保 data 总是一个字典，即使没有数据传递
            
        print(f"发出事件 '{event_name}'，数据: {data}")
        
        logger.debug(f"正在发出事件 '{event_name}'，数据: {data}")
        
        # 检查是否有任何处理器监听了这个事件
        if event_name in self._listeners:
            # 为了避免在迭代过程中修改列表（例如，处理器内部又注销了自己），可以复制一份列表
            handlers_to_call = list(self._listeners[event_name])
            for handler in handlers_to_call:
                try:
                    # 调用处理器，并将事件数据作为参数传递
                    handler(data)
                    logger.debug(f"已为事件 '{event_name}' 调用处理器: {handler.__name__ if hasattr(handler, '__name__') else handler}")
                except Exception as e:
                    # 如果某个处理器在执行时出错，记录错误但继续执行其他处理器
                    logger.error(
                        f"调用事件 '{event_name}' 的处理器 '{handler.__name__ if hasattr(handler, '__name__') else handler}' 时发生错误: {e}",
                        exc_info=True # exc_info=True 会记录完整的堆栈跟踪信息
                    )
        else:
            logger.debug(f"事件 '{event_name}' 被发出，但没有注册的监听器。")

# --- 用于直接运行和测试 EventSystem 的主代码块 ---
if __name__ == '__main__':
    # 配置基础日志以便在控制台看到输出
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("--- EventSystem 测试开始 ---")
    event_system = EventSystem()

    # 定义一些示例事件处理器函数
    def on_user_login(data):
        print(f"处理器 on_user_login 收到事件，用户 '{data.get('username')}' 已登录。")

    def on_user_login_notification(data):
        print(f"处理器 on_user_login_notification: 发送登录通知给管理员，用户: {data.get('username')}")

    def on_item_purchased(data):
        print(f"处理器 on_item_purchased: 商品 '{data.get('item_name')}' (数量: {data.get('quantity', 1)}) 已被购买。")
    
    def another_item_handler(data):
        print(f"处理器 another_item_handler: 商品 '{data.get('item_name')}' 的库存需要更新。")

    # 注册处理器
    print("\n--- 注册处理器 ---")
    event_system.register("USER_LOGIN", on_user_login)
    event_system.register("USER_LOGIN", on_user_login_notification) # 同一个事件可以有多个处理器
    event_system.register("ITEM_PURCHASED", on_item_purchased)
    event_system.register("ITEM_PURCHASED", another_item_handler)
    
    # 尝试重复注册
    event_system.register("USER_LOGIN", on_user_login) # 应该会有警告，不会重复添加

    # 发出事件
    print("\n--- 发出事件 ---")
    event_system.emit("USER_LOGIN", {"username": "Alice", "timestamp": time.time()})
    event_system.emit("ITEM_PURCHASED", {"item_name": "魔法药水", "quantity": 3, "price": 10.50})
    event_system.emit("ORDER_SHIPPED", {"order_id": "12345", "carrier": "顺丰"}) # 这个事件没有处理器

    # 注销处理器
    print("\n--- 注销处理器 ---")
    event_system.unregister("USER_LOGIN", on_user_login_notification)
    event_system.unregister("NON_EXISTENT_EVENT", on_user_login) # 尝试注销不存在事件的处理器
    event_system.unregister("USER_LOGIN", on_item_purchased)    # 尝试注销错误事件的处理器

    print("\n--- 再次发出 USER_LOGIN 事件 (一个处理器已被注销) ---")
    event_system.emit("USER_LOGIN", {"username": "Bob"})
    
    # 测试处理器执行出错的情况
    def faulty_handler(data):
        print("Faulty Handler: 我要抛出一个错误！")
        raise ValueError("这是一个来自 faulty_handler 的测试错误")

    print("\n--- 测试错误处理 ---")
    event_system.register("CRITICAL_ERROR", faulty_handler)
    event_system.register("CRITICAL_ERROR", on_user_login) # 另一个正常的处理器
    event_system.emit("CRITICAL_ERROR", {"code": 500}) # faulty_handler 会出错，但 on_user_login 应该仍能执行

    print("\n--- EventSystem 测试结束 ---")