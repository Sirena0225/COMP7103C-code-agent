"""
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
    def arxiv_id(self) -> str:
        """获取纯 arXiv ID"""
        return self.id.split("/")[-1]
    
    @property
    def bibtex(self) -> str:
        """生成 BibTeX 引用"""
        arxiv_id = self.arxiv_id
        first_author = self.authors[0].split()[-1] if self.authors else "Unknown"
        year = self.published.year
        title_clean = self.title.replace("\n", " ").strip()
        
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
        self.session.headers.update({
            "User-Agent": "arXiv-Browser/1.0 (academic research tool)"
        })
    
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
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return self._parse_feed(response.text)
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def get_recent_papers(self, category: str = "cs", 
                          days: int = 7, 
                          max_results: int = 100) -> List[Paper]:
        """获取最近几天的论文"""
        papers = self.search(
            category=category,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending"
        )
        
        cutoff = datetime.now() - timedelta(days=days)
        return [p for p in papers if p.published >= cutoff]
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """根据 ID 获取论文详情"""
        # 清理 ID 格式
        arxiv_id = arxiv_id.replace("http://arxiv.org/abs/", "")
        arxiv_id = arxiv_id.replace("https://arxiv.org/abs/", "")
        
        params = {
            "id_list": arxiv_id,
            "max_results": 1
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            papers = self._parse_feed(response.text)
            return papers[0] if papers else None
        except Exception as e:
            print(f"获取论文失败: {e}")
            return None
    
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
                if paper:
                    papers.append(paper)
            except Exception as e:
                print(f"解析论文失败: {e}")
                continue
        
        return papers
    
    def _parse_entry(self, entry) -> Optional[Paper]:
        """解析单个论文条目"""
        try:
            paper_id = entry.id
            
            # 提取标题
            title = html.unescape(entry.title)
            title = re.sub(r"\s+", " ", title).strip()
            
            # 提取摘要
            summary = html.unescape(entry.summary)
            summary = re.sub(r"\s+", " ", summary).strip()
            
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
            published = datetime(*entry.published_parsed[:6]) if entry.get("published_parsed") else datetime.now()
            updated = datetime(*entry.updated_parsed[:6]) if entry.get("updated_parsed") else published
            
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
        except Exception:
            return None


# 单例客户端
_client = None


def get_client() -> ArxivClient:
    """获取 arXiv 客户端实例"""
    global _client
    if _client is None:
        _client = ArxivClient()
    return _client

