"""
配置文件 - 多智能体协作系统
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "qwen"  # openai, anthropic
    model: str = "qwen-turbo"
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("YOUR_API_KEY"))
    temperature: float = 0.7
    max_tokens: int = 4096

@dataclass 
class AgentConfig:
    """智能体配置"""
    planner_llm: LLMConfig = field(default_factory=LLMConfig)
    coder_llm: LLMConfig = field(default_factory=LLMConfig)
    reviewer_llm: LLMConfig = field(default_factory=LLMConfig)

@dataclass
class SystemConfig:
    """系统配置"""
    output_dir: str = "./generated_projects"
    max_retries: int = 3
    timeout: int = 300
    log_level: str = "INFO"
    enable_testing: bool = True
    enable_linting: bool = True

@dataclass
class Config:
    """主配置类"""
    agent: AgentConfig = field(default_factory=AgentConfig)
    system: SystemConfig = field(default_factory=SystemConfig)

# 默认配置实例
default_config = Config()

