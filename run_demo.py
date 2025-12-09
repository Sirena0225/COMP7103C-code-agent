#!/usr/bin/env python3
"""
演示脚本 - 直接生成 arXiv 论文浏览器项目
"""
import asyncio
import argparse
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


def run_flask_server(project_dir: Path, port: int = 5001, open_browser: bool = True):
    """
    运行生成的 Flask 网页应用
    
    Args:
        project_dir: 项目目录路径
        port: 服务器端口
        open_browser: 是否自动打开浏览器
    """
    from run_server import run_flask_server as _run_server, find_flask_app, install_dependencies
    
    # 检查是否是 Flask 项目
    if not find_flask_app(project_dir):
        console.print("[yellow]⚠ 该项目不是 Flask 网页应用，跳过服务器启动[/yellow]")
        return
    
    # 安装依赖
    install_dependencies(project_dir)
    
    # 运行服务器
    _run_server(
        project_dir=project_dir,
        port=port,
        open_browser=open_browser
    )


ARXIV_REQUIREMENT = """
构建一个 arXiv 论文浏览网页应用，需要具备以下功能：

1. 分类导航：按 arXiv CS 领域分类浏览 (cs.AI, cs.LG, cs.CV, cs.CL, cs.SE 等)
2. 每日论文列表：展示最新论文，包含标题、提交时间、领域标签
3. 论文详情页：包含 PDF 链接、作者与机构、提交日期、一键复制 BibTeX 引用
4. 搜索功能：支持关键词搜索和分类过滤

技术栈：Python Flask, arXiv API, 现代深色主题 UI
"""


async def run_demo(run_server: bool = False, port: int = 5001, open_browser: bool = True):
    """
    运行演示
    
    Args:
        run_server: 是否在生成后运行服务器
        port: 服务器端口
        open_browser: 是否自动打开浏览器
    """
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
    
    if run_server:
        console.print("\n[bold cyan]🚀 启动 Flask 服务器...[/bold cyan]")
        run_flask_server(
            project_dir=output_dir,
            port=port,
            open_browser=open_browser
        )
    else:
        console.print("\n[bold]启动方式:[/bold]")
        console.print(f"  cd {output_dir}")
        console.print("  pip install -r requirements.txt")
        console.print("  python app.py")
        console.print(f"\n然后访问 http://localhost:5001")
        console.print("\n[dim]或使用以下命令直接运行:[/dim]")
        console.print("  python run_server.py -p arxiv_browser")
        console.print("  python run_demo.py --run")
    
    return state


def main():
    """主函数 - 解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="生成 arXiv 论文浏览器演示项目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_demo.py                    # 仅生成项目
  python run_demo.py --run              # 生成并运行服务器
  python run_demo.py --run --port 8080  # 使用自定义端口
        """
    )
    
    parser.add_argument(
        "--run",
        action="store_true",
        help="生成完成后自动运行 Flask 服务器"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Flask 服务器端口 (默认: 5001)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_demo(
        run_server=args.run,
        port=args.port,
        open_browser=not args.no_browser
    ))


if __name__ == "__main__":
    main()

