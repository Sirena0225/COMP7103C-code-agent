"""
代码生成智能体 - 根据任务指令编写代码
"""
from typing import Any, Dict, List, Optional
import json
import re

from .base import BaseAgent
from models import CodeFile, ProjectState, Task
from config import LLMConfig


CODER_SYSTEM_PROMPT = """你是一个专业的全栈开发工程师，擅长编写高质量、可维护的代码。

你的任务是根据给定的任务描述和项目上下文，生成完整的代码文件。

要求：
1. 代码必须完整、可运行，不要使用占位符或省略号
2. 遵循最佳实践和代码规范
3. 添加必要的注释说明
4. 考虑错误处理和边界情况
5. 确保代码风格一致

请以 JSON 格式返回生成的文件列表：

{
    "files": [
        {
            "path": "相对路径/文件名",
            "content": "完整的文件内容",
            "language": "编程语言",
            "description": "文件功能描述"
        }
    ]
}

确保：
- path 使用正斜杠分隔
- content 包含完整的可执行代码
- 不要在代码中使用 ... 或 TODO 占位符
"""


class CoderAgent(BaseAgent):
    """代码生成智能体"""
    
    def __init__(self, llm_config: LLMConfig = None):
        super().__init__("coder", llm_config)
        self.templates = CodeTemplates()
    
    async def process(self, input_data: Any) -> Any:
        """处理输入"""
        return None
    
    async def generate_code(self, task: Task, 
                           project_state: ProjectState) -> List[CodeFile]:
        """根据任务生成代码"""
        context = self._build_context(task, project_state)
        
        prompt = f"""请根据以下任务生成代码：

任务标题：{task.title}
任务描述：{task.description}

项目上下文：
{context}

请生成完整、可运行的代码文件。
"""
        
        response = await self.call_llm(prompt, CODER_SYSTEM_PROMPT)
        
        try:
            data = self.parse_json_response(response)
            files = []
            
            for file_data in data.get("files", []):
                file = CodeFile(
                    path=file_data.get("path", ""),
                    content=file_data.get("content", ""),
                    language=file_data.get("language", ""),
                    description=file_data.get("description", "")
                )
                files.append(file)
            
            return files
            
        except Exception as e:
            # 如果解析失败，尝试使用模板生成
            return await self._generate_from_template(task, project_state)
    
    def _build_context(self, task: Task, project_state: ProjectState) -> str:
        """构建项目上下文"""
        context_parts = []
        
        if project_state.plan:
            context_parts.append(f"项目名称: {project_state.plan.project_name}")
            context_parts.append(f"项目描述: {project_state.plan.description}")
            context_parts.append(f"技术栈: {json.dumps(project_state.plan.tech_stack, ensure_ascii=False)}")
            context_parts.append(f"文件结构: {project_state.plan.file_structure}")
        
        # 添加已生成的相关文件信息
        if project_state.files:
            context_parts.append("\n已生成的文件:")
            for file in project_state.files[:5]:  # 只显示前5个
                context_parts.append(f"  - {file.path}: {file.description}")
        
        return "\n".join(context_parts)
    
    async def _generate_from_template(self, task: Task, 
                                      project_state: ProjectState) -> List[CodeFile]:
        """使用模板生成代码（回退方案）"""
        files = []
        
        # 根据任务类型和项目规划选择模板
        if project_state.plan:
            plan = project_state.plan
            
            # arXiv 论文浏览器项目的特定模板
            if "arxiv" in plan.project_name.lower() or "论文" in plan.description:
                return await self._generate_arxiv_project(task, plan)
        
        return files
    
    async def _generate_arxiv_project(self, task: Task, plan) -> List[CodeFile]:
        """生成 arXiv 论文浏览器项目代码"""
        files = []
        
        task_title_lower = task.title.lower()
        
        if "api" in task_title_lower or "客户端" in task.title:
            files.append(self.templates.arxiv_client())
        
        elif "flask" in task_title_lower or "主程序" in task.title or "app" in task_title_lower:
            files.append(self.templates.flask_app())
        
        elif "模板" in task.title or "html" in task_title_lower:
            files.extend(self.templates.html_templates())
        
        elif "样式" in task.title or "css" in task_title_lower or "脚本" in task.title:
            files.extend(self.templates.static_files())
        
        elif "依赖" in task.title or "requirements" in task_title_lower:
            files.extend(self.templates.project_files())
        
        return files
    
    async def fix_code(self, file: CodeFile, issues: List[Dict]) -> CodeFile:
        """修复代码问题"""
        prompt = f"""请修复以下代码中的问题：

文件路径：{file.path}
语言：{file.language}

当前代码：
```{file.language}
{file.content}
```

发现的问题：
{json.dumps(issues, ensure_ascii=False, indent=2)}

请返回修复后的完整代码（JSON格式）：
{{"content": "修复后的完整代码"}}
"""
        
        response = await self.call_llm(prompt, CODER_SYSTEM_PROMPT)
        data = self.parse_json_response(response)
        
        return CodeFile(
            path=file.path,
            content=data.get("content", file.content),
            language=file.language,
            description=file.description
        )


