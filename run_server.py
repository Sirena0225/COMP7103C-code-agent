#!/usr/bin/env python3
"""
Flask 网站运行器 - 运行生成的 Flask 网页应用
"""
import os
import sys
import subprocess
import argparse
import signal
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def find_flask_app(project_dir: Path) -> Path | None:
    """
    在项目目录中查找 Flask 应用入口文件
    
    Args:
        project_dir: 项目目录路径
        
    Returns:
        Flask 应用文件路径，如果未找到则返回 None
    """
    # 常见的 Flask 入口文件名
    possible_files = ["app.py", "main.py", "server.py", "run.py", "wsgi.py"]
    
    for filename in possible_files:
        filepath = project_dir / filename
        if filepath.exists():
            # 检查文件是否包含 Flask 应用
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                if "Flask(" in content or "from flask import" in content:
                    return filepath
    
    return None


def find_requirements(project_dir: Path) -> Path | None:
    """
    查找项目依赖文件
    
    Args:
        project_dir: 项目目录路径
        
    Returns:
        requirements.txt 文件路径，如果未找到则返回 None
    """
    requirements_file = project_dir / "requirements.txt"
    if requirements_file.exists():
        return requirements_file
    return None


def install_dependencies(project_dir: Path, use_venv: bool = False) -> bool:
    """
    安装项目依赖
    
    Args:
        project_dir: 项目目录路径
        use_venv: 是否使用虚拟环境
        
    Returns:
        安装是否成功
    """
    requirements_file = find_requirements(project_dir)
    if not requirements_file:
        console.print("[yellow]⚠ 未找到 requirements.txt，跳过依赖安装[/yellow]")
        return True
    
    console.print("[cyan]📦 正在安装项目依赖...[/cyan]")
    
    try:
        if use_venv:
            venv_dir = project_dir / "venv"
            if not venv_dir.exists():
                # 创建虚拟环境
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_dir)],
                    check=True,
                    capture_output=True
                )
            
            # 获取虚拟环境中的 pip
            if sys.platform == "win32":
                pip_path = venv_dir / "Scripts" / "pip"
            else:
                pip_path = venv_dir / "bin" / "pip"
            
            pip_cmd = [str(pip_path)]
        else:
            pip_cmd = [sys.executable, "-m", "pip"]
        
        # 安装依赖
        result = subprocess.run(
            pip_cmd + ["install", "-r", str(requirements_file), "-q"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]✗ 依赖安装失败: {result.stderr}[/red]")
            return False
        
        console.print("[green]✓ 依赖安装成功[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ 依赖安装出错: {e}[/red]")
        return False


def run_flask_server(
    project_dir: Path,
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = True,
    use_venv: bool = False,
    open_browser: bool = True
) -> None:
    """
    运行 Flask 服务器
    
    Args:
        project_dir: 项目目录路径
        host: 服务器主机地址
        port: 服务器端口
        debug: 是否启用调试模式
        use_venv: 是否使用项目虚拟环境
        open_browser: 是否自动打开浏览器
    """
    # 查找 Flask 应用
    app_file = find_flask_app(project_dir)
    if not app_file:
        console.print("[red]✗ 未找到 Flask 应用文件[/red]")
        console.print("[dim]支持的入口文件: app.py, main.py, server.py, run.py, wsgi.py[/dim]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]🚀 启动 Flask 服务器[/bold cyan]\n"
        f"[dim]项目: {project_dir.name}[/dim]\n"
        f"[dim]入口: {app_file.name}[/dim]",
        border_style="cyan"
    ))
    
    # 确定 Python 解释器
    if use_venv:
        venv_dir = project_dir / "venv"
        if sys.platform == "win32":
            python_path = venv_dir / "Scripts" / "python"
        else:
            python_path = venv_dir / "bin" / "python"
        
        if not python_path.exists():
            console.print("[yellow]⚠ 虚拟环境不存在，使用系统 Python[/yellow]")
            python_path = sys.executable
    else:
        python_path = sys.executable
    
    # 设置环境变量
    env = os.environ.copy()
    env["FLASK_APP"] = str(app_file)
    env["FLASK_ENV"] = "development" if debug else "production"
    env["FLASK_DEBUG"] = "1" if debug else "0"
    
    url = f"http://{host}:{port}"
    
    console.print(f"\n[green]✓ 服务器地址: [bold]{url}[/bold][/green]")
    console.print("[dim]按 Ctrl+C 停止服务器[/dim]\n")
    
    # 自动打开浏览器
    if open_browser:
        import webbrowser
        # 延迟打开，等待服务器启动
        import threading
        def open_browser_delayed():
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    # 运行 Flask 服务器
    try:
        process = subprocess.Popen(
            [
                str(python_path), "-m", "flask", "run",
                "--host", host,
                "--port", str(port),
            ],
            cwd=str(project_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 设置信号处理
        def signal_handler(signum, frame):
            console.print("\n[yellow]⚠ 正在停止服务器...[/yellow]")
            process.terminate()
            process.wait(timeout=5)
            console.print("[green]✓ 服务器已停止[/green]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 输出服务器日志
        for line in process.stdout:
            # 格式化输出
            line = line.strip()
            if line:
                if "Running on" in line or "Serving Flask app" in line:
                    console.print(f"[cyan]{line}[/cyan]")
                elif "Error" in line or "error" in line:
                    console.print(f"[red]{line}[/red]")
                elif "WARNING" in line or "Warning" in line:
                    console.print(f"[yellow]{line}[/yellow]")
                else:
                    console.print(f"[dim]{line}[/dim]")
        
        process.wait()
        
    except FileNotFoundError:
        console.print("[red]✗ 未找到 Flask，请确保已安装 Flask[/red]")
        console.print("[dim]运行: pip install flask[/dim]")
    except Exception as e:
        console.print(f"[red]✗ 启动服务器失败: {e}[/red]")


def list_projects(base_dir: Path) -> list[Path]:
    """
    列出所有生成的项目
    
    Args:
        base_dir: 项目基础目录
        
    Returns:
        项目目录列表
    """
    projects = []
    if base_dir.exists():
        for item in base_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # 检查是否是 Flask 项目
                if find_flask_app(item):
                    projects.append(item)
    return projects


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="运行生成的 Flask 网页应用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_server.py                              # 交互式选择项目
  python run_server.py -p arxiv_browser             # 运行指定项目
  python run_server.py -p arxiv_browser --port 8080 # 指定端口
  python run_server.py --list                       # 列出所有项目
        """
    )
    
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="项目名称或路径"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="服务器端口 (默认: 5001)"
    )
    
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="禁用调试模式"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="安装项目依赖"
    )
    
    parser.add_argument(
        "--use-venv",
        action="store_true",
        help="使用项目虚拟环境"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的 Flask 项目"
    )
    
    args = parser.parse_args()
    
    # 获取项目基础目录
    base_dir = Path(__file__).parent / "generated_projects"
    
    # 列出项目
    if args.list:
        console.print("\n[bold]📁 可用的 Flask 项目:[/bold]\n")
        projects = list_projects(base_dir)
        if projects:
            for project in projects:
                app_file = find_flask_app(project)
                console.print(f"  • [cyan]{project.name}[/cyan] ({app_file.name if app_file else 'N/A'})")
        else:
            console.print("  [dim]没有找到 Flask 项目[/dim]")
        console.print()
        return
    
    # 确定项目目录
    if args.project:
        # 检查是否是绝对路径
        project_path = Path(args.project)
        if project_path.is_absolute():
            project_dir = project_path
        else:
            # 检查是否是相对路径
            if (Path.cwd() / args.project).exists():
                project_dir = Path.cwd() / args.project
            else:
                # 尝试在 generated_projects 中查找
                project_dir = base_dir / args.project
    else:
        # 交互式选择
        projects = list_projects(base_dir)
        
        if not projects:
            console.print("[red]✗ 没有找到可用的 Flask 项目[/red]")
            console.print("[dim]请先运行 python run_demo.py 生成项目[/dim]")
            return
        
        if len(projects) == 1:
            project_dir = projects[0]
            console.print(f"[cyan]自动选择项目: {project_dir.name}[/cyan]")
        else:
            console.print("\n[bold]请选择要运行的项目:[/bold]\n")
            for i, project in enumerate(projects, 1):
                console.print(f"  {i}. [cyan]{project.name}[/cyan]")
            
            console.print()
            try:
                choice = input("请输入项目编号 (或按 Enter 选择第一个): ").strip()
                if not choice:
                    choice = "1"
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    project_dir = projects[idx]
                else:
                    console.print("[red]✗ 无效的选择[/red]")
                    return
            except (ValueError, KeyboardInterrupt):
                console.print("\n[yellow]已取消[/yellow]")
                return
    
    # 检查项目目录
    if not project_dir.exists():
        console.print(f"[red]✗ 项目目录不存在: {project_dir}[/red]")
        return
    
    # 安装依赖
    if args.install_deps:
        if not install_dependencies(project_dir, args.use_venv):
            return
    
    # 运行服务器
    run_flask_server(
        project_dir=project_dir,
        host=args.host,
        port=args.port,
        debug=not args.no_debug,
        use_venv=args.use_venv,
        open_browser=not args.no_browser
    )


if __name__ == "__main__":
    main()

