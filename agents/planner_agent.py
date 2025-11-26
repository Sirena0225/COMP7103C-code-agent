"""Project planning agent."""

import json
from typing import Dict, Any, List, Optional
import re

from .base_agent import BaseAgent
from models import Task, TaskType, TaskStatus, ProjectSpec, FileSpec
from config import Settings


class PlannerAgent(BaseAgent):
    """
    项目规划智能体
    
    负责：
    - 分析需求
    - 设计架构
    - 拆解任务
    - 制定技术依赖
    """
    
    def __init__(self, settings: Settings):
        super().__init__(
            agent_id="planner",
            name="项目规划智能体",
            settings=settings
        )
    
    def get_system_prompt(self) -> str:
        return """你是一个专业的软件架构师和项目规划师。你的职责是：

1. 分析用户需求，理解核心功能和技术要求
2. 设计清晰的系统架构
3. 将需求拆解为可执行的开发任务
4. 确定技术栈和依赖
5. 规划文件结构

你需要输出结构化的 JSON 格式规划结果，包含：
- project_name: 项目名称
- description: 项目描述
- tech_stack: 技术栈
- architecture: 架构设计
- files: 需要创建的文件列表
- dependencies: 项目依赖
- features: 功能列表
- tasks: 任务清单

请确保规划全面、合理、可执行。"""
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """执行规划任务"""
        self.start_task(task)
        
        try:
            requirements = task.input_data.get("requirements", "")
            
            # 调用 LLM 进行规划
            project_spec = await self.analyze_and_plan(requirements)
            
            # 生成任务列表
            tasks = self.generate_tasks(project_spec)
            
            result = {
                "project_spec": project_spec.model_dump(),
                "tasks": [t.model_dump() for t in tasks]
            }
            
            self.complete_task(result)
            return result
            
        except Exception as e:
            self.fail_task(str(e))
            return {"error": str(e)}
    
    async def analyze_and_plan(self, requirements: str) -> ProjectSpec:
        """分析需求并生成项目规格"""
        
        prompt = f"""请分析以下项目需求，并生成详细的项目规划。

## 需求描述
{requirements}

## 输出要求
请以 JSON 格式输出项目规划，包含以下字段：

```json
{{
    "name": "项目名称（英文，小写，用横线分隔）",
    "description": "项目描述",
    "tech_stack": {{
        "backend": "后端技术",
        "frontend": "前端技术",
        "database": "数据库（如果需要）",
        "other": "其他技术"
    }},
    "architecture": {{
        "type": "架构类型（如 monolithic, microservices, serverless）",
        "components": ["组件列表"],
        "data_flow": "数据流描述"
    }},
    "files": [
        {{
            "path": "文件路径",
            "description": "文件描述",
            "language": "编程语言",
            "dependencies": ["依赖的其他文件路径"]
        }}
    ],
    "dependencies": {{
        "python": ["Python 包列表"],
        "npm": ["NPM 包列表（如果需要）"]
    }},
    "features": ["功能列表"],
    "api_endpoints": [
        {{
            "method": "HTTP 方法",
            "path": "路径",
            "description": "描述"
        }}
    ],
    "pages": [
        {{
            "name": "页面名称",
            "path": "路由路径",
            "description": "描述",
            "components": ["组件列表"]
        }}
    ]
}}
```

请确保规划完整且可执行。只输出 JSON，不要其他内容。"""

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.call_llm(messages, temperature=self.settings.planner_temperature)
        
        # 解析 JSON
        project_data = self._parse_json_response(response)
        
        # 如果解析失败，使用默认模板
        if not project_data:
            project_data = self._get_default_project_spec(requirements)
        
        # 构建 FileSpec 列表
        files = []
        for f in project_data.get("files", []):
            files.append(FileSpec(
                path=f.get("path", ""),
                description=f.get("description", ""),
                language=f.get("language"),
                dependencies=f.get("dependencies", [])
            ))
        
        return ProjectSpec(
            name=project_data.get("name", "project"),
            description=project_data.get("description", ""),
            tech_stack=project_data.get("tech_stack", {}),
            architecture=project_data.get("architecture", {}),
            files=files,
            dependencies=project_data.get("dependencies", {}),
            features=project_data.get("features", []),
            api_endpoints=project_data.get("api_endpoints", []),
            pages=project_data.get("pages", [])
        )
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试找到 JSON 对象
        brace_match = re.search(r'\{[\s\S]*\}', response)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _get_default_project_spec(self, requirements: str) -> Dict[str, Any]:
        """获取默认项目规格（arXiv 论文浏览器）"""
        return {
            "name": "arxiv-paper-browser",
            "description": "arXiv 论文浏览网站，支持分类导航、每日论文列表和论文详情查看",
            "tech_stack": {
                "backend": "FastAPI",
                "frontend": "HTML/CSS/JavaScript (Vanilla)",
                "database": "None (API-based)",
                "other": "arXiv API, Jinja2 Templates"
            },
            "architecture": {
                "type": "monolithic",
                "components": ["API Server", "Templates", "Static Files", "arXiv Client"],
                "data_flow": "User -> FastAPI -> arXiv API -> Templates -> User"
            },
            "files": [
                {"path": "main.py", "description": "FastAPI 应用入口", "language": "python", "dependencies": []},
                {"path": "arxiv_client.py", "description": "arXiv API 客户端", "language": "python", "dependencies": []},
                {"path": "models.py", "description": "数据模型", "language": "python", "dependencies": []},
                {"path": "templates/base.html", "description": "HTML 基础模板", "language": "html", "dependencies": []},
                {"path": "templates/index.html", "description": "首页模板", "language": "html", "dependencies": ["templates/base.html"]},
                {"path": "templates/category.html", "description": "分类页面模板", "language": "html", "dependencies": ["templates/base.html"]},
                {"path": "templates/paper.html", "description": "论文详情模板", "language": "html", "dependencies": ["templates/base.html"]},
                {"path": "static/css/style.css", "description": "样式文件", "language": "css", "dependencies": []},
                {"path": "static/js/main.js", "description": "前端脚本", "language": "javascript", "dependencies": []},
                {"path": "requirements.txt", "description": "Python 依赖", "language": "text", "dependencies": []}
            ],
            "dependencies": {
                "python": ["fastapi", "uvicorn", "jinja2", "aiohttp", "feedparser", "python-dateutil"]
            },
            "features": [
                "按 arXiv CS 领域分类浏览",
                "每日论文列表展示",
                "论文详情页面",
                "PDF 链接",
                "作者与机构信息",
                "BibTeX 一键复制"
            ],
            "api_endpoints": [
                {"method": "GET", "path": "/", "description": "首页"},
                {"method": "GET", "path": "/category/{category}", "description": "分类页面"},
                {"method": "GET", "path": "/paper/{paper_id}", "description": "论文详情"},
                {"method": "GET", "path": "/api/papers", "description": "获取论文列表 API"},
                {"method": "GET", "path": "/api/paper/{paper_id}/bibtex", "description": "获取 BibTeX"}
            ],
            "pages": [
                {"name": "首页", "path": "/", "description": "展示分类导航和最新论文", "components": ["分类导航", "论文卡片"]},
                {"name": "分类页", "path": "/category/{category}", "description": "特定分类的论文列表", "components": ["面包屑", "论文列表", "分页"]},
                {"name": "详情页", "path": "/paper/{paper_id}", "description": "论文详细信息", "components": ["论文信息", "作者列表", "BibTeX"]}
            ]
        }
    
    def generate_tasks(self, spec: ProjectSpec) -> List[Task]:
        """根据项目规格生成任务列表"""
        tasks = []
        
        # 1. 创建项目结构任务
        tasks.append(Task(
            name="创建项目结构",
            description="创建项目目录结构和基础文件",
            type=TaskType.CODING,
            priority=10,
            input_data={
                "project_name": spec.name,
                "directories": self._extract_directories(spec.files)
            }
        ))
        
        # 2. 创建依赖文件任务
        tasks.append(Task(
            name="创建依赖文件",
            description="创建 requirements.txt 等依赖配置文件",
            type=TaskType.CODING,
            priority=9,
            dependencies=[tasks[0].id],
            input_data={
                "dependencies": spec.dependencies
            }
        ))
        
        # 3. 为每个文件创建编码任务
        file_tasks = {}
        for file_spec in spec.files:
            if file_spec.path in ["requirements.txt", "package.json"]:
                continue  # 已在依赖任务中处理
            
            task = Task(
                name=f"编写 {file_spec.path}",
                description=file_spec.description,
                type=TaskType.CODING,
                priority=7,
                input_data={
                    "file_spec": file_spec.model_dump(),
                    "project_spec": spec.model_dump()
                },
                related_files=[file_spec.path]
            )
            
            # 添加依赖
            task.dependencies.append(tasks[1].id)  # 依赖于依赖文件任务
            for dep in file_spec.dependencies:
                if dep in file_tasks:
                    task.dependencies.append(file_tasks[dep].id)
            
            file_tasks[file_spec.path] = task
            tasks.append(task)
        
        # 4. 代码审查任务
        code_task_ids = [t.id for t in tasks if t.type == TaskType.CODING]
        tasks.append(Task(
            name="代码审查",
            description="审查所有生成的代码，检查质量和功能",
            type=TaskType.REVIEW,
            priority=5,
            dependencies=code_task_ids,
            input_data={
                "review_type": "full",
                "project_spec": spec.model_dump()
            }
        ))
        
        # 5. 测试任务
        tasks.append(Task(
            name="功能测试",
            description="测试项目功能是否符合需求",
            type=TaskType.TESTING,
            priority=4,
            dependencies=[tasks[-1].id],  # 依赖于审查任务
            input_data={
                "test_type": "functional",
                "features": spec.features
            }
        ))
        
        return tasks
    
    def _extract_directories(self, files: List[FileSpec]) -> List[str]:
        """从文件列表提取需要创建的目录"""
        dirs = set()
        for f in files:
            parts = f.path.split('/')
            if len(parts) > 1:
                for i in range(1, len(parts)):
                    dirs.add('/'.join(parts[:i]))
        return sorted(list(dirs))