class CodeTemplates:
    """代码模板库"""
    
    def arxiv_client(self) -> CodeFile:
        """arXiv API 客户端"""
        content = '''"""
arXiv API 客户端 - 获取论文数据
"""
import feedparser
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import html
import re


@dataclass
class Paper:
    """论文数据类"""
    id: str
    title: str
    summary: str
    authors: List[str]
    affiliations: List[str]
    categories: List[str]
    primary_category: str
    published: datetime
    updated: datetime
    pdf_url: str
    abs_url: str
    
    @property
    def bibtex(self) -> str:
        """生成 BibTeX 引用"""
        # 提取 arXiv ID
        arxiv_id = self.id.split("/")[-1]
        # 第一作者姓氏
        first_author = self.authors[0].split()[-1] if self.authors else "Unknown"
        year = self.published.year
        
        # 清理标题
        title_clean = self.title.replace("\\n", " ").strip()
        
        return f"""@article{{{first_author.lower()}{year}arxiv,
    title={{{title_clean}}},
    author={{{" and ".join(self.authors)}}},
    journal={{arXiv preprint arXiv:{arxiv_id}}},
    year={{{year}}},
    url={{{self.abs_url}}}
}}"""


class ArxivClient:
    """arXiv API 客户端"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    # CS 子领域分类
    CS_CATEGORIES = {
        "cs.AI": "人工智能",
        "cs.CL": "计算与语言",
        "cs.CV": "计算机视觉",
        "cs.LG": "机器学习",
        "cs.NE": "神经与进化计算",
        "cs.RO": "机器人学",
        "cs.SE": "软件工程",
        "cs.PL": "编程语言",
        "cs.DB": "数据库",
        "cs.DS": "数据结构与算法",
        "cs.IR": "信息检索",
        "cs.CR": "密码学与安全",
        "cs.DC": "分布式计算",
        "cs.NI": "网络与互联网",
        "cs.SY": "系统与控制",
        "cs.TH": "计算理论",
        "cs.HC": "人机交互",
        "cs.CG": "计算几何",
        "cs.GT": "博弈论",
        "cs.MA": "多智能体系统",
    }
    
    def __init__(self):
        self.session = requests.Session()
    
    def search(self, query: str = "", category: str = "cs", 
               max_results: int = 50, start: int = 0,
               sort_by: str = "submittedDate",
               sort_order: str = "descending") -> List[Paper]:
        """
        搜索论文
        
        Args:
            query: 搜索关键词
            category: 分类 (如 cs.AI)
            max_results: 最大结果数
            start: 起始位置
            sort_by: 排序字段 (submittedDate, relevance, lastUpdatedDate)
            sort_order: 排序顺序 (ascending, descending)
        """
        # 构建查询
        search_query = f"cat:{category}"
        if query:
            search_query = f"({query}) AND {search_query}"
        
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        response = self.session.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        return self._parse_feed(response.text)
    
    def get_recent_papers(self, category: str = "cs", 
                          days: int = 1, 
                          max_results: int = 100) -> List[Paper]:
        """获取最近几天的论文"""
        papers = self.search(
            category=category,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending"
        )
        
        # 过滤时间范围
        cutoff = datetime.now() - timedelta(days=days)
        return [p for p in papers if p.published >= cutoff]
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """根据 ID 获取论文详情"""
        params = {
            "id_list": arxiv_id,
            "max_results": 1
        }
        
        response = self.session.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        papers = self._parse_feed(response.text)
        return papers[0] if papers else None
    
    def get_categories(self) -> Dict[str, str]:
        """获取所有 CS 分类"""
        return self.CS_CATEGORIES.copy()
    
    def _parse_feed(self, xml_content: str) -> List[Paper]:
        """解析 Atom feed"""
        feed = feedparser.parse(xml_content)
        papers = []
        
        for entry in feed.entries:
            try:
                paper = self._parse_entry(entry)
                papers.append(paper)
            except Exception as e:
                print(f"解析论文失败: {e}")
                continue
        
        return papers
    
    def _parse_entry(self, entry) -> Paper:
        """解析单个论文条目"""
        # 提取 ID
        paper_id = entry.id
        
        # 提取标题（清理换行和多余空格）
        title = html.unescape(entry.title)
        title = re.sub(r"\\s+", " ", title).strip()
        
        # 提取摘要
        summary = html.unescape(entry.summary)
        summary = re.sub(r"\\s+", " ", summary).strip()
        
        # 提取作者和机构
        authors = []
        affiliations = []
        for author in entry.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)
            affil = author.get("arxiv_affiliation", "")
            if affil and affil not in affiliations:
                affiliations.append(affil)
        
        # 提取分类
        categories = [tag.term for tag in entry.get("tags", [])]
        primary_category = entry.get("arxiv_primary_category", {}).get("term", "")
        if not primary_category and categories:
            primary_category = categories[0]
        
        # 提取时间
        published = datetime(*entry.published_parsed[:6])
        updated = datetime(*entry.updated_parsed[:6])
        
        # 提取链接
        pdf_url = ""
        abs_url = entry.link
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
                break
        
        if not pdf_url:
            pdf_url = abs_url.replace("/abs/", "/pdf/") + ".pdf"
        
        return Paper(
            id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            affiliations=affiliations,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            pdf_url=pdf_url,
            abs_url=abs_url
        )


# 单例客户端
arxiv_client = ArxivClient()


def get_client() -> ArxivClient:
    """获取 arXiv 客户端实例"""
    return arxiv_client
'''
        return CodeFile(
            path="arxiv_client.py",
            content=content,
            language="python",
            description="arXiv API 客户端，提供论文搜索和获取功能"
        )
    
    def flask_app(self) -> CodeFile:
        """Flask 应用主程序"""
        content = '''"""
arXiv 论文浏览器 - Flask 应用
"""
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os

from arxiv_client import ArxivClient, get_client

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)

# arXiv 客户端
client = get_client()


@app.route("/")
def index():
    """首页 - 显示分类导航和最新论文"""
    categories = client.get_categories()
    
    # 获取热门分类的最新论文
    featured_papers = client.search(category="cs.AI", max_results=10)
    
    return render_template(
        "index.html",
        categories=categories,
        featured_papers=featured_papers,
        current_date=datetime.now().strftime("%Y年%m月%d日")
    )


@app.route("/category/<category_id>")
def category(category_id: str):
    """分类页面 - 显示特定分类的论文列表"""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    start = (page - 1) * per_page
    
    categories = client.get_categories()
    category_name = categories.get(category_id, category_id)
    
    papers = client.search(
        category=category_id,
        max_results=per_page,
        start=start
    )
    
    return render_template(
        "category.html",
        category_id=category_id,
        category_name=category_name,
        categories=categories,
        papers=papers,
        page=page,
        current_date=datetime.now().strftime("%Y年%m月%d日")
    )


@app.route("/paper/<path:paper_id>")
def paper(paper_id: str):
    """论文详情页"""
    # paper_id 可能包含版本号，如 2401.12345v1
    paper_data = client.get_paper_by_id(paper_id)
    
    if not paper_data:
        return render_template("404.html"), 404
    
    categories = client.get_categories()
    
    return render_template(
        "paper.html",
        paper=paper_data,
        categories=categories,
        bibtex=paper_data.bibtex
    )


@app.route("/search")
def search():
    """搜索页面"""
    query = request.args.get("q", "")
    category = request.args.get("category", "cs")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    start = (page - 1) * per_page
    
    categories = client.get_categories()
    papers = []
    
    if query:
        papers = client.search(
            query=query,
            category=category,
            max_results=per_page,
            start=start
        )
    
    return render_template(
        "search.html",
        query=query,
        category=category,
        categories=categories,
        papers=papers,
        page=page
    )


@app.route("/api/papers")
def api_papers():
    """API: 获取论文列表"""
    category = request.args.get("category", "cs")
    max_results = request.args.get("limit", 20, type=int)
    start = request.args.get("offset", 0, type=int)
    
    papers = client.search(
        category=category,
        max_results=max_results,
        start=start
    )
    
    return jsonify({
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "categories": p.categories,
                "published": p.published.isoformat(),
                "pdf_url": p.pdf_url,
                "abs_url": p.abs_url
            }
            for p in papers
        ]
    })


@app.route("/api/paper/<path:paper_id>/bibtex")
def api_bibtex(paper_id: str):
    """API: 获取 BibTeX 引用"""
    paper_data = client.get_paper_by_id(paper_id)
    
    if not paper_data:
        return jsonify({"error": "Paper not found"}), 404
    
    return jsonify({"bibtex": paper_data.bibtex})


@app.template_filter("truncate_text")
def truncate_text(text: str, length: int = 200) -> str:
    """截断文本"""
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


@app.template_filter("format_date")
def format_date(dt: datetime) -> str:
    """格式化日期"""
    return dt.strftime("%Y-%m-%d %H:%M")


@app.template_filter("format_date_short")
def format_date_short(dt: datetime) -> str:
    """格式化短日期"""
    return dt.strftime("%Y-%m-%d")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
'''
        return CodeFile(
            path="app.py",
            content=content,
            language="python",
            description="Flask 主应用，提供路由和视图"
        )
    
    def html_templates(self) -> List[CodeFile]:
        """HTML 模板文件"""
        base_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}arXiv 论文浏览器{% endblock %}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="{{ url_for('index') }}" class="logo">
                <span class="logo-icon">📄</span>
                <span class="logo-text">arXiv 浏览器</span>
            </a>
            <form action="{{ url_for('search') }}" method="get" class="search-form">
                <input type="text" name="q" placeholder="搜索论文..." 
                       value="{{ request.args.get('q', '') }}" class="search-input">
                <button type="submit" class="search-btn">🔍</button>
            </form>
            <div class="nav-links">
                <a href="{{ url_for('index') }}">首页</a>
                <a href="{{ url_for('category', category_id='cs.AI') }}">AI</a>
                <a href="{{ url_for('category', category_id='cs.LG') }}">ML</a>
                <a href="{{ url_for('category', category_id='cs.CV') }}">CV</a>
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

    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>'''

        index_html = '''{% extends "base.html" %}

