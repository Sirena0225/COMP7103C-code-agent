"""
协调器模块 - 管理任务、通信、状态
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from models import (
    AgentMessage, CodeFile, MessageType, ProjectPlan, 
    ProjectState, ReviewResult, Task, TaskStatus, TaskType
)
from config import Config, default_config

console = Console()


class MessageBus:
    """消息总线 - 智能体间通信"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[AgentMessage] = []
    
    def subscribe(self, agent_id: str, callback: Callable):
        """订阅消息"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)
    
    async def publish(self, message: AgentMessage):
        """发布消息"""
        self.message_history.append(message)
        await self.message_queue.put(message)
        
        # 直接通知接收者
        if message.receiver in self.subscribers:
            for callback in self.subscribers[message.receiver]:
                await callback(message)
        
        # 通知广播接收者
        if "*" in self.subscribers:
            for callback in self.subscribers["*"]:
                await callback(message)
    
    async def get_message(self) -> AgentMessage:
        """获取队列中的消息"""
        return await self.message_queue.get()


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
    
    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
    
    def add_tasks(self, tasks: List[Task]):
        """批量添加任务"""
        for task in tasks:
            self.add_task(task)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Dict = None):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now()
            if result:
                self.tasks[task_id].result = result
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
    
    def get_ready_tasks(self) -> List[Task]:
        """获取可执行任务（依赖已完成）"""
        ready = []
        for task in self.get_pending_tasks():
            dependencies_met = all(
                self.tasks.get(dep_id) and 
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if dependencies_met:
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority)
    
    def get_progress(self) -> float:
        """获取整体进度"""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks) * 100
    
    def display_status(self):
        """显示任务状态表格"""
        table = Table(title="任务状态")
        table.add_column("ID", style="cyan")
        table.add_column("类型", style="magenta")
        table.add_column("标题", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("优先级", style="blue")
        
        for task in self.tasks.values():
            status_color = {
                TaskStatus.PENDING: "white",
                TaskStatus.IN_PROGRESS: "yellow",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.BLOCKED: "orange"
            }.get(task.status, "white")
            
            table.add_row(
                task.id[:8],
                task.type.value,
                task.title[:30],
                f"[{status_color}]{task.status.value}[/]",
                str(task.priority)
            )
        
        console.print(table)


class StateManager:
    """状态管理器"""
    
    def __init__(self):
        self.project_state: Optional[ProjectState] = None
    
    def initialize(self, project_id: str, name: str):
        """初始化项目状态"""
        self.project_state = ProjectState(
            project_id=project_id,
            name=name
        )
    
    def set_plan(self, plan: ProjectPlan):
        """设置项目规划"""
        if self.project_state:
            self.project_state.plan = plan
            self.project_state.current_phase = "development"
    
    def add_file(self, file: CodeFile):
        """添加代码文件"""
        if self.project_state:
            # 更新或添加文件
            existing = next((f for f in self.project_state.files if f.path == file.path), None)
            if existing:
                self.project_state.files.remove(existing)
            self.project_state.files.append(file)
    
    def add_review(self, review: ReviewResult):
        """添加审查结果"""
        if self.project_state:
            self.project_state.reviews.append(review)
    
    def add_message(self, message: AgentMessage):
        """添加消息记录"""
        if self.project_state:
            self.project_state.messages.append(message)
    
    def update_progress(self, progress: float):
        """更新进度"""
        if self.project_state:
            self.project_state.progress = progress
            self.project_state.updated_at = datetime.now()
    
    def set_phase(self, phase: str):
        """设置当前阶段"""
        if self.project_state:
            self.project_state.current_phase = phase
    
    def add_error(self, error: str):
        """记录错误"""
        if self.project_state:
            self.project_state.errors.append(error)
    
    def get_state(self) -> Optional[ProjectState]:
        """获取当前状态"""
        return self.project_state


class Coordinator:
    """协调器 - 核心调度模块"""
    
    def __init__(self, config: Config = None):
        self.config = config or default_config
        self.message_bus = MessageBus()
        self.task_manager = TaskManager()
        self.state_manager = StateManager()
        self.agents: Dict[str, Any] = {}
        self.running = False
    
    def register_agent(self, agent_id: str, agent: Any):
        """注册智能体"""
        self.agents[agent_id] = agent
        # 订阅消息
        self.message_bus.subscribe(agent_id, agent.handle_message)
        console.print(f"[green]✓ 智能体 '{agent_id}' 已注册[/green]")
    
    async def send_message(self, sender: str, receiver: str, 
                          msg_type: MessageType, content: Dict[str, Any],
                          correlation_id: str = None):
        """发送消息"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            sender=sender,
            receiver=receiver,
            content=content,
            correlation_id=correlation_id
        )
        self.state_manager.add_message(message)
        await self.message_bus.publish(message)
        return message
    
    async def assign_task(self, task: Task, agent_id: str):
        """分配任务给智能体"""
        task.assigned_to = agent_id
        task.status = TaskStatus.IN_PROGRESS
        self.task_manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        await self.send_message(
            sender="coordinator",
            receiver=agent_id,
            msg_type=MessageType.TASK_ASSIGNMENT,
            content={"task": task.model_dump()}
        )
    
    async def run_planning_phase(self, requirement: str) -> ProjectPlan:
        """执行规划阶段"""
        console.print("\n[bold blue]📋 阶段 1: 项目规划[/bold blue]")
        
        planner = self.agents.get("planner")
        if not planner:
            raise RuntimeError("规划智能体未注册")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("正在分析需求并制定规划...", total=None)
            plan = await planner.create_plan(requirement)
            progress.remove_task(task)
        
        self.state_manager.set_plan(plan)
        self.task_manager.add_tasks(plan.tasks)
        
        console.print(f"[green]✓ 项目规划完成: {plan.project_name}[/green]")
        console.print(f"  - 技术栈: {plan.tech_stack}")
        console.print(f"  - 任务数: {len(plan.tasks)}")
        
        return plan
    
    async def run_development_phase(self):
        """执行开发阶段"""
        console.print("\n[bold blue]💻 阶段 2: 代码生成[/bold blue]")
        
        coder = self.agents.get("coder")
        if not coder:
            raise RuntimeError("代码生成智能体未注册")
        
        code_tasks = [t for t in self.task_manager.tasks.values() 
                     if t.type == TaskType.CODE_GENERATION]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for i, task in enumerate(code_tasks):
                prog_task = progress.add_task(
                    f"生成代码 ({i+1}/{len(code_tasks)}): {task.title[:30]}...", 
                    total=None
                )
                
                self.task_manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                
                try:
                    files = await coder.generate_code(task, self.state_manager.get_state())
                    for file in files:
                        self.state_manager.add_file(file)
                    
                    self.task_manager.update_task_status(
                        task.id, TaskStatus.COMPLETED,
                        {"files": [f.path for f in files]}
                    )
                except Exception as e:
                    self.task_manager.update_task_status(task.id, TaskStatus.FAILED)
                    self.state_manager.add_error(f"任务 {task.id} 失败: {str(e)}")
                    console.print(f"[red]✗ 任务失败: {e}[/red]")
                
                progress.remove_task(prog_task)
        
        console.print(f"[green]✓ 代码生成完成[/green]")
    
    async def run_review_phase(self):
        """执行审查阶段"""
        console.print("\n[bold blue]🔍 阶段 3: 代码审查[/bold blue]")
        
        reviewer = self.agents.get("reviewer")
        if not reviewer:
            raise RuntimeError("审查智能体未注册")
        
        state = self.state_manager.get_state()
        if not state or not state.files:
            console.print("[yellow]⚠ 没有代码文件需要审查[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            prog_task = progress.add_task("正在审查代码质量...", total=None)
            
            reviews = await reviewer.review_project(state)
            for review in reviews:
                self.state_manager.add_review(review)
            
            progress.remove_task(prog_task)
        
        # 统计审查结果
        passed = sum(1 for r in reviews if r.passed)
        avg_score = sum(r.score for r in reviews) / len(reviews) if reviews else 0
        
        console.print(f"[green]✓ 代码审查完成[/green]")
        console.print(f"  - 通过: {passed}/{len(reviews)}")
        console.print(f"  - 平均分: {avg_score:.1f}/10")
    
    async def run(self, requirement: str, output_dir: str = None) -> ProjectState:
        """运行完整流程"""
        project_id = str(uuid.uuid4())
        output_dir = output_dir or self.config.system.output_dir
        
        console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]       🤖 多智能体代码生成系统启动[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        
        self.state_manager.initialize(project_id, "generated_project")
        self.running = True
        
        try:
            # 阶段 1: 规划
            plan = await self.run_planning_phase(requirement)
            
            # 阶段 2: 开发
            await self.run_development_phase()
            
            # 阶段 3: 审查
            await self.run_review_phase()
            
            # 阶段 4: 输出
            self.state_manager.set_phase("completed")
            state = self.state_manager.get_state()
            
            # 写入文件到输出目录
            await self._write_output(state, output_dir)
            
            console.print("\n[bold green]═══════════════════════════════════════════════════[/bold green]")
            console.print("[bold green]       ✅ 项目生成完成![/bold green]")
            console.print(f"[bold green]       📁 输出目录: {output_dir}[/bold green]")
            console.print("[bold green]═══════════════════════════════════════════════════[/bold green]")
            
            return state
            
        except Exception as e:
            self.state_manager.add_error(str(e))
            console.print(f"\n[bold red]❌ 项目生成失败: {e}[/bold red]")
            raise
        finally:
            self.running = False
    
    async def _write_output(self, state: ProjectState, output_dir: str):
        """将生成的文件写入输出目录"""
        import os
        import aiofiles
        
        for file in state.files:
            file_path = os.path.join(output_dir, file.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(file.content)
        
        console.print(f"[dim]已写入 {len(state.files)} 个文件[/dim]")

