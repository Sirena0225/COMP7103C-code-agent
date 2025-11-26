"""Base agent class."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging
import json
from datetime import datetime

from models import Task, Message, MessageType
from config import Settings


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_id: str, name: str, settings: Settings):
        """
        初始化智能体
        
        Args:
            agent_id: 智能体唯一标识
            name: 智能体名称
            settings: 系统配置
        """
        self.agent_id = agent_id
        self.name = name
        self.settings = settings
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # 消息队列
        self.message_inbox: List[Message] = []
        self.message_outbox: List[Message] = []
        
        # 状态
        self.is_busy = False
        self.current_task: Optional[Task] = None
        
        # LLM 客户端
        self._llm_client = None
    
    @property
    def llm_client(self):
        """获取 LLM 客户端"""
        if self._llm_client is None:
            self._llm_client = self._create_llm_client()
        return self._llm_client
    
    def _create_llm_client(self):
        """创建 LLM 客户端"""
        if self.settings.llm_provider == "anthropic":
            try:
                from anthropic import Anthropic
                return Anthropic(api_key=self.settings.anthropic_api_key)
            except ImportError:
                self.logger.warning("Anthropic not installed, falling back to OpenAI")
        
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.settings.openai_api_key)
        except ImportError:
            self.logger.error("No LLM client available")
            return None
    
    async def call_llm(self, messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 4096) -> str:
        """
        调用 LLM
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 响应
        """
        if self.llm_client is None:
            # 模拟响应用于测试
            return self._get_mock_response(messages)
        
        try:
            if self.settings.llm_provider == "anthropic":
                # Anthropic API
                response = self.llm_client.messages.create(
                    model=self.settings.anthropic_model,
                    max_tokens=max_tokens,
                    messages=messages,
                    temperature=temperature
                )
                return response.content[0].text
            else:
                # OpenAI API
                response = self.llm_client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return self._get_mock_response(messages)
    
    def _get_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """获取模拟响应（用于测试或无API时）"""
        return "Mock response - LLM not available"
    
    @abstractmethod
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 要执行的任务
            
        Returns:
            任务执行结果
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    def receive_message(self, message: Message):
        """接收消息"""
        self.message_inbox.append(message)
        self.logger.debug(f"Received message from {message.sender}: {message.type}")
    
    def send_message(self, receiver: str, msg_type: MessageType, 
                     content: str, data: Dict[str, Any] = None,
                     task_id: str = None) -> Message:
        """发送消息"""
        message = Message(
            sender=self.agent_id,
            receiver=receiver,
            type=msg_type,
            content=content,
            data=data or {},
            task_id=task_id
        )
        self.message_outbox.append(message)
        self.logger.debug(f"Sent message to {receiver}: {msg_type}")
        return message
    
    def get_pending_messages(self) -> List[Message]:
        """获取待处理消息"""
        return [m for m in self.message_inbox if not m.read]
    
    def mark_message_read(self, message_id: str):
        """标记消息已读"""
        for msg in self.message_inbox:
            if msg.id == message_id:
                msg.read = True
                break
    
    def flush_outbox(self) -> List[Message]:
        """清空发件箱并返回所有消息"""
        messages = self.message_outbox.copy()
        self.message_outbox.clear()
        return messages
    
    def start_task(self, task: Task):
        """开始任务"""
        self.is_busy = True
        self.current_task = task
        task.start()
        task.assigned_agent = self.agent_id
        self.logger.info(f"Started task: {task.name}")
    
    def complete_task(self, output: Dict[str, Any] = None):
        """完成当前任务"""
        if self.current_task:
            self.current_task.complete(output)
            self.logger.info(f"Completed task: {self.current_task.name}")
        self.is_busy = False
        self.current_task = None
    
    def fail_task(self, error: str):
        """标记任务失败"""
        if self.current_task:
            self.current_task.fail(error)
            self.logger.error(f"Task failed: {self.current_task.name} - {error}")
        self.is_busy = False
        self.current_task = None
    
    def log(self, level: str, message: str):
        """记录日志"""
        getattr(self.logger, level.lower())(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "is_busy": self.is_busy,
            "current_task": self.current_task.id if self.current_task else None,
            "inbox_count": len(self.message_inbox),
            "outbox_count": len(self.message_outbox)
        }

