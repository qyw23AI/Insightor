"""
AI 分析引擎 - 封装 Claude API 调用
"""
import os
from typing import Optional, Dict, List
from anthropic import Anthropic
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class AIEngine:
    """AI 代码分析引擎"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "claude-opus-4-8",
        max_tokens: int = 4096,
        temperature: float = 0.3
    ):
        """
        初始化 AI 引擎

        Args:
            api_key: Anthropic API 密钥（默认从环境变量读取）
            base_url: API 基础 URL（用于第三方代理）
            model: 使用的模型名称
            max_tokens: 最大输出 token 数
            temperature: 温度参数（0-1，越低越确定）
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_key:
            raise ValueError("未找到 ANTHROPIC_API_KEY，请在 .env 文件中配置")

        # 初始化 Anthropic 客户端
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = Anthropic(**client_kwargs)

    def analyze_code(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        分析代码

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数（可选，覆盖默认值）

        Returns:
            AI 分析结果
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # 提取文本内容
            if response.content and len(response.content) > 0:
                return response.content[0].text

            return "AI 未返回有效内容"

        except Exception as e:
            error_msg = f"AI 分析失败: {str(e)}"
            print(f"错误: {error_msg}")
            raise

    def batch_analyze(
        self,
        system_prompt: str,
        prompts: List[str],
        temperature: Optional[float] = None
    ) -> List[str]:
        """
        批量分析多个提示词

        Args:
            system_prompt: 系统提示词
            prompts: 用户提示词列表
            temperature: 温度参数

        Returns:
            分析结果列表
        """
        results = []

        for i, prompt in enumerate(prompts):
            print(f"正在分析 {i + 1}/{len(prompts)}...")
            try:
                result = self.analyze_code(system_prompt, prompt, temperature)
                results.append(result)
            except Exception as e:
                print(f"分析第 {i + 1} 项时出错: {e}")
                results.append(f"分析失败: {str(e)}")

        return results

    def review_pr(
        self,
        pr_context: dict,
        review_type: str = "comprehensive"
    ) -> Dict[str, str]:
        """
        评审 PR

        Args:
            pr_context: PR 上下文信息
            review_type: 评审类型
                - comprehensive: 综合评审
                - security: 安全审查
                - performance: 性能分析
                - quality: 代码质量

        Returns:
            评审结果字典
        """
        from .prompts import (
            SYSTEM_PROMPT,
            format_code_review_prompt,
            format_security_review_prompt,
            format_performance_review_prompt
        )

        results = {}

        if review_type == "comprehensive":
            # 综合评审
            prompt = format_code_review_prompt(
                pr_context['pr_info'],
                pr_context['files']
            )
            results['comprehensive'] = self.analyze_code(SYSTEM_PROMPT, prompt)

        elif review_type == "security":
            # 安全审查
            security_prompts = []
            for file_data in pr_context['files']:
                if file_data.get('language') in ['python', 'javascript', 'typescript', 'java', 'php']:
                    content = file_data.get('full_content') or file_data.get('patch', '')
                    if content:
                        security_prompts.append(
                            format_security_review_prompt(
                                file_data['filename'],
                                content
                            )
                        )

            if security_prompts:
                security_results = self.batch_analyze(SYSTEM_PROMPT, security_prompts)
                results['security'] = "\n\n".join(security_results)
            else:
                results['security'] = "无需安全审查的文件"

        elif review_type == "performance":
            # 性能分析
            perf_prompts = []
            for file_data in pr_context['files']:
                if not file_data.get('is_config', False):
                    content = file_data.get('full_content') or file_data.get('patch', '')
                    if content:
                        perf_prompts.append(
                            format_performance_review_prompt(
                                file_data['filename'],
                                content
                            )
                        )

            if perf_prompts:
                perf_results = self.batch_analyze(SYSTEM_PROMPT, perf_prompts)
                results['performance'] = "\n\n".join(perf_results)
            else:
                results['performance'] = "无需性能分析的文件"

        elif review_type == "quality":
            # 代码质量评估
            prompt = format_code_review_prompt(
                pr_context['pr_info'],
                pr_context['files']
            )
            results['quality'] = self.analyze_code(SYSTEM_PROMPT, prompt, temperature=0.2)

        else:
            raise ValueError(f"不支持的评审类型: {review_type}")

        return results

    def summarize_reviews(self, review_results: Dict[str, str]) -> str:
        """
        总结评审结果

        Args:
            review_results: 各类评审结果

        Returns:
            总结文本
        """
        from .prompts import SYSTEM_PROMPT, SUMMARY_PROMPT

        # 合并所有评审结果
        combined_results = "\n\n".join([
            f"## {key.upper()}\n{value}"
            for key, value in review_results.items()
        ])

        summary_prompt = SUMMARY_PROMPT.format(review_results=combined_results)

        return self.analyze_code(SYSTEM_PROMPT, summary_prompt, temperature=0.2)

    def get_model_info(self) -> dict:
        """获取当前模型信息"""
        return {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'base_url': self.base_url or 'https://api.anthropic.com'
        }


# 便捷函数
def create_engine(
    model: str = "claude-opus-4-8",
    max_tokens: int = 4096,
    temperature: float = 0.3
) -> AIEngine:
    """
    创建 AI 引擎实例

    Args:
        model: 模型名称
        max_tokens: 最大 token 数
        temperature: 温度参数

    Returns:
        AIEngine 实例
    """
    return AIEngine(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )
