#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
火山引擎语音识别(ASR)客户端模块
"""

import os
import json
import time
import uuid
import base64
import logging
import threading
import hmac
import hashlib
import websocket
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# 导入音频处理工具
from utils.audio_utils import AudioRecorder, AudioPlayer

logger = logging.getLogger(__name__)

class ASRClient:
    """
    火山引擎语音识别客户端，用于实时语音识别
    """
    
    def __init__(self, config: Any, on_result: Optional[Callable[[str], None]] = None):
        """
        初始化ASR客户端
        
        Args:
            config: 配置管理器实例
            on_result: 识别结果回调函数
        """
        self.config = config
        self.on_result = on_result
        
        # 从配置加载ASR设置
        model_config = self.config.get_model_config
        
        self.app_id = model_config('model_config.asr.app_id', '')
        self.access_key = model_config('model_config.asr.api_key', '')
        self.secret_key = model_config('model_config.asr.api_secret', '')
        self.language = model_config('model_config.asr.language', 'zh')
        self.format = model_config('model_config.asr.format', 'wav')
        self.sample_rate = model_config('model_config.asr.sample_rate', 16000)
        
        # 语音检测参数
        self.silence_threshold = model_config('voice_detection.silence_threshold', 500)
        self.min_silence_duration = model_config('voice_detection.min_silence_duration', 1.0)
        self.speech_timeout = model_config('voice_detection.speech_timeout', 5.0)
        self.chunk_size = model_config('voice_detection.chunk_size', 1024)
        
        # 临时音频文件目录
        self.temp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'temp'
        )
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # WebSocket对象
        self.ws = None
        self.ws_thread = None
        
        # 录音状态
        self.is_recording = False
        self.audio_recorder = None
        
        # 识别状态
        self.recognition_id = ""
        self.current_result = ""
        self.is_final_result = False
        
        logger.info("ASR客户端已初始化")
    
    def start_listening(self) -> bool:
        """
        开始监听用户语音输入
        
        Returns:
            是否成功启动监听
        """
        if self.is_recording:
            logger.warning("已经在录音中")
            return False
        
        # 检查API凭据
        if not self._check_credentials():
            logger.error("ASR API凭据未设置")
            return False
            
        # 生成识别ID
        self.recognition_id = f"asr_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 重置状态
        self.current_result = ""
        self.is_final_result = False
        
        # 开始录音
        self.audio_recorder = AudioRecorder(
            temp_dir=self.temp_dir,
            silence_threshold=self.silence_threshold,
            min_silence_duration=self.min_silence_duration,
            sample_rate=self.sample_rate
        )
        
        # 启动WebSocket连接
        self._connect_websocket()
        
        # 启动录音
        self.is_recording = True
        self.audio_recorder.start_recording(self._on_audio_chunk)
        
        logger.info("开始监听用户语音输入")
        return True
    
    def stop_listening(self) -> str:
        """
        停止监听并获取最终识别结果
        
        Returns:
            最终识别结果文本
        """
        if not self.is_recording:
            return self.current_result
        
        # 停止录音
        if self.audio_recorder:
            self.audio_recorder.stop_recording()
        
        # 等待最终识别结果
        timeout = time.time() + 2.0  # 2秒超时
        while not self.is_final_result and time.time() < timeout:
            time.sleep(0.1)
        
        # 关闭WebSocket连接
        self._close_websocket()
        
        self.is_recording = False
        logger.info(f"停止监听，最终结果: '{self.current_result}'")
        
        return self.current_result
    
    def _check_credentials(self) -> bool:
        """
        检查API凭据是否已设置
        
        Returns:
            凭据是否有效
        """
        return bool(self.app_id and self.access_key and self.secret_key)
    
    def _connect_websocket(self) -> None:
        """建立WebSocket连接"""
        try:
            # 构建连接URL和认证信息
            host = "asr.volces.com"
            path = f"/v1/{self.app_id}/asr"
            url = f"wss://{host}{path}"
            
            # 计算认证签名
            timestamp = int(time.time())
            nonce = uuid.uuid4().hex
            
            string_to_sign = f"{timestamp}{nonce}"
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 设置认证头
            headers = {
                "Host": host,
                "X-Timestamp": str(timestamp),
                "X-Nonce": nonce,
                "X-Access-Key": self.access_key,
                "X-Signature": signature,
                "Content-Type": "application/json"
            }
            
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                url,
                header=headers,
                on_open=self._on_ws_open,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close
            )
            
            # 在独立线程中运行WebSocket
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            logger.debug("ASR WebSocket连接已启动")
        except Exception as e:
            logger.error(f"建立WebSocket连接失败: {e}", exc_info=True)
            self.ws = None
    
    def _close_websocket(self) -> None:
        """关闭WebSocket连接"""
        if self.ws:
            try:
                # 发送结束标志
                end_message = {
                    "type": "end"
                }
                self.ws.send(json.dumps(end_message))
                
                # 关闭连接
                self.ws.close()
                
                # 等待线程结束
                if self.ws_thread and self.ws_thread.is_alive():
                    self.ws_thread.join(timeout=1.0)
                
                logger.debug("ASR WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"关闭WebSocket连接出错: {e}", exc_info=True)
            finally:
                self.ws = None
                self.ws_thread = None
    
    def _on_ws_open(self, ws) -> None:
        """
        WebSocket连接打开回调
        
        Args:
            ws: WebSocket对象
        """
        try:
            # 发送语音识别会话初始化消息
            init_message = {
                "type": "start",
                "data": {
                    "asr_params": {
                        "sample_rate": self.sample_rate,
                        "format": self.format,
                        "language": self.language
                    },
                    "enable_vad": True,
                    "enable_punctuation": True,
                    "enable_intermediate_result": True
                }
            }
            ws.send(json.dumps(init_message))
            logger.debug("ASR会话已初始化")
        except Exception as e:
            logger.error(f"发送WebSocket初始化消息出错: {e}", exc_info=True)
    
    def _on_ws_message(self, ws, message) -> None:
        """
        WebSocket消息接收回调
        
        Args:
            ws: WebSocket对象
            message: 接收到的消息
        """
        try:
            response = json.loads(message)
            
            if response.get("type") == "response":
                result = response.get("data", {}).get("text", "")
                is_final = response.get("data", {}).get("is_final", False)
                
                # 更新当前结果
                self.current_result = result
                self.is_final_result = is_final
                
                logger.debug(f"ASR结果: '{result}' (最终: {is_final})")
                
                # 调用结果回调
                if self.on_result and (is_final or (len(result) > 3 and not result.endswith('...'))):
                    self.on_result(result)
        except Exception as e:
            logger.error(f"处理WebSocket消息出错: {e}", exc_info=True)
    
    def _on_ws_error(self, ws, error) -> None:
        """
        WebSocket错误回调
        
        Args:
            ws: WebSocket对象
            error: 错误信息
        """
        logger.error(f"WebSocket错误: {error}")
    
    def _on_ws_close(self, ws, close_status_code, close_reason) -> None:
        """
        WebSocket关闭回调
        
        Args:
            ws: WebSocket对象
            close_status_code: 关闭状态码
            close_reason: 关闭原因
        """
        logger.debug(f"WebSocket已关闭: {close_status_code} {close_reason}")
        self.is_final_result = True
    
    def _on_audio_chunk(self, chunk) -> None:
        """
        音频数据块回调
        
        Args:
            chunk: 音频数据块
        """
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                # 将音频数据编码为base64
                audio_base64 = base64.b64encode(chunk).decode('utf-8')
                
                # 发送音频数据
                audio_message = {
                    "type": "binary",
                    "data": {
                        "audio": audio_base64
                    }
                }
                self.ws.send(json.dumps(audio_message))
            except Exception as e:
                logger.error(f"发送音频数据出错: {e}", exc_info=True)
    
    def test_recognition(self, audio_file: str) -> str:
        """
        使用指定的音频文件测试识别功能
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            识别结果文本
        """
        if not os.path.exists(audio_file):
            logger.error(f"测试音频文件不存在: {audio_file}")
            return "错误：音频文件不存在"
            
        # 重置状态
        self.current_result = ""
        self.is_final_result = False
        
        # 启动WebSocket连接
        self._connect_websocket()
        
        # 读取音频文件
        try:
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # 分块发送音频数据
            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                self._on_audio_chunk(chunk)
                time.sleep(0.1)  # 模拟实时录音速度
            
            # 发送结束标志
            if self.ws:
                end_message = {
                    "type": "end"
                }
                self.ws.send(json.dumps(end_message))
            
            # 等待最终识别结果
            timeout = time.time() + 5.0  # 5秒超时
            while not self.is_final_result and time.time() < timeout:
                time.sleep(0.1)
                
            # 关闭WebSocket连接
            self._close_websocket()
            
            logger.info(f"测试识别结果: '{self.current_result}'")
            return self.current_result
            
        except Exception as e:
            logger.error(f"测试识别出错: {e}", exc_info=True)
            self._close_websocket()
            return f"错误：{str(e)}"
