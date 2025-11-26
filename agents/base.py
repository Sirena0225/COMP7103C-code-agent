"""
基础智能体类
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json

from models import AgentMessage, Task
from config import LLMConfig


class LLMClient:
    """LLM 客户端封装"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """懒加载客户端"""
        if self._client is None:
            # 如果没有 API key，直接返回 None 使用模拟模式
            if not self.config.api_key:
                return None
            
            if self.config.provider == "openai":
                try:
                    from openai import AsyncOpenAI
                    self._client = AsyncOpenAI(api_key=self.config.api_key)
                except (ImportError, Exception):
                    self._client = None
            elif self.config.provider == "anthropic":
                try:
                    from anthropic import AsyncAnthropic
                    self._client = AsyncAnthropic(api_key=self.config.api_key)
                except (ImportError, Exception):
                    self._client = None
        return self._client
    
    async def complete(self, messages: List[Dict[str, str]], 
                      system: str = None) -> str:
        """调用 LLM 生成回复"""
        client = self._get_client()
        
        if client is None:
            # 如果没有配置 API，使用模拟响应
            return await self._mock_complete(messages, system)
        
        try:
            if self.config.provider == "openai":
                full_messages = []
                if system:
                    full_messages.append({"role": "system", "content": system})
                full_messages.extend(messages)
                
                response = await client.chat.completions.create(
                    model=self.config.model,
                    messages=full_messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                return response.choices[0].message.content
                
            elif self.config.provider == "anthropic":
                response = await client.messages.create(
                    model=self.config.model,
                    system=system or "",
                    messages=messages,
                    max_tokens=self.config.max_tokens
                )
                return response.content[0].text
                
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return await self._mock_complete(messages, system)
    
    async def _mock_complete(self, messages: List[Dict[str, str]], 
                            system: str = None) -> str:
        """模拟 LLM 响应（用于测试和演示）"""
        await asyncio.sleep(0.5)  # 模拟延迟
        
        last_message = messages[-1]["content"] if messages else ""
        
        # 根据上下文返回模拟响应
        if "项目规划" in str(system) or "架构" in last_message:
            return self._mock_planning_response(last_message)
        elif "代码生成" in str(system) or "实现" in last_message:
            return self._mock_code_response(last_message)
        elif "审查" in str(system) or "测试" in last_message:
            return self._mock_review_response()
        
        return "模拟响应"
    
    def _mock_planning_response(self, requirement: str) -> str:
        """模拟规划响应"""
        return json.dumps({
            "project_name": "arxiv-browser",
            "description": "arXiv 论文浏览网页应用",
            "architecture": {
                "type": "web_application",
                "frontend": "HTML/CSS/JavaScript",
                "backend": "Python Flask",
                "data_source": "arXiv API"
            },
            "tech_stack": {
                "frontend": ["HTML5", "CSS3", "JavaScript", "Tailwind CSS"],
                "backend": ["Python", "Flask", "Jinja2"],
                "api": ["arXiv API", "feedparser"]
            },
            "file_structure": [
                "app.py",
                "templates/base.html",
                "templates/index.html",
                "templates/category.html",
                "templates/paper.html",
                "static/css/style.css",
                "static/js/main.js",
                "arxiv_client.py",
                "requirements.txt"
            ],
            "tasks": [
                {
                    "id": "task-1",
                    "type": "code_generation",
                    "title": "创建 arXiv API 客户端",
                    "description": "实现与 arXiv API 交互的客户端模块",
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "id": "task-2",
                    "type": "code_generation",
                    "title": "创建 Flask 应用主程序",
                    "description": "实现 Flask 后端路由和视图",
                    "priority": 2,
                    "dependencies": ["task-1"]
                },
                {
                    "id": "task-3",
                    "type": "code_generation",
                    "title": "创建 HTML 模板",
                    "description": "实现所有页面模板",
                    "priority": 3,
                    "dependencies": ["task-2"]
                },
                {
                    "id": "task-4",
                    "type": "code_generation",
                    "title": "创建样式和脚本",
                    "description": "实现 CSS 样式和 JavaScript 交互",
                    "priority": 4,
                    "dependencies": ["task-3"]
                },
                {
                    "id": "task-5",
                    "type": "code_generation",
                    "title": "创建依赖配置",
                    "description": "创建 requirements.txt 和 README",
                    "priority": 5,
                    "dependencies": []
                }
            ]
        }, ensure_ascii=False)
    
    def _mock_code_response(self, context: str) -> str:
        """模拟代码生成响应"""
        return json.dumps({
            "files": [
                {
                    "path": "example.py",
                    "content": "# Generated code\nprint('Hello World')",
                    "language": "python"
                }
            ]
        }, ensure_ascii=False)
    
    def _mock_review_response(self) -> str:
        """模拟审查响应"""
        return json.dumps({
            "passed": True,
            "score": 8.5,
            "issues": [],
            "suggestions": ["代码结构清晰", "建议添加更多注释"]
        }, ensure_ascii=False)


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_id: str, llm_config: LLMConfig = None):
        self.agent_id = agent_id
        self.llm_config = llm_config or LLMConfig()
        self.llm = LLMClient(self.llm_config)
        self.message_queue: asyncio.Queue = asyncio.Queue()
    
    async def handle_message(self, message: AgentMessage):
        """处理接收到的消息"""
        await self.message_queue.put(message)
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """处理任务的核心逻辑"""
        pass
    
    async def call_llm(self, prompt: str, system: str = None) -> str:
        """调用 LLM"""
        messages = [{"role": "user", "content": prompt}]
        return await self.llm.complete(messages, system)
    
    def parse_json_response(self, response: str) -> Dict:
        """解析 JSON 响应"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试找到第一个 { 和最后一个 }
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                return json.loads(response[start:end+1])
            
            raise ValueError(f"无法解析 JSON 响应: {response[:200]}...")

