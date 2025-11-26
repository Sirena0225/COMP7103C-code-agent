"""Code generation agent."""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base_agent import BaseAgent
from models import Task, TaskType, TaskStatus, MessageType
from config import Settings
from tools import FileTools, CodeTools


class CoderAgent(BaseAgent):
    """
    代码生成智能体
    
    负责：
    - 根据任务指令编写代码
    - 创建和修改文件
    - 管理项目依赖
    - 代码重构优化
    """
    
    def __init__(self, settings: Settings, file_tools: FileTools):
        super().__init__(
            agent_id="coder",
            name="代码生成智能体",
            settings=settings
        )
        self.file_tools = file_tools
        self.code_tools = CodeTools()
        self.project_path: Optional[Path] = None
    
    def set_project_path(self, path: Path):
        """设置项目路径"""
        self.project_path = path
    
    def get_system_prompt(self) -> str:
        return """你是一个专业的软件开发工程师。你的职责是：

1. 根据任务要求编写高质量代码
2. 遵循最佳实践和设计模式
3. 编写清晰的注释和文档
4. 确保代码可维护和可扩展

代码规范：
- Python: 遵循 PEP 8，使用类型注解
- HTML/CSS: 语义化标签，响应式设计
- JavaScript: ES6+ 语法，模块化

输出格式：
当需要生成代码时，使用以下格式：
```文件路径
代码内容
```

确保代码完整、可运行、无语法错误。"""
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """执行编码任务"""
        self.start_task(task)
        
        try:
            if task.name == "创建项目结构":
                result = await self._create_project_structure(task)
            elif task.name == "创建依赖文件":
                result = await self._create_dependency_files(task)
            elif task.name.startswith("编写"):
                result = await self._write_file(task)
            else:
                result = await self._generic_coding_task(task)
            
            self.complete_task(result)
            return result
            
        except Exception as e:
            self.fail_task(str(e))
            return {"error": str(e)}
    
    async def _create_project_structure(self, task: Task) -> Dict[str, Any]:
        """创建项目结构"""
        project_name = task.input_data.get("project_name", "project")
        directories = task.input_data.get("directories", [])
        
        # 创建项目目录
        self.project_path = self.file_tools.create_project_directory(project_name)
        
        # 创建子目录
        created_dirs = []
        for dir_path in directories:
            full_path = self.file_tools.create_directory(dir_path, self.project_path)
            created_dirs.append(full_path)
        
        return {
            "project_path": str(self.project_path),
            "created_directories": created_dirs
        }
    
    async def _create_dependency_files(self, task: Task) -> Dict[str, Any]:
        """创建依赖文件"""
        dependencies = task.input_data.get("dependencies", {})
        created_files = []
        
        # Python dependencies
        if "python" in dependencies:
            requirements = "\n".join(dependencies["python"])
            file_path = self.file_tools.write_file(
                "requirements.txt", 
                requirements, 
                self.project_path
            )
            created_files.append(file_path)
        
        # NPM dependencies
        if "npm" in dependencies:
            package_json = {
                "name": self.project_path.name if self.project_path else "project",
                "version": "1.0.0",
                "dependencies": {pkg: "latest" for pkg in dependencies["npm"]}
            }
            file_path = self.file_tools.write_file(
                "package.json",
                json.dumps(package_json, indent=2),
                self.project_path
            )
            created_files.append(file_path)
        
        return {"created_files": created_files}
    
    async def _write_file(self, task: Task) -> Dict[str, Any]:
        """编写文件"""
        file_spec = task.input_data.get("file_spec", {})
        project_spec = task.input_data.get("project_spec", {})
        
        file_path = file_spec.get("path", "")
        description = file_spec.get("description", "")
        language = file_spec.get("language", "")
        
        # 生成代码
        code = await self._generate_code(file_path, description, language, project_spec)
        
        # 检查语法
        if language == "python":
            is_valid, error = self.code_tools.check_python_syntax(code)
            if not is_valid:
                # 尝试修复
                code = await self._fix_code(code, error, language)
        
        # 写入文件
        full_path = self.file_tools.write_file(file_path, code, self.project_path)
        
        return {
            "file_path": full_path,
            "code_length": len(code),
            "language": language
        }
    
    async def _generate_code(self, file_path: str, description: str, 
                            language: str, project_spec: Dict) -> str:
        """生成代码"""
        
        # 构建上下文
        context = self._build_context(file_path, project_spec)
        
        prompt = f"""请为以下文件编写代码：

## 文件信息
- 路径: {file_path}
- 语言: {language}
- 描述: {description}

## 项目上下文
{context}

## 要求
1. 代码必须完整可运行
2. 包含必要的导入语句
3. 添加适当的注释
4. 遵循{language}最佳实践

请只输出代码内容，不要添加任何解释或标记。"""

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.call_llm(messages, temperature=self.settings.coder_temperature)
        
        # 清理响应
        code = self._clean_code_response(response, language)
        
        # 如果是模拟响应，使用预设模板
        if "Mock response" in response or not code.strip():
            code = self._get_template_code(file_path, language, project_spec)
        
        return code
    
    def _build_context(self, file_path: str, project_spec: Dict) -> str:
        """构建项目上下文"""
        context_parts = []
        
        # 项目描述
        context_parts.append(f"项目名称: {project_spec.get('name', 'unknown')}")
        context_parts.append(f"项目描述: {project_spec.get('description', '')}")
        
        # 技术栈
        tech_stack = project_spec.get("tech_stack", {})
        if tech_stack:
            context_parts.append(f"技术栈: {json.dumps(tech_stack, ensure_ascii=False)}")
        
        # 相关功能
        features = project_spec.get("features", [])
        if features:
            context_parts.append(f"功能列表: {', '.join(features)}")
        
        # API 端点
        endpoints = project_spec.get("api_endpoints", [])
        if endpoints:
            endpoint_str = "\n".join([f"  - {e.get('method')} {e.get('path')}: {e.get('description')}" for e in endpoints])
            context_parts.append(f"API 端点:\n{endpoint_str}")
        
        return "\n".join(context_parts)
    
    def _clean_code_response(self, response: str, language: str) -> str:
        """清理代码响应"""
        # 移除代码块标记
        code = response.strip()
        
        # 尝试提取代码块
        code_block_pattern = r'```(?:\w+)?\s*([\s\S]*?)```'
        matches = re.findall(code_block_pattern, code)
        if matches:
            code = matches[0]
        
        # 移除可能的文件路径前缀
        lines = code.split('\n')
        if lines and (lines[0].endswith('.py') or lines[0].endswith('.html') or 
                      lines[0].endswith('.css') or lines[0].endswith('.js')):
            lines = lines[1:]
        
        return '\n'.join(lines).strip()
    
    def _get_template_code(self, file_path: str, language: str, project_spec: Dict) -> str:
        """获取预设模板代码"""
        
        templates = {
            "main.py": self._get_main_py_template(project_spec),
            "arxiv_client.py": self._get_arxiv_client_template(),
            "models.py": self._get_models_template(),
            "templates/base.html": self._get_base_html_template(project_spec),
            "templates/index.html": self._get_index_html_template(),
            "templates/category.html": self._get_category_html_template(),
            "templates/paper.html": self._get_paper_html_template(),
            "static/css/style.css": self._get_style_css_template(),
            "static/js/main.js": self._get_main_js_template(),
        }
        
        return templates.get(file_path, f"# {file_path}\n# TODO: Implement this file")
    
    def _get_main_py_template(self, project_spec: Dict) -> str:
        return '''"""arXiv 论文浏览器 - FastAPI 应用"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from arxiv_client import ArxivClient
from models import Paper, Category, CS_CATEGORIES

app = FastAPI(
    title="arXiv 论文浏览器",
    description="浏览和搜索 arXiv CS 领域论文",
    version="1.0.0"
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# arXiv 客户端
arxiv_client = ArxivClient()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页 - 显示分类导航和最新论文"""
    try:
        # 获取最新论文
        papers = await arxiv_client.get_recent_papers(category="cs.*", max_results=20)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "categories": CS_CATEGORIES,
            "papers": papers,
            "current_date": datetime.now().strftime("%Y-%m-%d")
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "categories": CS_CATEGORIES,
            "papers": [],
            "error": str(e),
            "current_date": datetime.now().strftime("%Y-%m-%d")
        })


@app.get("/category/{category}", response_class=HTMLResponse)
async def category_page(request: Request, category: str, page: int = 1):
    """分类页面 - 显示特定分类的论文列表"""
    if category not in [c["id"] for c in CS_CATEGORIES]:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    try:
        papers = await arxiv_client.get_recent_papers(
            category=category, 
            max_results=30,
            start=(page - 1) * 30
        )
        
        category_info = next((c for c in CS_CATEGORIES if c["id"] == category), None)
        
        return templates.TemplateResponse("category.html", {
            "request": request,
            "category": category_info,
            "categories": CS_CATEGORIES,
            "papers": papers,
            "current_page": page,
            "has_next": len(papers) == 30
        })
    except Exception as e:
        return templates.TemplateResponse("category.html", {
            "request": request,
            "category": {"id": category, "name": category},
            "categories": CS_CATEGORIES,
            "papers": [],
            "error": str(e),
            "current_page": page,
            "has_next": False
        })


@app.get("/paper/{paper_id:path}", response_class=HTMLResponse)
async def paper_detail(request: Request, paper_id: str):
    """论文详情页"""
    try:
        paper = await arxiv_client.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
        
        return templates.TemplateResponse("paper.html", {
            "request": request,
            "paper": paper,
            "categories": CS_CATEGORIES
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers")
async def api_get_papers(
    category: Optional[str] = "cs.*",
    max_results: int = 20,
    start: int = 0
):
    """API: 获取论文列表"""
    try:
        papers = await arxiv_client.get_recent_papers(
            category=category,
            max_results=max_results,
            start=start
        )
        return {"papers": [p.dict() for p in papers]}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/paper/{paper_id:path}/bibtex")
async def api_get_bibtex(paper_id: str):
    """API: 获取论文 BibTeX"""
    try:
        paper = await arxiv_client.get_paper_by_id(paper_id)
        if not paper:
            return JSONResponse(
                status_code=404,
                content={"error": "论文不存在"}
            )
        
        bibtex = paper.generate_bibtex()
        return {"bibtex": bibtex}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    def _get_arxiv_client_template(self) -> str:
        return '''"""arXiv API 客户端"""