{% block title %}arXiv 论文浏览器 - 发现最新计算机科学研究{% endblock %}

{% block content %}
<section class="hero">
    <h1>探索最新计算机科学研究</h1>
    <p class="hero-subtitle">{{ current_date }} | 汇集 arXiv 最新论文</p>
</section>

<section class="categories-section">
    <h2 class="section-title">📚 分类导航</h2>
    <div class="category-grid">
        {% for cat_id, cat_name in categories.items() %}
        <a href="{{ url_for('category', category_id=cat_id) }}" class="category-card">
            <span class="category-id">{{ cat_id }}</span>
            <span class="category-name">{{ cat_name }}</span>
        </a>
        {% endfor %}
    </div>
</section>

<section class="papers-section">
    <h2 class="section-title">🔥 最新 AI 论文</h2>
    <div class="paper-list">
        {% for paper in featured_papers %}
        <article class="paper-card">
            <div class="paper-header">
                <a href="{{ url_for('paper', paper_id=paper.id.split('/')[-1]) }}" class="paper-title">
                    {{ paper.title }}
                </a>
                <div class="paper-meta">
                    <span class="paper-date">{{ paper.published | format_date_short }}</span>
                    <span class="paper-category">{{ paper.primary_category }}</span>
                </div>
            </div>
            <p class="paper-authors">
                {% for author in paper.authors[:5] %}
                {{ author }}{% if not loop.last %}, {% endif %}
                {% endfor %}
                {% if paper.authors | length > 5 %}等{% endif %}
            </p>
            <p class="paper-summary">{{ paper.summary | truncate_text(250) }}</p>
            <div class="paper-actions">
                <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-primary">
                    📥 PDF
                </a>
                <a href="{{ paper.abs_url }}" target="_blank" class="btn btn-secondary">
                    🔗 arXiv
                </a>
            </div>
        </article>
        {% endfor %}
    </div>
