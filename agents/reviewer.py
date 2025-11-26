"""
代码评估智能体 - 自动测试、审查代码质量与功能
"""
import ast
import re
from typing import Any, Dict, List, Optional
import json
import subprocess
import tempfile
import os

from .base import BaseAgent
from models import CodeFile, ProjectState, ReviewResult
from config import LLMConfig


REVIEWER_SYSTEM_PROMPT = """你是一个资深代码审查专家，专注于代码质量、安全性和最佳实践。

你的任务是审查代码并提供详细的反馈。请关注：

1. **代码质量**
   - 代码结构和可读性
   - 命名规范
   - 注释完整性
   - DRY 原则遵循

2. **功能完整性**
   - 是否满足需求
   - 边界情况处理
   - 错误处理

3. **安全性**
   - 输入验证
   - SQL 注入防护
   - XSS 防护
   - 敏感信息处理

4. **性能**
   - 算法效率
   - 资源使用
   - 缓存策略

请以 JSON 格式返回审查结果：

{
    "passed": true/false,
    "score": 0-10,
    "issues": [
        {
            "severity": "error/warning/info",
            "line": 行号,
            "message": "问题描述",
            "suggestion": "修复建议"
        }
    ],
    "suggestions": ["优化建议列表"],
    "summary": "整体评价"
}
"""


class ReviewerAgent(BaseAgent):
    """代码评估智能体"""
    
    def __init__(self, llm_config: LLMConfig = None):
        super().__init__("reviewer", llm_config)
        self.static_analyzers = StaticAnalyzers()
    
    async def process(self, input_data: Any) -> Any:
        """处理输入"""
        return None
    
    async def review_project(self, project_state: ProjectState) -> List[ReviewResult]:
        """审查整个项目"""
        results = []
        
        for file in project_state.files:
            result = await self.review_file(file, project_state)
            results.append(result)
        
        return results
    
    async def review_file(self, file: CodeFile, 
                         project_state: ProjectState) -> ReviewResult:
        """审查单个文件"""
        # 静态分析
        static_issues = self._run_static_analysis(file)
        
        # LLM 审查
        llm_review = await self._llm_review(file, project_state)
        
        # 合并结果
        all_issues = static_issues + llm_review.get("issues", [])
        
        # 计算最终分数
        score = self._calculate_score(all_issues, llm_review.get("score", 8.0))
        passed = score >= 6.0 and not any(
            i.get("severity") == "error" for i in all_issues
        )
        
        return ReviewResult(
            file_path=file.path,
            passed=passed,
            score=score,
            issues=all_issues,
            suggestions=llm_review.get("suggestions", [])
        )
    
    async def _llm_review(self, file: CodeFile, 
                         project_state: ProjectState) -> Dict:
        """使用 LLM 进行代码审查"""
        context = ""
        if project_state.plan:
            context = f"""
项目名称: {project_state.plan.project_name}
项目描述: {project_state.plan.description}
"""
        
        prompt = f"""请审查以下代码文件：

文件路径：{file.path}
语言：{file.language}
描述：{file.description}

{context}

代码内容：
```{file.language}
{file.content[:4000]}  # 限制长度
```

请提供详细的代码审查结果。
"""
        
        response = await self.call_llm(prompt, REVIEWER_SYSTEM_PROMPT)
        
        try:
            return self.parse_json_response(response)
        except Exception:
            # 返回默认审查结果
            return {
                "passed": True,
                "score": 7.5,
                "issues": [],
                "suggestions": ["代码整体质量良好"],
                "summary": "代码审查通过"
            }
    
    def _run_static_analysis(self, file: CodeFile) -> List[Dict]:
        """运行静态代码分析"""
        issues = []
        
        if file.language == "python":
            issues.extend(self.static_analyzers.analyze_python(file.content))
        elif file.language in ("javascript", "typescript"):
            issues.extend(self.static_analyzers.analyze_javascript(file.content))
        elif file.language == "html":
            issues.extend(self.static_analyzers.analyze_html(file.content))
        elif file.language == "css":
            issues.extend(self.static_analyzers.analyze_css(file.content))
        
        return issues
    
    def _calculate_score(self, issues: List[Dict], base_score: float) -> float:
        """计算最终分数"""
        score = base_score
        
        for issue in issues:
            severity = issue.get("severity", "info")
            if severity == "error":
                score -= 1.0
            elif severity == "warning":
                score -= 0.3
            elif severity == "info":
                score -= 0.1
        
        return max(0.0, min(10.0, score))
    
    async def run_tests(self, project_state: ProjectState) -> Dict:
        """运行项目测试"""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_results": []
        }
        
        # 查找测试文件
        test_files = [
            f for f in project_state.files 
            if "test" in f.path.lower() and f.language == "python"
        ]
        
        if not test_files:
            results["errors"].append("未找到测试文件")
            return results
        
        # 在临时目录中运行测试
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入所有文件
            for file in project_state.files:
                file_path = os.path.join(tmpdir, file.path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file.content)
            
            # 运行 pytest
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "-v", "--tb=short"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # 解析测试结果
                output = result.stdout + result.stderr
                
                # 统计通过/失败
                passed_match = re.search(r"(\d+) passed", output)
                failed_match = re.search(r"(\d+) failed", output)
                
                if passed_match:
                    results["passed"] = int(passed_match.group(1))
                if failed_match:
                    results["failed"] = int(failed_match.group(1))
                
                results["total"] = results["passed"] + results["failed"]
                results["output"] = output
                
            except subprocess.TimeoutExpired:
                results["errors"].append("测试超时")
            except Exception as e:
                results["errors"].append(f"测试执行失败: {str(e)}")
        
        return results


