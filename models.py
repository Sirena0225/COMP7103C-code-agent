"""
数据模型定义 - 多智能体协作系统
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    """任务类型枚举"""
    ARCHITECTURE = "architecture"
    REQUIREMENT = "requirement"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"


class MessageType(str, Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    CODE_SUBMISSION = "code_submission"
    REVIEW_RESULT = "review_result"
    ERROR_REPORT = "error_report"
    COMPLETION = "completion"


class Task(BaseModel):
    """任务模型"""
    id: str
    type: TaskType
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10, 1 最高
    dependencies: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


class ProjectPlan(BaseModel):
    """项目规划模型"""
    project_name: str
    description: str
    architecture: Dict[str, Any]
    tech_stack: Dict[str, List[str]]
    file_structure: List[str]
    tasks: List[Task]
    dependencies: Dict[str, List[str]]
    created_at: datetime = Field(default_factory=datetime.now)


class CodeFile(BaseModel):
    """代码文件模型"""
    path: str
    content: str
    language: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class ReviewResult(BaseModel):
    """代码审查结果模型"""
    file_path: str
    passed: bool
    score: float = 0.0  # 0-10
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None


class AgentMessage(BaseModel):
    """智能体间消息模型"""
    id: str
    type: MessageType
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


class ProjectState(BaseModel):
    """项目状态模型"""
    project_id: str
    name: str
    status: str = "initializing"
    plan: Optional[ProjectPlan] = None
    files: List[CodeFile] = Field(default_factory=list)
    reviews: List[ReviewResult] = Field(default_factory=list)
    messages: List[AgentMessage] = Field(default_factory=list)
    current_phase: str = "planning"
    progress: float = 0.0
    errors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