</section>
{% endblock %}'''

        category_html = '''{% extends "base.html" %}

{% block title %}{{ category_name }} ({{ category_id }}) - arXiv 论文浏览器{% endblock %}

{% block content %}
<section class="page-header">
    <nav class="breadcrumb">
        <a href="{{ url_for('index') }}">首页</a> / 
        <span>{{ category_id }}</span>
    </nav>
    <h1>{{ category_name }}</h1>
    <p class="category-id-display">{{ category_id }}</p>
</section>

<section class="sidebar-layout">
    <aside class="sidebar">
        <h3>分类列表</h3>
        <ul class="category-list">
            {% for cat_id, cat_name in categories.items() %}
            <li class="{% if cat_id == category_id %}active{% endif %}">
                <a href="{{ url_for('category', category_id=cat_id) }}">
                    {{ cat_id }} - {{ cat_name }}
                </a>
            </li>
            {% endfor %}
        </ul>
    </aside>
    
    <div class="main-area">
        <div class="papers-header">
            <h2>最新论文</h2>
            <span class="paper-count">共 {{ papers | length }} 篇</span>
        </div>
        
        <div class="paper-list">
            {% for paper in papers %}
            <article class="paper-card">
                <div class="paper-header">
                    <a href="{{ url_for('paper', paper_id=paper.id.split('/')[-1]) }}" class="paper-title">
                        {{ paper.title }}
                    </a>
                    <div class="paper-meta">
                        <span class="paper-date">{{ paper.published | format_date_short }}</span>
                        {% for cat in paper.categories[:3] %}
                        <span class="paper-tag">{{ cat }}</span>
                        {% endfor %}
                    </div>
                </div>
                <p class="paper-authors">
                    {% for author in paper.authors[:5] %}
                    {{ author }}{% if not loop.last %}, {% endif %}
                    {% endfor %}
                    {% if paper.authors | length > 5 %}等{% endif %}
                </p>
                <p class="paper-summary">{{ paper.summary | truncate_text(200) }}</p>
                <div class="paper-actions">
                    <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-sm btn-primary">PDF</a>
                    <a href="{{ paper.abs_url }}" target="_blank" class="btn btn-sm btn-secondary">arXiv</a>
                </div>
            </article>
            {% endfor %}
        </div>
        
        <div class="pagination">
            {% if page > 1 %}
            <a href="?page={{ page - 1 }}" class="btn btn-secondary">上一页</a>
            {% endif %}
            <span class="page-info">第 {{ page }} 页</span>
            {% if papers | length >= 20 %}
            <a href="?page={{ page + 1 }}" class="btn btn-secondary">下一页</a>
            {% endif %}
        </div>
    </div>
