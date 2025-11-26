"""Code review and evaluation agent."""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base_agent import BaseAgent
from models import Task, TaskType, TaskStatus, MessageType
from config import Settings
from tools import FileTools, CodeTools, TestTools


class ReviewerAgent(BaseAgent):
    """
    代码评估智能体
    
    负责：
    - 代码质量审查
    - 功能测试
    - 安全检查
    - 性能评估
    - 反馈与建议
    """
    
    def __init__(self, settings: Settings, file_tools: FileTools):
        super().__init__(
            agent_id="reviewer",
            name="代码评估智能体",
            settings=settings
        )
        self.file_tools = file_tools
        self.code_tools = CodeTools()
        self.test_tools = TestTools()
        self.project_path: Optional[Path] = None
    
    def set_project_path(self, path: Path):
        """设置项目路径"""
        self.project_path = path
    
    def get_system_prompt(self) -> str:
        return """你是一个专业的代码审查专家和质量保证工程师。你的职责是：

1. 审查代码质量和最佳实践
2. 检测潜在的 bug 和安全漏洞
3. 评估代码的可维护性和可读性
4. 验证功能是否符合需求
5. 提供改进建议

审查维度：
- 代码风格：是否遵循语言规范
- 功能正确性：是否实现了预期功能
- 安全性：是否有安全隐患
- 性能：是否有性能问题
- 可维护性：代码是否易于理解和修改

输出格式：
请以 JSON 格式输出审查结果，包含：
- score: 总体评分 (1-10)
- issues: 问题列表
- suggestions: 改进建议
- summary: 总结"""
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """执行审查任务"""
        self.start_task(task)
        
        try:
            if task.type == TaskType.REVIEW:
                result = await self._review_code(task)
            elif task.type == TaskType.TESTING:
                result = await self._run_tests(task)
            else:
                result = await self._generic_review(task)
            
            self.complete_task(result)
            return result
            
        except Exception as e:
            self.fail_task(str(e))
            return {"error": str(e)}
    
    async def _review_code(self, task: Task) -> Dict[str, Any]:
        """审查代码"""
        review_type = task.input_data.get("review_type", "full")
        project_spec = task.input_data.get("project_spec", {})
        
        if not self.project_path:
            return {"error": "项目路径未设置"}
        
        # 获取所有文件
        files = self.file_tools.list_files("", self.project_path, "*")
        
        # 过滤代码文件
        code_files = [f for f in files if self._is_code_file(f)]
        
        # 审查每个文件
        file_reviews = []
        total_score = 0
        all_issues = []
        all_suggestions = []
        
        for file_path in code_files:
            content = self.file_tools.read_file(file_path, self.project_path)
            if content:
                review = await self._review_single_file(file_path, content, project_spec)
                file_reviews.append(review)
                total_score += review.get("score", 5)
                all_issues.extend(review.get("issues", []))
                all_suggestions.extend(review.get("suggestions", []))
        
        # 计算平均分
        avg_score = total_score / len(file_reviews) if file_reviews else 0
        
        # 运行语法检查
        syntax_issues = self._check_syntax_all(code_files)
        all_issues.extend(syntax_issues)
        
        return {
            "overall_score": round(avg_score, 1),
            "files_reviewed": len(file_reviews),
            "file_reviews": file_reviews,
            "total_issues": len(all_issues),
            "issues": all_issues[:20],  # 限制数量
            "suggestions": list(set(all_suggestions))[:10],
            "passed": avg_score >= 6 and len([i for i in all_issues if i.get("severity") == "critical"]) == 0
        }
    
    async def _review_single_file(self, file_path: str, content: str, 
                                   project_spec: Dict) -> Dict[str, Any]:
        """审查单个文件"""
        
        prompt = f"""请审查以下代码文件：

## 文件路径
{file_path}

## 项目需求
{json.dumps(project_spec.get("features", []), ensure_ascii=False)}

## 代码内容
```
{content[:3000]}  
```
{"(代码已截断)" if len(content) > 3000 else ""}

## 请从以下维度进行审查并以 JSON 格式返回：

```json
{{
    "score": 评分(1-10),
    "issues": [
        {{
            "type": "bug/style/security/performance",
            "severity": "critical/high/medium/low",
            "line": 行号或null,
            "message": "问题描述"
        }}
    ],
    "suggestions": ["改进建议1", "改进建议2"],
    "summary": "总体评价"
}}
```"""

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.call_llm(messages, temperature=self.settings.reviewer_temperature)
        
        # 解析响应
        review = self._parse_review_response(response)
        review["file"] = file_path
        
        # 如果解析失败，返回默认评审
        if review.get("score", 0) == 0:
            review = self._get_default_review(file_path, content)
        
        return review
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """解析审查响应"""
        import re
        
        try:
            return json.loads(response)
        except:
            pass
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return {
            "score": 0,
            "issues": [],
            "suggestions": [],
            "summary": "无法解析审查结果"
        }
    
    def _get_default_review(self, file_path: str, content: str) -> Dict[str, Any]:
        """获取默认审查结果"""
        issues = []
        suggestions = []
        score = 7
        
        # 基本检查
        lines = content.split('\n')
        
        # 检查文件长度
        if len(lines) > 500:
            issues.append({
                "type": "style",
                "severity": "medium",
                "line": None,
                "message": f"文件过长 ({len(lines)} 行)，建议拆分"
            })
            score -= 0.5
        
        # 检查是否有 docstring/注释
        if file_path.endswith('.py'):
            if '"""' not in content and "'''" not in content:
                issues.append({
                    "type": "style",
                    "severity": "low",
                    "line": None,
                    "message": "缺少文档字符串"
                })
                suggestions.append("添加模块和函数的文档字符串")
                score -= 0.5
        
        # 检查是否有硬编码敏感信息
        sensitive_patterns = ['password', 'secret', 'api_key', 'token']
        for pattern in sensitive_patterns:
            if pattern in content.lower() and '=' in content:
                issues.append({
                    "type": "security",
                    "severity": "high",
                    "line": None,
                    "message": f"可能存在硬编码的敏感信息: {pattern}"
                })
                score -= 1
        
        # 检查 TODO/FIXME
        todo_count = content.lower().count('todo') + content.lower().count('fixme')
        if todo_count > 0:
            issues.append({
                "type": "style",
                "severity": "low",
                "line": None,
                "message": f"存在 {todo_count} 个 TODO/FIXME 注释"
            })
        
        return {
            "file": file_path,
            "score": max(1, min(10, score)),
            "issues": issues,
            "suggestions": suggestions,
            "summary": f"代码基本符合规范，评分 {score}/10"
        }
    
    def _check_syntax_all(self, files: List[str]) -> List[Dict[str, Any]]:
        """检查所有文件的语法"""
        issues = []
        
        for file_path in files:
            content = self.file_tools.read_file(file_path, self.project_path)
            if not content:
                continue
            
            result = self.test_tools.check_file_syntax(file_path, content)
            
            if not result["valid"]:
                for error in result["errors"]:
                    issues.append({
                        "type": "bug",
                        "severity": "critical",
                        "file": file_path,
                        "message": f"语法错误: {error}"
                    })
            
            for warning in result.get("warnings", []):
                issues.append({
                    "type": "style",
                    "severity": "low",
                    "file": file_path,
                    "message": f"警告: {warning}"
                })
        
        return issues
    
    def _is_code_file(self, file_path: str) -> bool:
        """判断是否是代码文件"""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', 
            '.html', '.htm', '.css', '.scss',
            '.json', '.yaml', '.yml'
        }
        return Path(file_path).suffix.lower() in code_extensions
    
    async def _run_tests(self, task: Task) -> Dict[str, Any]:
        """运行测试"""
        test_type = task.input_data.get("test_type", "functional")
        features = task.input_data.get("features", [])
        
        if not self.project_path:
            return {"error": "项目路径未设置"}
        
        results = {
            "test_type": test_type,
            "passed": True,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        # 功能测试
        if test_type == "functional":
            # 检查必要文件是否存在
            required_files = self._get_required_files(features)
            for file_path in required_files:
                exists = self.file_tools.file_exists(file_path, self.project_path)
                results["tests_run"] += 1
                
                if exists:
                    results["tests_passed"] += 1
                    results["details"].append({
                        "test": f"文件存在: {file_path}",
                        "passed": True
                    })
                else:
                    results["tests_failed"] += 1
                    results["passed"] = False
                    results["details"].append({
                        "test": f"文件存在: {file_path}",
                        "passed": False,
                        "error": "文件不存在"
                    })
            
            # 检查关键功能
            func_results = await self._check_features(features)
            results["tests_run"] += func_results["total"]
            results["tests_passed"] += func_results["passed"]
            results["tests_failed"] += func_results["failed"]
            results["details"].extend(func_results["details"])
            
            if func_results["failed"] > 0:
                results["passed"] = False
        
        # 运行 pytest（如果存在测试文件）
        test_files = self.file_tools.list_files("", self.project_path, "test_*.py")
        if test_files:
            pytest_results = self.test_tools.run_python_tests(
                ".",
                self.project_path
            )
            results["pytest"] = pytest_results
        
        return results
    
    def _get_required_files(self, features: List[str]) -> List[str]:
        """根据功能确定必需的文件"""
        required = ["main.py"]
        
        for feature in features:
            feature_lower = feature.lower()
            
            if "分类" in feature or "导航" in feature:
                required.extend([
                    "templates/index.html",
                    "templates/category.html"
                ])
            
            if "论文" in feature or "详情" in feature:
                required.extend([
                    "templates/paper.html",
                    "arxiv_client.py"
                ])
            
            if "样式" in feature or "界面" in feature:
                required.append("static/css/style.css")
        
        return list(set(required))
    
    async def _check_features(self, features: List[str]) -> Dict[str, Any]:
        """检查功能实现"""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        # 读取主文件检查路由
        main_content = self.file_tools.read_file("main.py", self.project_path)
        
        if not main_content:
            results["total"] = 1
            results["failed"] = 1
            results["details"].append({
                "test": "main.py 存在且可读",
                "passed": False,
                "error": "无法读取 main.py"
            })
            return results
        
        # 检查路由定义
        route_checks = [
            ('/', '首页路由'),
            ('/category/', '分类路由'),
            ('/paper/', '论文详情路由'),
        ]
        
        for route, name in route_checks:
            results["total"] += 1
            if route in main_content or f'"{route}' in main_content:
                results["passed"] += 1
                results["details"].append({
                    "test": f"{name} ({route})",
                    "passed": True
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "test": f"{name} ({route})",
                    "passed": False,
                    "error": f"未找到路由 {route}"
                })
        
        # 检查关键功能
        feature_checks = [
            ('bibtex', 'BibTeX 功能'),
            ('pdf', 'PDF 链接功能'),
            ('category', '分类功能'),
        ]
        
        for keyword, name in feature_checks:
            results["total"] += 1
            if keyword.lower() in main_content.lower():
                results["passed"] += 1
                results["details"].append({
                    "test": name,
                    "passed": True
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "test": name,
                    "passed": False,
                    "error": f"未找到 {keyword} 相关实现"
                })
        
        return results
    
    async def _generic_review(self, task: Task) -> Dict[str, Any]:
        """通用审查任务"""
        return {
            "status": "completed",
            "task_name": task.name,
            "review_type": "generic"
        }
    
    def generate_review_report(self, review_results: Dict[str, Any]) -> str:
        """生成审查报告"""
        report = []
        report.append("=" * 60)
        report.append("代码审查报告")
        report.append("=" * 60)
        report.append("")
        
        # 总体评分
        score = review_results.get("overall_score", 0)
        report.append(f"📊 总体评分: {score}/10")
        report.append(f"📁 审查文件数: {review_results.get('files_reviewed', 0)}")
        report.append(f"⚠️  发现问题数: {review_results.get('total_issues', 0)}")
        report.append(f"✅ 审查结果: {'通过' if review_results.get('passed') else '未通过'}")
        report.append("")
        
        # 问题列表
        issues = review_results.get("issues", [])
        if issues:
            report.append("-" * 40)
            report.append("问题列表:")
            report.append("-" * 40)
            for i, issue in enumerate(issues, 1):
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    issue.get("severity", "low"), "⚪"
                )
                report.append(f"{i}. {severity_icon} [{issue.get('type', 'unknown')}] {issue.get('message', '')}")
                if issue.get("file"):
                    report.append(f"   文件: {issue['file']}")
            report.append("")
        
        # 改进建议
        suggestions = review_results.get("suggestions", [])
        if suggestions:
            report.append("-" * 40)
            report.append("改进建议:")
            report.append("-" * 40)
            for i, suggestion in enumerate(suggestions, 1):
                report.append(f"{i}. 💡 {suggestion}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)