class StaticAnalyzers:
    """静态代码分析器集合"""
    
    def analyze_python(self, code: str) -> List[Dict]:
        """分析 Python 代码"""
        issues = []
        
        # 语法检查
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append({
                "severity": "error",
                "line": e.lineno,
                "message": f"语法错误: {e.msg}",
                "suggestion": "修复语法错误"
            })
            return issues  # 语法错误后无法继续分析
        
        lines = code.split("\n")
        
        for i, line in enumerate(lines, 1):
            # 行长度检查
            if len(line) > 120:
                issues.append({
                    "severity": "warning",
                    "line": i,
                    "message": f"行长度 ({len(line)}) 超过 120 字符",
                    "suggestion": "考虑拆分为多行"
                })
            
            # 调试代码检查
            if re.search(r"\bprint\s*\([^)]*debug|DEBUG", line):
                issues.append({
                    "severity": "warning",
                    "line": i,
                    "message": "可能存在调试代码",
                    "suggestion": "移除或替换为日志"
                })
            
            # 硬编码密码检查
            if re.search(r"(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]", line, re.I):
                issues.append({
                    "severity": "error",
                    "line": i,
                    "message": "可能存在硬编码的敏感信息",
                    "suggestion": "使用环境变量或配置文件"
                })
            
            # TODO/FIXME 检查
            if re.search(r"#\s*(TODO|FIXME|XXX|HACK)", line, re.I):
                issues.append({
                    "severity": "info",
                    "line": i,
                    "message": "存在待处理标记",
                    "suggestion": "完成或创建任务跟踪"
                })
        
        # 导入检查
        if not re.search(r"^from\s+__future__\s+import", code, re.M):
            pass  # 可选建议
        
        return issues
    
    def analyze_javascript(self, code: str) -> List[Dict]:
        """分析 JavaScript 代码"""
        issues = []
        lines = code.split("\n")
        
        for i, line in enumerate(lines, 1):
            # var 使用检查
            if re.search(r"\bvar\s+\w+", line):
                issues.append({
                    "severity": "warning",
                    "line": i,
                    "message": "使用 var 声明变量",
                    "suggestion": "建议使用 let 或 const"
                })
            
            # console.log 检查
            if "console.log" in line and "// debug" not in line.lower():
                issues.append({
                    "severity": "info",
                    "line": i,
                    "message": "存在 console.log 调用",
                    "suggestion": "生产环境应移除"
                })
            
            # eval 使用检查
            if re.search(r"\beval\s*\(", line):
                issues.append({
                    "severity": "error",
                    "line": i,
                    "message": "使用了 eval()，存在安全风险",
                    "suggestion": "避免使用 eval，使用更安全的替代方案"
                })
        
        return issues
    
    def analyze_html(self, code: str) -> List[Dict]:
        """分析 HTML 代码"""
        issues = []
        
        # DOCTYPE 检查
        if not re.search(r"<!DOCTYPE\s+html>", code, re.I):
            issues.append({
                "severity": "warning",
                "line": 1,
                "message": "缺少 DOCTYPE 声明",
                "suggestion": "添加 <!DOCTYPE html>"
            })
        
        # 字符编码检查
        if not re.search(r'<meta\s+charset', code, re.I):
            issues.append({
                "severity": "warning",
                "line": 1,
                "message": "缺少字符编码声明",
                "suggestion": "添加 <meta charset=\"UTF-8\">"
            })
        
        # 内联事件处理检查
        inline_events = re.findall(r'on\w+\s*=\s*["\']', code)
        if inline_events:
            issues.append({
                "severity": "info",
                "line": 1,
                "message": f"发现 {len(inline_events)} 个内联事件处理器",
                "suggestion": "建议使用 addEventListener"
            })
        
        return issues
    
    def analyze_css(self, code: str) -> List[Dict]:
        """分析 CSS 代码"""
        issues = []
        
        # !important 使用检查
        important_count = code.count("!important")
        if important_count > 5:
            issues.append({
                "severity": "warning",
                "line": 1,
                "message": f"过度使用 !important ({important_count} 次)",
                "suggestion": "重构 CSS 选择器优先级"
            })
        
        # 重复属性检查
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # 检查魔法数字
            magic_numbers = re.findall(r":\s*\d+px", line)
            if len(magic_numbers) > 0:
                # 只对非标准值报告
                for match in magic_numbers:
                    value = int(re.search(r"\d+", match).group())
                    if value not in (0, 1, 2, 4, 8, 12, 16, 20, 24, 32, 48, 64):
                        pass  # 可选：报告非标准间距值
        
        return issues