</section>
{% endblock %}'''

        paper_html = '''{% extends "base.html" %}

{% block title %}{{ paper.title }} - arXiv 论文浏览器{% endblock %}

{% block content %}
<article class="paper-detail">
    <nav class="breadcrumb">
        <a href="{{ url_for('index') }}">首页</a> / 
        <a href="{{ url_for('category', category_id=paper.primary_category) }}">{{ paper.primary_category }}</a> / 
        <span>论文详情</span>
    </nav>
    
    <header class="paper-detail-header">
        <h1>{{ paper.title }}</h1>
        
        <div class="paper-detail-meta">
            <div class="meta-item">
                <span class="meta-label">📅 提交时间</span>
                <span class="meta-value">{{ paper.published | format_date }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">🔄 更新时间</span>
                <span class="meta-value">{{ paper.updated | format_date }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">📂 分类</span>
                <div class="meta-value tags">
                    {% for cat in paper.categories %}
                    <a href="{{ url_for('category', category_id=cat) }}" class="tag">{{ cat }}</a>
                    {% endfor %}
                </div>
            </div>
        </div>
    </header>
    
    <section class="paper-section">
        <h2>👥 作者</h2>
        <div class="authors-list">
            {% for author in paper.authors %}
            <span class="author-name">{{ author }}</span>
            {% endfor %}
        </div>
        {% if paper.affiliations %}
        <div class="affiliations-list">
            <strong>机构：</strong>
            {% for affil in paper.affiliations %}
            <span class="affiliation">{{ affil }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </section>
    
    <section class="paper-section">
        <h2>📝 摘要</h2>
        <div class="abstract-content">
            {{ paper.summary }}
        </div>
    </section>
    
    <section class="paper-section">
        <h2>📎 链接</h2>
        <div class="paper-links">
            <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-lg btn-primary">
                📥 下载 PDF
            </a>
            <a href="{{ paper.abs_url }}" target="_blank" class="btn btn-lg btn-secondary">
                🔗 arXiv 页面
            </a>
        </div>
    </section>
    
    <section class="paper-section">
        <h2>📋 BibTeX 引用</h2>
        <div class="bibtex-container">
            <pre class="bibtex-code" id="bibtex-content">{{ bibtex }}</pre>
            <button class="btn btn-copy" onclick="copyBibtex()">
                📋 一键复制
            </button>
        </div>
    </section>
</article>
{% endblock %}

{% block extra_js %}
<script>
function copyBibtex() {
    const bibtexContent = document.getElementById('bibtex-content').textContent;
    navigator.clipboard.writeText(bibtexContent).then(() => {
        const btn = document.querySelector('.btn-copy');
        const originalText = btn.textContent;
        btn.textContent = '✅ 已复制!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('copied');
        }, 2000);
    });
}
</script>
{% endblock %}'''

        search_html = '''{% extends "base.html" %}

{% block title %}搜索: {{ query }} - arXiv 论文浏览器{% endblock %}

{% block content %}
<section class="search-page">
    <h1>搜索结果</h1>
    
    <form action="{{ url_for('search') }}" method="get" class="search-form-large">
        <input type="text" name="q" value="{{ query }}" placeholder="输入关键词..." class="search-input-large">
        <select name="category" class="category-select">
            <option value="cs" {% if category == 'cs' %}selected{% endif %}>全部 CS</option>
            {% for cat_id, cat_name in categories.items() %}
            <option value="{{ cat_id }}" {% if category == cat_id %}selected{% endif %}>
                {{ cat_id }} - {{ cat_name }}
            </option>
            {% endfor %}
        </select>
        <button type="submit" class="btn btn-primary btn-lg">搜索</button>
    </form>
    
    {% if query %}
    <p class="search-info">
        在 <strong>{{ category }}</strong> 中搜索 "<strong>{{ query }}</strong>"，
        找到 {{ papers | length }} 篇论文
    </p>
    {% endif %}
    
    <div class="paper-list">
        {% for paper in papers %}
        <article class="paper-card">
            <div class="paper-header">
                <a href="{{ url_for('paper', paper_id=paper.id.split('/')[-1]) }}" class="paper-title">
                    {{ paper.title }}
                </a>
                <div class="paper-meta">
                    <span class="paper-date">{{ paper.published | format_date_short }}</span>
                    <span class="paper-category">{{ paper.primary_category }}</span>
                </div>
            </div>
            <p class="paper-authors">
                {% for author in paper.authors[:5] %}
                {{ author }}{% if not loop.last %}, {% endif %}
                {% endfor %}
                {% if paper.authors | length > 5 %}等{% endif %}
            </p>
            <p class="paper-summary">{{ paper.summary | truncate_text(200) }}</p>
            <div class="paper-actions">
                <a href="{{ paper.pdf_url }}" target="_blank" class="btn btn-sm btn-primary">PDF</a>
                <a href="{{ paper.abs_url }}" target="_blank" class="btn btn-sm btn-secondary">arXiv</a>
            </div>
        </article>
        {% endfor %}
    </div>
    
    {% if papers %}
    <div class="pagination">
        {% if page > 1 %}
        <a href="?q={{ query }}&category={{ category }}&page={{ page - 1 }}" class="btn btn-secondary">上一页</a>
        {% endif %}
        <span class="page-info">第 {{ page }} 页</span>
        {% if papers | length >= 20 %}
        <a href="?q={{ query }}&category={{ category }}&page={{ page + 1 }}" class="btn btn-secondary">下一页</a>
        {% endif %}
    </div>
    {% endif %}
</section>
{% endblock %}'''

        error_404_html = '''{% extends "base.html" %}

{% block title %}页面未找到 - arXiv 论文浏览器{% endblock %}

{% block content %}
<div class="error-page">
    <h1>404</h1>
    <p>抱歉，您访问的页面不存在</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">返回首页</a>
</div>
{% endblock %}'''

        return [
            CodeFile(
                path="templates/base.html",
                content=base_html,
                language="html",
                description="基础模板，包含导航栏和页脚"
            ),
            CodeFile(
                path="templates/index.html",
                content=index_html,
                language="html",
                description="首页模板，显示分类和最新论文"
            ),
            CodeFile(
                path="templates/category.html",
                content=category_html,
                language="html",
                description="分类页面模板"
            ),
            CodeFile(
                path="templates/paper.html",
                content=paper_html,
                language="html",
                description="论文详情页模板"
            ),
            CodeFile(
                path="templates/search.html",
                content=search_html,
                language="html",
                description="搜索结果页模板"
            ),
            CodeFile(
                path="templates/404.html",
                content=error_404_html,
                language="html",
                description="404 错误页模板"
            )
        ]
    
    def static_files(self) -> List[CodeFile]:
        """静态文件"""
        css_content = ''':root {
    /* 深色主题配色 */
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --bg-card: #1c2128;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --accent-primary: #58a6ff;
    --accent-secondary: #1f6feb;
    --accent-success: #3fb950;
    --accent-warning: #d29922;
    --accent-danger: #f85149;
    --border-color: #30363d;
    --border-light: #21262d;
    
    /* 渐变 */
    --gradient-hero: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --gradient-card: linear-gradient(145deg, #1c2128 0%, #161b22 100%);
    
    /* 字体 */
    --font-sans: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    
    /* 阴影 */
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
    --shadow-lg: 0 10px 25px rgba(0,0,0,0.5);
    
    /* 圆角 */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-sans);
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 24px;
}

/* 导航栏 */
.navbar {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 16px 0;
    position: sticky;
    top: 0;
    z-index: 1000;
    backdrop-filter: blur(10px);
}

.navbar .container {
    display: flex;
    align-items: center;
    gap: 32px;
}

.logo {
    display: flex;
    align-items: center;
    gap: 12px;
    text-decoration: none;
    color: var(--text-primary);
    font-weight: 700;
    font-size: 1.25rem;
}

.logo-icon {
    font-size: 1.5rem;
}

.search-form {
    flex: 1;
    max-width: 500px;
    display: flex;
    gap: 8px;
}

.search-input {
    flex: 1;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 10px 16px;
    color: var(--text-primary);
    font-size: 0.95rem;
    transition: all 0.2s ease;
}

.search-input:focus {
    outline: none;
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
}

.search-btn {
    background: var(--accent-secondary);
    border: none;
    border-radius: var(--radius-md);
    padding: 10px 16px;
    color: white;
    cursor: pointer;
    transition: background 0.2s ease;
}

.search-btn:hover {
    background: var(--accent-primary);
}

.nav-links {
    display: flex;
    gap: 20px;
}

.nav-links a {
    color: var(--text-secondary);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s ease;
}

.nav-links a:hover {
    color: var(--accent-primary);
}

/* 主内容区 */
.main-content {
    min-height: calc(100vh - 180px);
    padding: 40px 0;
}

/* Hero 区域 */
.hero {
    text-align: center;
    padding: 60px 20px;
    background: var(--gradient-hero);
    border-radius: var(--radius-lg);
    margin-bottom: 48px;
}

.hero h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 16px;
}

