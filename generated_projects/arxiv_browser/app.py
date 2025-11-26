"""
arXiv 论文浏览器 - Flask 应用
"""
from flask import Flask, render_template, request, jsonify, abort
from datetime import datetime
import os

from arxiv_client import get_client

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# arXiv 客户端
client = get_client()


@app.route("/")
def index():
    """首页 - 显示分类导航和最新论文"""
    categories = client.get_categories()
    
    # 获取热门分类的最新论文
    try:
        featured_papers = client.search(category="cs.AI", max_results=10)
    except Exception:
        featured_papers = []
    
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
    
    try:
        papers = client.search(
            category=category_id,
            max_results=per_page,
            start=start
        )
    except Exception:
        papers = []
    
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
    paper_data = client.get_paper_by_id(paper_id)
    
    if not paper_data:
        abort(404)
    
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
        try:
            papers = client.search(
                query=query,
                category=category,
                max_results=per_page,
                start=start
            )
        except Exception:
            papers = []
    
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
    max_results = min(request.args.get("limit", 20, type=int), 100)
    start = request.args.get("offset", 0, type=int)
    
    try:
        papers = client.search(
            category=category,
            max_results=max_results,
            start=start
        )
        
        return jsonify({
            "success": True,
            "papers": [
                {
                    "id": p.arxiv_id,
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
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/paper/<path:paper_id>")
def api_paper(paper_id: str):
    """API: 获取论文详情"""
    paper_data = client.get_paper_by_id(paper_id)
    
    if not paper_data:
        return jsonify({"success": False, "error": "Paper not found"}), 404
    
    return jsonify({
        "success": True,
        "paper": {
            "id": paper_data.arxiv_id,
            "title": paper_data.title,
            "summary": paper_data.summary,
            "authors": paper_data.authors,
            "affiliations": paper_data.affiliations,
            "categories": paper_data.categories,
            "published": paper_data.published.isoformat(),
            "updated": paper_data.updated.isoformat(),
            "pdf_url": paper_data.pdf_url,
            "abs_url": paper_data.abs_url,
            "bibtex": paper_data.bibtex
        }
    })


@app.route("/api/paper/<path:paper_id>/bibtex")
def api_bibtex(paper_id: str):
    """API: 获取 BibTeX 引用"""
    paper_data = client.get_paper_by_id(paper_id)
    
    if not paper_data:
        return jsonify({"success": False, "error": "Paper not found"}), 404
    
    return jsonify({
        "success": True,
        "bibtex": paper_data.bibtex
    })


@app.route("/api/categories")
def api_categories():
    """API: 获取分类列表"""
    return jsonify({
        "success": True,
        "categories": client.get_categories()
    })


@app.template_filter("truncate_text")
def truncate_text(text: str, length: int = 200) -> str:
    """截断文本"""
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


@app.template_filter("format_date")
def format_date(dt: datetime) -> str:
    """格式化日期"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%Y-%m-%d %H:%M")


@app.template_filter("format_date_short")
def format_date_short(dt: datetime) -> str:
    """格式化短日期"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%Y-%m-%d")


@app.errorhandler(404)
def page_not_found(e):
    """404 错误页"""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    """500 错误页"""
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)

