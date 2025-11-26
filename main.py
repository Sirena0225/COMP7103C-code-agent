"""
多智能体代码生成系统 - 主入口
"""
import asyncio
import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from coordinator import Coordinator
from agents import PlannerAgent, CoderAgent, ReviewerAgent
from config import Config, default_config

console = Console()


ARXIV_BROWSER_REQUIREMENT = """
构建一个 arXiv 论文浏览网页应用，需要具备以下功能：

1. **分类导航**
   - 按 arXiv CS 领域分类浏览 (如 cs.AI、cs.TH、cs.SY、cs.LG、cs.CV 等)
   - 显示各分类的中文名称
   - 支持快速切换分类

2. **每日论文列表**
   - 展示最新论文
   - 每篇论文显示：标题（可点击链接）、提交时间、领域标签
   - 作者列表（支持多作者）
   - 摘要预览

3. **论文详情页**
   - PDF 下载链接
   - 作者与机构信息
   - 完整摘要
   - 提交日期和更新日期
   - 一键复制 BibTeX 引用

4. **搜索功能**
   - 支持关键词搜索
   - 可按分类过滤

技术要求：
- 使用 Python Flask 作为后端
- 使用 arXiv API 获取数据
- 现代化的深色主题 UI 设计
- 响应式布局，支持移动端
"""


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="多智能体代码生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--requirement", "-r",
        type=str,
        help="项目需求描述（直接输入或文件路径）"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./generated_projects/arxiv_browser",
        help="输出目录路径"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="运行演示模式，生成 arXiv 论文浏览器"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互式模式"
    )
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "[bold cyan]🤖 多智能体代码生成系统[/bold cyan]\n"
        "[dim]从自然语言描述自动生成完整项目代码[/dim]",
        border_style="cyan"
    ))
    
    # 确定需求
    if args.demo:
        requirement = ARXIV_BROWSER_REQUIREMENT
        console.print("\n[yellow]📋 演示模式: 生成 arXiv 论文浏览器[/yellow]")
    elif args.requirement:
        # 检查是否是文件路径
        if os.path.isfile(args.requirement):
            with open(args.requirement, "r", encoding="utf-8") as f:
                requirement = f.read()
        else:
            requirement = args.requirement
    elif args.interactive:
        console.print("\n[cyan]请输入项目需求描述 (输入 END 结束):[/cyan]")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        requirement = "\n".join(lines)
    else:
        # 默认使用演示需求
        requirement = ARXIV_BROWSER_REQUIREMENT
        console.print("\n[yellow]📋 使用默认需求: 生成 arXiv 论文浏览器[/yellow]")
    
    # 显示需求摘要
    console.print("\n[bold]📝 项目需求:[/bold]")
    console.print(Panel(
        Markdown(requirement[:500] + ("..." if len(requirement) > 500 else "")),
        border_style="blue"
    ))
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化系统
    config = default_config
    coordinator = Coordinator(config)
    
    # 注册智能体
    planner = PlannerAgent(config.agent.planner_llm)
    coder = CoderAgent(config.agent.coder_llm)
    reviewer = ReviewerAgent(config.agent.reviewer_llm)
    
    coordinator.register_agent("planner", planner)
    coordinator.register_agent("coder", coder)
    coordinator.register_agent("reviewer", reviewer)
    
    # 运行生成流程
    try:
        state = await coordinator.run(requirement, str(output_dir))
        
        # 显示最终结果
        console.print("\n[bold green]📊 生成报告[/bold green]")
        console.print(f"  项目名称: {state.plan.project_name if state.plan else 'N/A'}")
        console.print(f"  生成文件: {len(state.files)}")
        console.print(f"  代码审查: {'通过' if all(r.passed for r in state.reviews) else '部分问题'}")
        
        if state.reviews:
            avg_score = sum(r.score for r in state.reviews) / len(state.reviews)
            console.print(f"  平均评分: {avg_score:.1f}/10")
        
        console.print(f"\n[bold]📁 输出目录: {output_dir.absolute()}[/bold]")
        
        # 列出生成的文件
        console.print("\n[dim]生成的文件:[/dim]")
        for file in state.files:
            console.print(f"  - {file.path}")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ 生成失败: {e}[/bold red]")
        raise


def run():
    """同步运行入口"""
    asyncio.run(main())


if __name__ == "__main__":
    run()