.hero-subtitle {
    color: rgba(255,255,255,0.9);
    font-size: 1.1rem;
}

/* 分类区域 */
.section-title {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 24px;
    color: var(--text-primary);
}

.category-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 48px;
}

.category-card {
    background: var(--gradient-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 20px;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: all 0.2s ease;
}

.category-card:hover {
    border-color: var(--accent-primary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.category-id {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--accent-primary);
    font-weight: 600;
}

.category-name {
    color: var(--text-primary);
    font-weight: 500;
}

/* 论文列表 */
.paper-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.paper-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 24px;
    transition: all 0.2s ease;
}

.paper-card:hover {
    border-color: var(--border-light);
    box-shadow: var(--shadow-md);
}

.paper-header {
    margin-bottom: 12px;
}

.paper-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--accent-primary);
    text-decoration: none;
    line-height: 1.4;
    display: block;
    margin-bottom: 8px;
}

.paper-title:hover {
    text-decoration: underline;
}

.paper-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
}

.paper-date {
    color: var(--text-muted);
    font-size: 0.85rem;
}

.paper-category,
.paper-tag {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-family: var(--font-mono);
}

.paper-authors {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 12px;
}

.paper-summary {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 16px;
    line-height: 1.6;
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
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    font-weight: 500;
    text-decoration: none;
    transition: all 0.2s ease;
    cursor: pointer;
    border: none;
    font-size: 0.9rem;
}