import aiohttp
import feedparser
from typing import List, Optional
from datetime import datetime
import re
import asyncio
from urllib.parse import quote

from models import Paper, Author


class ArxivClient:
    """arXiv API 客户端"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_recent_papers(
        self, 
        category: str = "cs.*",
        max_results: int = 20,
        start: int = 0
    ) -> List[Paper]:
        """
        获取最新论文
        
        Args:
            category: arXiv 分类 (如 "cs.AI", "cs.*")
            max_results: 最大返回数量
            start: 起始位置
            
        Returns:
            论文列表
        """
        # 构建查询
        search_query = f"cat:{category}"
        
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        url = f"{self.BASE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                content = await response.text()
                return self._parse_feed(content)
        except Exception as e:
            print(f"Error fetching papers: {e}")
            return []
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        根据 ID 获取论文详情
        
        Args:
            paper_id: 论文 ID (如 "2301.00001")
            
        Returns:
            论文对象或 None
        """
        # 清理 ID
        paper_id = paper_id.replace("arxiv:", "").replace("arXiv:", "")
        
        params = {
            "id_list": paper_id,
            "max_results": 1
        }
        
        url = f"{self.BASE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                content = await response.text()
                papers = self._parse_feed(content)
                return papers[0] if papers else None
        except Exception as e:
            print(f"Error fetching paper: {e}")
            return None
    
    async def search_papers(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 20
    ) -> List[Paper]:
        """
        搜索论文
        
        Args:
            query: 搜索关键词
            category: 限定分类
            max_results: 最大返回数量
            
        Returns:
            论文列表
        """
        search_parts = [f"all:{quote(query)}"]
        if category:
            search_parts.append(f"cat:{category}")
        
        search_query = "+AND+".join(search_parts)
        
        params = {
            "search_query": search_query,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        url = f"{self.BASE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                content = await response.text()
                return self._parse_feed(content)
        except Exception as e:
            print(f"Error searching papers: {e}")
            return []
    
    def _parse_feed(self, content: str) -> List[Paper]:
        """解析 Atom feed"""
        feed = feedparser.parse(content)
        papers = []
        
        for entry in feed.entries:
            try:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
            except Exception as e:
                print(f"Error parsing entry: {e}")
                continue
        
        return papers
    
    def _parse_entry(self, entry) -> Optional[Paper]:
        """解析单个条目"""
        # 提取 ID
        arxiv_id = entry.id.split("/abs/")[-1]
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]
        
        # 提取作者
        authors = []
        for author in entry.get("authors", []):
            name = author.get("name", "Unknown")
            affiliation = ""
            if "arxiv_affiliation" in author:
                affiliation = author["arxiv_affiliation"]
            authors.append(Author(name=name, affiliation=affiliation))
        
        # 提取分类
        categories = []
        for tag in entry.get("tags", []):
            if "term" in tag:
                categories.append(tag["term"])
        
        # 提取日期
        published = entry.get("published", "")
        updated = entry.get("updated", "")
        
        try:
            published_date = datetime.strptime(published[:10], "%Y-%m-%d") if published else None
        except:
            published_date = None
        
        try:
            updated_date = datetime.strptime(updated[:10], "%Y-%m-%d") if updated else None
        except:
            updated_date = None
        
        # 提取链接
        pdf_link = ""
        abstract_link = ""
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_link = link.get("href", "")
            elif link.get("type") == "text/html":
                abstract_link = link.get("href", "")
        
        if not pdf_link and arxiv_id:
            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if not abstract_link and arxiv_id:
            abstract_link = f"https://arxiv.org/abs/{arxiv_id}"
        
        # 清理摘要
        summary = entry.get("summary", "")
        summary = re.sub(r"\\s+", " ", summary).strip()
        
        return Paper(
            arxiv_id=arxiv_id,
            title=entry.get("title", "").replace("\\n", " ").strip(),
            authors=authors,
            abstract=summary,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published_date=published_date,
            updated_date=updated_date,
            pdf_url=pdf_link,
            abstract_url=abstract_link
        )
