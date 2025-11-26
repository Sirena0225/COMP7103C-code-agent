#!/usr/bin/env python3
"""
演示脚本 - 直接生成 arXiv 论文浏览器项目
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

from coordinator import Coordinator
from agents import PlannerAgent, CoderAgent, ReviewerAgent
from config import default_config

console = Console()


ARXIV_REQUIREMENT = """
构建一个 arXiv 论文浏览网页应用，需要具备以下功能：

1. 分类导航：按 arXiv CS 领域分类浏览 (cs.AI, cs.LG, cs.CV, cs.CL, cs.SE 等)
2. 每日论文列表：展示最新论文，包含标题、提交时间、领域标签
3. 论文详情页：包含 PDF 链接、作者与机构、提交日期、一键复制 BibTeX 引用
4. 搜索功能：支持关键词搜索和分类过滤

技术栈：Python Flask, arXiv API, 现代深色主题 UI
"""


async def run_demo():
    """运行演示"""
    console.print(Panel.fit(
        "[bold cyan]🚀 多智能体代码生成系统演示[/bold cyan]\n"
        "[dim]正在生成 arXiv 论文浏览器项目...[/dim]",
        border_style="cyan"
    ))
    
    # 输出目录
    output_dir = Path(__file__).parent / "generated_projects" / "arxiv_browser"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化协调器
    coordinator = Coordinator(default_config)
    
    # 注册智能体
    coordinator.register_agent("planner", PlannerAgent())
    coordinator.register_agent("coder", CoderAgent())
    coordinator.register_agent("reviewer", ReviewerAgent())
    
    # 运行生成
    state = await coordinator.run(ARXIV_REQUIREMENT, str(output_dir))
    
    # 显示结果
    console.print("\n" + "="*60)
    console.print("[bold green]✅ 项目生成完成![/bold green]")
    console.print(f"📁 项目位置: {output_dir.absolute()}")
    console.print("\n[bold]启动方式:[/bold]")
    console.print(f"  cd {output_dir}")
    console.print("  pip install -r requirements.txt")
    console.print("  python app.py")
    console.print("\n然后访问 http://localhost:5000")
    
    return state


if __name__ == "__main__":
    asyncio.run(run_demo())

