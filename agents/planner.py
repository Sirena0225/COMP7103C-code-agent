"""
项目规划智能体 - 设计架构、拆解需求、制定任务清单与技术依赖
"""
from typing import Any, Dict, List
from datetime import datetime

from .base import BaseAgent
from models import ProjectPlan, Task, TaskStatus, TaskType
from config import LLMConfig


PLANNER_SYSTEM_PROMPT = """你是一个专业的软件架构师和项目规划专家。你的任务是：

1. 分析用户的自然语言需求描述
2. 设计合适的软件架构
3. 选择最佳的技术栈
4. 将需求拆解为具体的开发任务
5. 确定任务之间的依赖关系

请以 JSON 格式返回项目规划，包含以下字段：

{
    "project_name": "项目名称",
    "description": "项目描述",
    "architecture": {
        "type": "应用类型",
        "components": ["组件列表"],
        "patterns": ["设计模式"]
    },
    "tech_stack": {
        "frontend": ["前端技术"],
        "backend": ["后端技术"],
        "database": ["数据库"],
        "tools": ["工具"]
    },
    "file_structure": ["文件路径列表"],
    "tasks": [
        {
            "id": "唯一ID",
            "type": "code_generation",
            "title": "任务标题",
            "description": "详细描述",
            "priority": 1-10,
            "dependencies": ["依赖的任务ID"]
        }
    ]
}

确保：
- 任务拆分粒度适中，每个任务专注于一个具体功能
- 依赖关系准确反映任务执行顺序
- 技术栈选择现代且稳定
- 文件结构清晰合理
"""


class PlannerAgent(BaseAgent):
    """项目规划智能体"""
    
    def __init__(self, llm_config: LLMConfig = None):
        super().__init__("planner", llm_config)
    
    async def process(self, input_data: Any) -> Any:
        """处理输入并返回规划"""
        if isinstance(input_data, str):
            return await self.create_plan(input_data)
        return None
    
    async def create_plan(self, requirement: str) -> ProjectPlan:
        """根据需求创建项目规划"""
        prompt = f"""请根据以下需求创建详细的项目规划：

{requirement}

请确保规划完整、可执行，并包含所有必要的技术细节。
"""
        
        response = await self.call_llm(prompt, PLANNER_SYSTEM_PROMPT)
        plan_data = self.parse_json_response(response)
        
        # 转换任务格式
        tasks = []
        for task_data in plan_data.get("tasks", []):
            task = Task(
                id=task_data.get("id", f"task-{len(tasks)+1}"),
                type=TaskType(task_data.get("type", "code_generation")),
                title=task_data.get("title", ""),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", 5),
                dependencies=task_data.get("dependencies", []),
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        # 构建项目规划
        plan = ProjectPlan(
            project_name=plan_data.get("project_name", "generated_project"),
            description=plan_data.get("description", ""),
            architecture=plan_data.get("architecture", {}),
            tech_stack=plan_data.get("tech_stack", {}),
            file_structure=plan_data.get("file_structure", []),
            tasks=tasks,
            dependencies=self._extract_dependencies(tasks)
        )
        
        return plan
    
    def _extract_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """提取任务依赖关系图"""
        dependencies = {}
        for task in tasks:
            dependencies[task.id] = task.dependencies
        return dependencies
    
    async def refine_plan(self, plan: ProjectPlan, feedback: str) -> ProjectPlan:
        """根据反馈优化规划"""
        prompt = f"""当前项目规划：
{plan.model_dump_json(indent=2)}

收到以下反馈：
{feedback}

请根据反馈优化项目规划，返回更新后的完整规划（JSON格式）。
"""
        
        response = await self.call_llm(prompt, PLANNER_SYSTEM_PROMPT)
        plan_data = self.parse_json_response(response)
        
        # 重新构建规划
        tasks = []
        for task_data in plan_data.get("tasks", []):
            task = Task(
                id=task_data.get("id", f"task-{len(tasks)+1}"),
                type=TaskType(task_data.get("type", "code_generation")),
                title=task_data.get("title", ""),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", 5),
                dependencies=task_data.get("dependencies", []),
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        return ProjectPlan(
            project_name=plan_data.get("project_name", plan.project_name),
            description=plan_data.get("description", plan.description),
            architecture=plan_data.get("architecture", plan.architecture),
            tech_stack=plan_data.get("tech_stack", plan.tech_stack),
            file_structure=plan_data.get("file_structure", plan.file_structure),
            tasks=tasks,
            dependencies=self._extract_dependencies(tasks)
        )
    
    async def estimate_effort(self, plan: ProjectPlan) -> Dict[str, Any]:
        """估算项目工作量"""
        prompt = f"""请分析以下项目规划，估算开发工作量：

项目名称：{plan.project_name}
描述：{plan.description}
技术栈：{plan.tech_stack}
任务数量：{len(plan.tasks)}

请以 JSON 格式返回估算结果，包含：
- total_hours: 预计总工时
- complexity: 复杂度 (low/medium/high)
- risk_factors: 风险因素列表
- recommendations: 建议列表
"""
        
        response = await self.call_llm(prompt, PLANNER_SYSTEM_PROMPT)
        return self.parse_json_response(response)