'''

    def _get_models_template(self) -> str:
        return '''"""数据模型定义"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import re


class Author(BaseModel):
    """作者模型"""
    name: str
    affiliation: str = ""


class Paper(BaseModel):
    """论文模型"""
    arxiv_id: str
    title: str
    authors: List[Author]
    abstract: str
    categories: List[str]
    primary_category: str
    published_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    pdf_url: str
    abstract_url: str
    
    def get_authors_str(self) -> str:
        """获取作者字符串"""
        return ", ".join([a.name for a in self.authors])
    
    def get_first_author(self) -> str:
        """获取第一作者"""
        return self.authors[0].name if self.authors else "Unknown"
    
    def get_formatted_date(self) -> str:
        """获取格式化日期"""
        if self.published_date:
            return self.published_date.strftime("%Y-%m-%d")
        return "Unknown"
    
    def get_category_badges(self) -> List[str]:
        """获取分类标签"""
        return self.categories[:3]  # 最多显示3个
    
    def generate_bibtex(self) -> str:
        """生成 BibTeX 引用"""
        # 生成 cite key
        first_author = self.get_first_author().split()[-1].lower()
        year = self.published_date.year if self.published_date else "2024"
        title_word = re.sub(r"[^a-zA-Z]", "", self.title.split()[0].lower()) if self.title else "paper"
        cite_key = f"{first_author}{year}{title_word}"
        
        # 格式化作者
        authors_bibtex = " and ".join([a.name for a in self.authors])
        
        # 清理标题
        title_clean = self.title.replace("{", "").replace("}", "")
        
        bibtex = f"""@article{{{cite_key},
    title = {{{title_clean}}},
    author = {{{authors_bibtex}}},
    journal = {{arXiv preprint arXiv:{self.arxiv_id}}},
    year = {{{year}}},
    eprint = {{{self.arxiv_id}}},
    archivePrefix = {{arXiv}},
    primaryClass = {{{self.primary_category}}}
}}"""
        return bibtex


class Category(BaseModel):
    """分类模型"""
    id: str
    name: str
    description: str = ""


# CS 分类列表
CS_CATEGORIES = [
    {"id": "cs.AI", "name": "人工智能", "description": "Artificial Intelligence"},
    {"id": "cs.CL", "name": "计算语言学", "description": "Computation and Language"},
    {"id": "cs.CV", "name": "计算机视觉", "description": "Computer Vision and Pattern Recognition"},
    {"id": "cs.LG", "name": "机器学习", "description": "Machine Learning"},
    {"id": "cs.NE", "name": "神经网络", "description": "Neural and Evolutionary Computing"},
    {"id": "cs.RO", "name": "机器人学", "description": "Robotics"},
    {"id": "cs.CR", "name": "密码学与安全", "description": "Cryptography and Security"},
    {"id": "cs.DB", "name": "数据库", "description": "Databases"},
    {"id": "cs.DC", "name": "分布式计算", "description": "Distributed, Parallel, and Cluster Computing"},
    {"id": "cs.DS", "name": "数据结构与算法", "description": "Data Structures and Algorithms"},
    {"id": "cs.GT", "name": "博弈论", "description": "Computer Science and Game Theory"},
    {"id": "cs.HC", "name": "人机交互", "description": "Human-Computer Interaction"},
    {"id": "cs.IR", "name": "信息检索", "description": "Information Retrieval"},
    {"id": "cs.IT", "name": "信息论", "description": "Information Theory"},
    {"id": "cs.LO", "name": "逻辑", "description": "Logic in Computer Science"},
    {"id": "cs.MA", "name": "多智能体系统", "description": "Multiagent Systems"},
    {"id": "cs.NI", "name": "网络与互联网", "description": "Networking and Internet Architecture"},
    {"id": "cs.PL", "name": "程序语言", "description": "Programming Languages"},
    {"id": "cs.SE", "name": "软件工程", "description": "Software Engineering"},
    {"id": "cs.SY", "name": "系统与控制", "description": "Systems and Control"},
    {"id": "cs.TH", "name": "理论计算机", "description": "Computation Theory"},
]
'''

    def _get_base_html_template(self, project_spec: Dict) -> str:
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}arXiv 论文浏览器{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="/" class="logo">
                <span class="logo-icon">📚</span>
                <span class="logo-text">arXiv 论文浏览器</span>
            </a>
            <div class="nav-links">
                <a href="/" class="nav-link">首页</a>
                <div class="dropdown">
                    <button class="dropdown-btn">分类导航 ▼</button>
                    <div class="dropdown-content">
                        {% for cat in categories %}
                        <a href="/category/{{ cat.id }}">{{ cat.id }} - {{ cat.name }}</a>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="main-content">
        <div class="container">
            {% block content %}{% endblock %}
        </div>
    </main>

    <footer class="footer">
        <div class="container">
            <p>数据来源: <a href="https://arxiv.org" target="_blank">arXiv.org</a></p>
            <p>© 2024 arXiv 论文浏览器 | 仅供学术研究使用</p>
        </div>
    </footer>

    <script src="/static/js/main.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
'''

    def _get_index_html_template(self) -> str:
        return '''{% extends "base.html" %}

{% block title %}arXiv 论文浏览器 - 首页{% endblock %}

{% block content %}
<section class="hero">
    <h1>arXiv CS 论文浏览器</h1>
    <p class="hero-subtitle">探索计算机科学领域的最新研究成果</p>
    <p class="date-info">📅 {{ current_date }}</p>
</section>

<section class="categories-section">
    <h2 class="section-title">🏷️ 分类导航</h2>
    <div class="categories-grid">
        {% for cat in categories %}
        <a href="/category/{{ cat.id }}" class="category-card">
            <span class="category-id">{{ cat.id }}</span>
            <span class="category-name">{{ cat.name }}</span>
            <span class="category-desc">{{ cat.description }}</span>
        </a>
        {% endfor %}
    </div>
</section>

<section class="papers-section">
    <h2 class="section-title">📄 最新论文</h2>
    
    {% if error %}
    <div class="error-message">
        <p>⚠️ 获取论文时出错: {{ error }}</p>
        <p>请稍后刷新重试</p>
    </div>
    {% elif papers %}
    <div class="papers-list">
        {% for paper in papers %}
        <article class="paper-card">
            <div class="paper-header">
                <div class="paper-categories">
                    {% for cat in paper.get_category_badges() %}
                    <span class="category-badge">{{ cat }}</span>
                    {% endfor %}
                </div>
                <span class="paper-date">{{ paper.get_formatted_date() }}</span>
            </div>
            <h3 class="paper-title">
                <a href="/paper/{{ paper.arxiv_id }}">{{ paper.title }}</a>
            </h3>
            <p class="paper-authors">{{ paper.get_authors_str() }}</p>
            <p class="paper-abstract">{{ paper.abstract[:300] }}{% if paper.abstract|length > 300 %}...{% endif %}</p>
            <div class="paper-actions">
                <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-primary">📥 PDF</a>
                <a href="/paper/{{ paper.arxiv_id }}" class="btn btn-secondary">详情</a>
            </div>
        </article>
        {% endfor %}
    </div>
    {% else %}
    <div class="empty-message">
        <p>暂无论文数据</p>
    </div>
    {% endif %}
</section>
{% endblock %}
'''

    def _get_category_html_template(self) -> str:
        return '''{% extends "base.html" %}

{% block title %}{{ category.name }} - arXiv 论文浏览器{% endblock %}

{% block content %}
<section class="breadcrumb">
    <a href="/">首页</a> / <span>{{ category.id }} - {{ category.name }}</span>
</section>

<section class="category-header">
    <h1>{{ category.id }}</h1>
    <p class="category-full-name">{{ category.name }}</p>
    <p class="category-description">{{ category.description }}</p>
</section>

<section class="papers-section">
    <h2 class="section-title">📄 论文列表</h2>
    
    {% if error %}
    <div class="error-message">
        <p>⚠️ 获取论文时出错: {{ error }}</p>
    </div>
    {% elif papers %}
    <div class="papers-list">
        {% for paper in papers %}
        <article class="paper-card">
            <div class="paper-header">
                <div class="paper-categories">
                    {% for cat in paper.get_category_badges() %}
                    <span class="category-badge {% if cat == category.id %}primary{% endif %}">{{ cat }}</span>
                    {% endfor %}
                </div>
                <span class="paper-date">{{ paper.get_formatted_date() }}</span>
            </div>
            <h3 class="paper-title">
                <a href="/paper/{{ paper.arxiv_id }}">{{ paper.title }}</a>
            </h3>
            <p class="paper-authors">{{ paper.get_authors_str() }}</p>
            <p class="paper-abstract">{{ paper.abstract[:300] }}{% if paper.abstract|length > 300 %}...{% endif %}</p>
            <div class="paper-actions">
                <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-primary">📥 PDF</a>
                <a href="/paper/{{ paper.arxiv_id }}" class="btn btn-secondary">详情</a>
            </div>
        </article>
        {% endfor %}
    </div>
    
    <div class="pagination">
        {% if current_page > 1 %}
        <a href="/category/{{ category.id }}?page={{ current_page - 1 }}" class="btn">← 上一页</a>
        {% endif %}
        <span class="page-info">第 {{ current_page }} 页</span>
        {% if has_next %}
        <a href="/category/{{ category.id }}?page={{ current_page + 1 }}" class="btn">下一页 →</a>
        {% endif %}
    </div>
    {% else %}
    <div class="empty-message">
        <p>该分类暂无论文</p>
    </div>
    {% endif %}
</section>
{% endblock %}
'''

    def _get_paper_html_template(self) -> str:
        return '''{% extends "base.html" %}

{% block title %}{{ paper.title }} - arXiv 论文浏览器{% endblock %}

{% block content %}
<section class="breadcrumb">
    <a href="/">首页</a> / 
    <a href="/category/{{ paper.primary_category }}">{{ paper.primary_category }}</a> / 
    <span>{{ paper.arxiv_id }}</span>
</section>

<article class="paper-detail">
    <header class="paper-detail-header">
        <div class="paper-categories">
            {% for cat in paper.categories %}
            <a href="/category/{{ cat }}" class="category-badge">{{ cat }}</a>
            {% endfor %}
        </div>
        <h1 class="paper-title">{{ paper.title }}</h1>
        <p class="paper-id">arXiv:{{ paper.arxiv_id }}</p>
    </header>
    
    <section class="paper-meta">
        <div class="meta-item">
            <span class="meta-label">📅 提交日期</span>
            <span class="meta-value">{{ paper.get_formatted_date() }}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">🏷️ 主分类</span>
            <span class="meta-value">{{ paper.primary_category }}</span>
        </div>
    </section>
    
    <section class="paper-authors-section">
        <h2>👥 作者</h2>
        <div class="authors-list">
            {% for author in paper.authors %}
            <div class="author-item">
                <span class="author-name">{{ author.name }}</span>
                {% if author.affiliation %}
                <span class="author-affiliation">{{ author.affiliation }}</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </section>
    
    <section class="paper-abstract-section">
        <h2>📝 摘要</h2>
        <p class="abstract-text">{{ paper.abstract }}</p>
    </section>
    
    <section class="paper-actions-section">
        <h2>📎 链接与引用</h2>
        <div class="actions-grid">
            <a href="{{ paper.pdf_url }}" target="_blank" class="action-card">
                <span class="action-icon">📥</span>
                <span class="action-text">下载 PDF</span>
            </a>
            <a href="{{ paper.abstract_url }}" target="_blank" class="action-card">
                <span class="action-icon">🔗</span>
                <span class="action-text">arXiv 页面</span>
            </a>
            <button class="action-card" onclick="copyBibtex()">
                <span class="action-icon">📋</span>
                <span class="action-text">复制 BibTeX</span>
            </button>
        </div>
    </section>
    
    <section class="bibtex-section">
        <h2>📚 BibTeX 引用</h2>
        <div class="bibtex-container">
            <pre id="bibtex-content">{{ paper.generate_bibtex() }}</pre>
            <button class="copy-btn" onclick="copyBibtex()">📋 复制</button>
        </div>
    </section>
</article>
{% endblock %}

{% block scripts %}
<script>
function copyBibtex() {
    const bibtex = document.getElementById('bibtex-content').textContent;
    navigator.clipboard.writeText(bibtex).then(() => {
        showToast('BibTeX 已复制到剪贴板!');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败，请手动选择复制');
    });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 2000);
}
</script>
{% endblock %}
'''

    def _get_style_css_template(self) -> str:
        return '''/* arXiv 论文浏览器样式 */

:root {
    --primary-color: #b31b1b;
    --primary-dark: #8a1515;
    --secondary-color: #1a5276;
    --accent-color: #f39c12;
    --background: #0f0f14;
    --surface: #1a1a24;
    --surface-light: #252532;
    --text-primary: #e8e8e8;
    --text-secondary: #a0a0a0;
    --text-muted: #666;
    --border-color: #333;
    --success-color: #27ae60;
    --error-color: #e74c3c;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.4);
    --radius: 12px;
    --radius-sm: 6px;
    --transition: all 0.3s ease;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--background);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* 导航栏 */
.navbar {
    background: var(--surface);
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
}

.navbar .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 70px;
}

.logo {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: var(--text-primary);
    font-weight: 700;
    font-size: 1.3rem;
}

.logo-icon {
    font-size: 1.8rem;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 30px;
}

.nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition);
    font-weight: 500;
}

.nav-link:hover {
    color: var(--primary-color);
}

/* 下拉菜单 */
.dropdown {
    position: relative;
}

.dropdown-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 1rem;
    cursor: pointer;
    font-family: inherit;
    font-weight: 500;
    transition: var(--transition);
}

.dropdown-btn:hover {
    color: var(--primary-color);
}

.dropdown-content {
    display: none;
    position: absolute;
    top: 100%;
    right: 0;
    background: var(--surface-light);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    min-width: 280px;
    max-height: 400px;
    overflow-y: auto;
    box-shadow: var(--shadow-lg);
    padding: 10px 0;
}

.dropdown:hover .dropdown-content {
    display: block;
}

.dropdown-content a {
    display: block;
    padding: 10px 20px;
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition);
    font-size: 0.9rem;
}

.dropdown-content a:hover {
    background: var(--surface);
    color: var(--primary-color);
}

/* 主内容 */
.main-content {
    flex: 1;
    padding: 40px 0;
}

/* Hero 区域 */
.hero {
    text-align: center;
    padding: 60px 0;
    background: linear-gradient(135deg, var(--surface) 0%, var(--surface-light) 100%);
    border-radius: var(--radius);
    margin-bottom: 50px;
    border: 1px solid var(--border-color);
}

.hero h1 {
    font-size: 2.8rem;
    font-weight: 700;
    margin-bottom: 15px;
    background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    color: var(--text-secondary);
    font-size: 1.2rem;
    margin-bottom: 20px;
}

.date-info {
    color: var(--accent-color);
    font-weight: 500;
}

/* 分类区域 */
.section-title {
    font-size: 1.5rem;
    margin-bottom: 25px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
}

.categories-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 15px;
    margin-bottom: 50px;
}

.category-card {
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 20px;
    text-decoration: none;
    color: var(--text-primary);
    transition: var(--transition);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.category-card:hover {
    border-color: var(--primary-color);
    transform: translateY(-3px);
    box-shadow: var(--shadow);
}

.category-id {
    font-family: 'JetBrains Mono', monospace;
    color: var(--primary-color);
    font-weight: 600;
    font-size: 0.9rem;
}

.category-name {
    font-weight: 500;
}

.category-desc {
    color: var(--text-muted);
    font-size: 0.85rem;
}

/* 论文列表 */
.papers-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.paper-card {
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 25px;
    transition: var(--transition);
}

.paper-card:hover {
    border-color: var(--primary-color);
    box-shadow: var(--shadow);
}

.paper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.paper-categories {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.category-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    padding: 4px 10px;
    background: var(--surface-light);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    color: var(--secondary-color);
    text-decoration: none;
    transition: var(--transition);
}

.category-badge:hover,
.category-badge.primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: white;
}

.paper-date {
    color: var(--text-muted);
    font-size: 0.9rem;
}

.paper-title {
    font-size: 1.2rem;
    margin-bottom: 10px;
    line-height: 1.4;
}

.paper-title a {
    color: var(--text-primary);
    text-decoration: none;
    transition: var(--transition);
}

.paper-title a:hover {
    color: var(--primary-color);
}

.paper-authors {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 12px;
}

.paper-abstract {
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.7;
    margin-bottom: 20px;
}

.paper-actions {
    display: flex;
    gap: 12px;
}

/* 按钮 */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 18px;
    border-radius: var(--radius-sm);
    text-decoration: none;
    font-weight: 500;
    font-size: 0.9rem;
    transition: var(--transition);
    cursor: pointer;
    border: none;
    font-family: inherit;
}

.btn-primary {
    background: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-secondary {
    background: var(--surface-light);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

.btn-secondary:hover {
    background: var(--surface);
    border-color: var(--primary-color);
}

/* 论文详情页 */
.breadcrumb {
    margin-bottom: 30px;
    color: var(--text-muted);
}

.breadcrumb a {
    color: var(--text-secondary);
    text-decoration: none;
}

.breadcrumb a:hover {
    color: var(--primary-color);
}

.paper-detail {
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 40px;
}

.paper-detail-header {
    margin-bottom: 30px;
    padding-bottom: 30px;
    border-bottom: 1px solid var(--border-color);
}

.paper-detail-header .paper-title {
    font-size: 1.8rem;
    margin: 20px 0 15px;
}

.paper-id {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-muted);
}

.paper-meta {
    display: flex;
    gap: 40px;
    margin-bottom: 30px;
}

.meta-item {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.meta-label {
    color: var(--text-muted);
    font-size: 0.9rem;
}

.meta-value {
    color: var(--text-primary);
    font-weight: 500;
}

.paper-authors-section,
.paper-abstract-section,
.paper-actions-section,
.bibtex-section {
    margin-bottom: 35px;
}

.paper-authors-section h2,
.paper-abstract-section h2,
.paper-actions-section h2,
.bibtex-section h2 {
    font-size: 1.2rem;
    margin-bottom: 20px;
    color: var(--text-primary);
}

.authors-list {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
}

.author-item {
    background: var(--surface-light);
    padding: 12px 18px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
}

.author-name {
    font-weight: 500;
    display: block;
}

.author-affiliation {
    color: var(--text-muted);
    font-size: 0.85rem;
    display: block;
    margin-top: 3px;
}

.abstract-text {
    color: var(--text-secondary);
    line-height: 1.8;
    text-align: justify;
}

.actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
}

.action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 25px;
    background: var(--surface-light);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    text-decoration: none;
    color: var(--text-primary);
    transition: var(--transition);
    cursor: pointer;
    font-family: inherit;
    font-size: 1rem;
}

.action-card:hover {
    border-color: var(--primary-color);
    transform: translateY(-3px);
}

.action-icon {
    font-size: 2rem;
}

/* BibTeX 区域 */
.bibtex-container {
    position: relative;
    background: var(--surface-light);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 20px;
}

.bibtex-container pre {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre-wrap;
    color: var(--text-secondary);
}

.copy-btn {
    position: absolute;
    top: 15px;
    right: 15px;
    padding: 8px 15px;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-family: inherit;
    transition: var(--transition);
}

.copy-btn:hover {
    background: var(--primary-dark);
}

/* 分页 */
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-top: 40px;
}

.page-info {
    color: var(--text-muted);
}

/* 消息提示 */
.error-message,
.empty-message {
    text-align: center;
    padding: 60px 20px;
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
}

.error-message {
    color: var(--error-color);
}

.empty-message {
    color: var(--text-muted);
}

/* Toast 通知 */
.toast {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: var(--success-color);
    color: white;
    padding: 15px 30px;
    border-radius: var(--radius);
    font-weight: 500;
    opacity: 0;
    transition: all 0.3s ease;
    z-index: 1000;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
}

/* 页脚 */
.footer {
    background: var(--surface);
    border-top: 1px solid var(--border-color);
    padding: 30px 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.footer a {
    color: var(--primary-color);
    text-decoration: none;
}

.footer p {
    margin: 5px 0;
}

/* 分类页头部 */
.category-header {
    text-align: center;
    padding: 40px;
    background: var(--surface);
    border-radius: var(--radius);
    margin-bottom: 40px;
    border: 1px solid var(--border-color);
}

.category-header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    color: var(--primary-color);
    margin-bottom: 10px;
}

.category-full-name {
    font-size: 1.5rem;
    margin-bottom: 10px;
}

.category-description {
    color: var(--text-muted);
}

/* 响应式设计 */
@media (max-width: 768px) {
    .hero h1 {
        font-size: 2rem;
    }
    
    .categories-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .paper-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
    
    .paper-detail {
        padding: 25px;
    }
    
    .paper-meta {
        flex-direction: column;
        gap: 20px;
    }
    
    .navbar .container {
        flex-direction: column;
        height: auto;
        padding: 15px 20px;
        gap: 15px;
    }
    
    .nav-links {
        width: 100%;
        justify-content: center;
    }
}

@media (max-width: 480px) {
    .categories-grid {
        grid-template-columns: 1fr;
    }
    
    .actions-grid {
        grid-template-columns: 1fr;
    }
}
'''

    def _get_main_js_template(self) -> str:
        return '''/**
 * arXiv 论文浏览器 - 前端脚本
 */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('arXiv Paper Browser loaded');
    
    // 初始化功能
    initializeDropdowns();
    initializeSearch();
    initializeCopyButtons();
});

/**
 * 初始化下拉菜单
 */
function initializeDropdowns() {
    // 点击外部关闭下拉菜单
    document.addEventListener('click', function(e) {
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                const content = dropdown.querySelector('.dropdown-content');
                if (content) {
                    content.style.display = 'none';
                }
            }
        });
    });
}

/**
 * 初始化搜索功能
 */
function initializeSearch() {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch(this.value);
            }
        });
    }
}

/**
 * 执行搜索
 */
function performSearch(query) {
    if (query.trim()) {
        window.location.href = `/search?q=${encodeURIComponent(query)}`;
    }
}

/**
 * 初始化复制按钮
 */
function initializeCopyButtons() {
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-copy');
            const content = document.getElementById(targetId);
            if (content) {
                copyToClipboard(content.textContent);
            }
        });
    });
}

/**
 * 复制文本到剪贴板
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败，请手动复制');
    });
}

/**
 * 显示提示消息
 */
function showToast(message, duration = 2000) {
    // 检查是否已有toast
    let toast = document.querySelector('.toast');
    if (toast) {
        document.body.removeChild(toast);
    }
    
    // 创建新toast
    toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 隐藏动画
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, duration);
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * 截断文本
 */
function truncateText(text, maxLength = 200) {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
}

/**
 * 加载更多论文（无限滚动）
 */
let isLoading = false;
let currentPage = 1;

function loadMorePapers() {
    if (isLoading) return;
    
    const papersList = document.querySelector('.papers-list');
    if (!papersList) return;
    
    // 检查是否滚动到底部
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    
    if (scrollTop + windowHeight >= documentHeight - 100) {
        isLoading = true;
        currentPage++;
        
        // 显示加载指示器
        const loader = document.createElement('div');
        loader.className = 'loading-indicator';
        loader.innerHTML = '加载中...';
        papersList.appendChild(loader);
        
        // 获取当前分类
        const categoryMatch = window.location.pathname.match(/\\/category\\/(.+)/);
        const category = categoryMatch ? categoryMatch[1] : 'cs.*';
        
        // 请求更多论文
        fetch(`/api/papers?category=${category}&start=${(currentPage - 1) * 30}&max_results=30`)
            .then(response => response.json())
            .then(data => {
                loader.remove();
                if (data.papers && data.papers.length > 0) {
                    data.papers.forEach(paper => {
                        const card = createPaperCard(paper);
                        papersList.appendChild(card);
                    });
                }
                isLoading = false;
            })
            .catch(err => {
                console.error('加载失败:', err);
                loader.textContent = '加载失败';
                isLoading = false;
            });
    }
}

/**
 * 创建论文卡片
 */
function createPaperCard(paper) {
    const article = document.createElement('article');
    article.className = 'paper-card';
    
    const categories = paper.categories.slice(0, 3).map(cat => 
        `<span class="category-badge">${cat}</span>`
    ).join('');
    
    article.innerHTML = `
        <div class="paper-header">
            <div class="paper-categories">${categories}</div>
            <span class="paper-date">${formatDate(paper.published_date)}</span>
        </div>
        <h3 class="paper-title">
            <a href="/paper/${paper.arxiv_id}">${paper.title}</a>
        </h3>
        <p class="paper-authors">${paper.authors.map(a => a.name).join(', ')}</p>
        <p class="paper-abstract">${truncateText(paper.abstract, 300)}</p>
        <div class="paper-actions">
            <a href="${paper.pdf_url}" target="_blank" class="btn btn-primary">📥 PDF</a>
            <a href="/paper/${paper.arxiv_id}" class="btn btn-secondary">详情</a>
        </div>
    `;
    
    return article;
}

// 监听滚动事件（可选，用于无限滚动）
// window.addEventListener('scroll', loadMorePapers);
'''

    async def _fix_code(self, code: str, error: str, language: str) -> str:
        """尝试修复代码错误"""
        prompt = f"""请修复以下 {language} 代码中的错误：

## 错误信息
{error}

## 代码
```{language}
{code}
```

请只输出修复后的完整代码，不要其他解释。"""

        messages = [
            {"role": "system", "content": "你是一个代码修复专家。只输出修复后的代码，不要其他内容。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.call_llm(messages, temperature=0.2)
        return self._clean_code_response(response, language)
    
    async def _generic_coding_task(self, task: Task) -> Dict[str, Any]:
        """处理通用编码任务"""
        return {
            "status": "completed",
            "task_name": task.name
        }