.btn-primary {
    background: var(--accent-secondary);
    color: white;
}

.btn-primary:hover {
    background: var(--accent-primary);
}

.btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

.btn-secondary:hover {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
}

.btn-sm {
    padding: 6px 12px;
    font-size: 0.8rem;
}

.btn-lg {
    padding: 12px 24px;
    font-size: 1rem;
}

/* 侧边栏布局 */
.sidebar-layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 40px;
}

.sidebar {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 24px;
    height: fit-content;
    position: sticky;
    top: 100px;
}

.sidebar h3 {
    font-size: 1rem;
    margin-bottom: 16px;
    color: var(--text-primary);
}

.category-list {
    list-style: none;
}

.category-list li {
    margin-bottom: 8px;
}

.category-list a {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 0.9rem;
    display: block;
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    transition: all 0.2s ease;
}

.category-list li.active a,
.category-list a:hover {
    background: var(--bg-tertiary);
    color: var(--accent-primary);
}

/* 论文详情页 */
.paper-detail {
    max-width: 900px;
    margin: 0 auto;
}

.breadcrumb {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-bottom: 24px;
}

.breadcrumb a {
    color: var(--accent-primary);
    text-decoration: none;
}

.breadcrumb a:hover {
    text-decoration: underline;
}

.paper-detail-header {
    margin-bottom: 40px;
}

.paper-detail-header h1 {
    font-size: 2rem;
    line-height: 1.3;
    margin-bottom: 24px;
}

.paper-detail-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    background: var(--bg-card);
    padding: 24px;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);
}

.meta-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.meta-label {
    font-size: 0.85rem;
    color: var(--text-muted);
}

.meta-value {
    font-weight: 500;
    color: var(--text-primary);
}

.meta-value.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.tag {
    background: var(--bg-tertiary);
    color: var(--accent-primary);
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.8rem;
    text-decoration: none;
    font-family: var(--font-mono);
}

.tag:hover {
    background: var(--accent-secondary);
    color: white;
}

.paper-section {
    margin-bottom: 32px;
}

.paper-section h2 {
    font-size: 1.25rem;
    margin-bottom: 16px;
    color: var(--text-primary);
}

.authors-list {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 12px;
}

.author-name {
    background: var(--bg-tertiary);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.9rem;
}

.affiliations-list {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

.abstract-content {
    background: var(--bg-card);
    padding: 24px;
    border-radius: var(--radius-md);
    border-left: 4px solid var(--accent-primary);
    line-height: 1.8;
    color: var(--text-secondary);
}

.paper-links {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}

.bibtex-container {
    position: relative;
    background: var(--bg-card);
    border-radius: var(--radius-md);
    overflow: hidden;
}

.bibtex-code {
    padding: 24px;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre-wrap;
    color: var(--text-secondary);
}

.btn-copy {
    position: absolute;
    top: 12px;
    right: 12px;
    background: var(--accent-secondary);
    color: white;
}

.btn-copy.copied {
    background: var(--accent-success);
}

/* 搜索页面 */
.search-page h1 {
    margin-bottom: 24px;
}

.search-form-large {
    display: flex;
    gap: 12px;
    margin-bottom: 32px;
    flex-wrap: wrap;
}

.search-input-large {
    flex: 1;
    min-width: 300px;
    padding: 14px 20px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 1rem;
}

.category-select {
    padding: 14px 20px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 1rem;
    cursor: pointer;
}

.search-info {
    color: var(--text-secondary);
    margin-bottom: 24px;
}

/* 分页 */
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    margin-top: 40px;
}

.page-info {
    color: var(--text-muted);
}

/* 页脚 */
.footer {
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    padding: 24px 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.footer a {
    color: var(--accent-primary);
    text-decoration: none;
}

/* 错误页 */
.error-page {
    text-align: center;
    padding: 80px 20px;
}

.error-page h1 {
    font-size: 6rem;
    color: var(--accent-primary);
    margin-bottom: 16px;
}

.error-page p {
    color: var(--text-secondary);
    margin-bottom: 32px;
}

/* 响应式 */
@media (max-width: 900px) {
    .sidebar-layout {
        grid-template-columns: 1fr;
    }
    
    .sidebar {
        position: static;
    }
    
    .navbar .container {
        flex-wrap: wrap;
    }
    
    .search-form {
        order: 3;
        width: 100%;
        max-width: none;
    }
}

@media (max-width: 600px) {
    .hero h1 {
        font-size: 1.75rem;
    }
    
    .paper-detail-header h1 {
        font-size: 1.5rem;
    }
    
    .category-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}'''

        js_content = '''/**
 * arXiv 论文浏览器 - 前端交互脚本
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化
    initSearchHighlight();
    initSmoothScroll();
    initKeyboardShortcuts();
});

/**
 * 搜索关键词高亮
 */
function initSearchHighlight() {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (query && query.trim()) {
        const keywords = query.trim().split(/\\s+/);
        const paperCards = document.querySelectorAll('.paper-card');
        
        paperCards.forEach(card => {
            const title = card.querySelector('.paper-title');
            const summary = card.querySelector('.paper-summary');
            
            if (title) highlightText(title, keywords);
            if (summary) highlightText(summary, keywords);
        });
    }
}

/**
 * 高亮文本中的关键词
 */
function highlightText(element, keywords) {
    let html = element.innerHTML;
    
    keywords.forEach(keyword => {
        if (keyword.length > 1) {
            const regex = new RegExp(`(${escapeRegex(keyword)})`, 'gi');
            html = html.replace(regex, '<mark class="highlight">$1</mark>');
        }
    });
    
    element.innerHTML = html;
}

/**
 * 转义正则特殊字符
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
}

/**
 * 平滑滚动
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * 键盘快捷键
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K: 聚焦搜索框
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Esc: 取消搜索框焦点
        if (e.key === 'Escape') {
            document.activeElement.blur();
        }
    });
}

/**
 * 复制到剪贴板
 */
async function copyToClipboard(text, buttonElement) {
    try {
        await navigator.clipboard.writeText(text);
        
        if (buttonElement) {
            const originalText = buttonElement.textContent;
            buttonElement.textContent = '✅ 已复制!';
            buttonElement.classList.add('copied');
            
            setTimeout(() => {
                buttonElement.textContent = originalText;
                buttonElement.classList.remove('copied');
            }, 2000);
        }
        
        return true;
    } catch (err) {
        console.error('复制失败:', err);
        return false;
    }
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('zh-CN', options);
}

/**
 * 懒加载图片
 */
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => observer.observe(img));
}'''

        return [
            CodeFile(
                path="static/css/style.css",
                content=css_content,
                language="css",
                description="主样式文件，深色主题设计"
            ),
            CodeFile(
                path="static/js/main.js",
                content=js_content,
                language="javascript",
                description="前端交互脚本"
            )
        ]
    
    def project_files(self) -> List[CodeFile]:
        """项目配置文件"""
        requirements = '''flask>=2.3.0
jinja2>=3.1.2
feedparser>=6.0.10
requests>=2.31.0
python-dotenv>=1.0.0
gunicorn>=21.2.0
'''
        
        readme = '''# arXiv 论文浏览器

一个现代化的 arXiv 计算机科学论文浏览网页应用。

## 功能特性

- 📚 **分类导航**: 按 arXiv CS 领域分类浏览 (cs.AI, cs.LG, cs.CV 等)
- 📄 **每日论文**: 展示最新论文，包含标题、提交时间、领域标签
- 📋 **论文详情**: PDF 链接、作者与机构、一键复制 BibTeX 引用
- 🔍 **搜索功能**: 支持关键词搜索和分类过滤

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python app.py
```

访问 http://localhost:5000 即可使用。

### 生产部署

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 技术栈

- **后端**: Python Flask
- **前端**: HTML5, CSS3, JavaScript
- **数据源**: arXiv API
- **样式**: 自定义 CSS (深色主题)

## 项目结构

```
├── app.py              # Flask 主应用
├── arxiv_client.py     # arXiv API 客户端
├── requirements.txt    # Python 依赖
├── templates/          # Jinja2 模板
│   ├── base.html
│   ├── index.html
│   ├── category.html
│   ├── paper.html
│   └── search.html
└── static/             # 静态资源
    ├── css/style.css
    └── js/main.js
```

## 许可证

MIT License
'''
        
        gitignore = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project
*.log
'''
        
        return [
            CodeFile(
                path="requirements.txt",
                content=requirements,
                language="text",
                description="Python 依赖列表"
            ),
            CodeFile(
                path="README.md",
                content=readme,
                language="markdown",
                description="项目说明文档"
            ),
            CodeFile(
                path=".gitignore",
                content=gitignore,
                language="text",
                description="Git 忽略文件"
            )
        ]

