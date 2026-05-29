"""
构建代码评审所需的上下文信息
"""
import os
from typing import Dict, List, Optional
from pathlib import Path

class ContextBuilder:
    """构建代码评审上下文"""

    def __init__(self, repo_path: Optional[str] = None):
        """
        初始化上下文构建器

        Args:
            repo_path: 仓库本地路径（可选）
        """
        self.repo_path = repo_path

    def build_pr_context(self, pr_data: dict, files_data: list) -> dict:
        """
        构建 PR 评审上下文

        Args:
            pr_data: PR 基本信息
            files_data: 文件变更列表

        Returns:
            完整的上下文字典
        """
        context = {
            'pr_info': self._extract_pr_info(pr_data),
            'files': self._process_files(files_data),
            'statistics': self._calculate_statistics(files_data),
            'metadata': {
                'total_files': len(files_data),
                'languages': self._detect_languages(files_data),
                'change_types': self._count_change_types(files_data)
            }
        }

        return context

    def _extract_pr_info(self, pr_data: dict) -> dict:
        """提取 PR 基本信息"""
        return {
            'number': pr_data.get('number'),
            'title': pr_data.get('title'),
            'description': pr_data.get('body', ''),
            'author': pr_data.get('user', {}).get('login'),
            'source_branch': pr_data.get('head', {}).get('ref'),
            'target_branch': pr_data.get('base', {}).get('ref'),
            'state': pr_data.get('state'),
            'created_at': pr_data.get('created_at'),
            'updated_at': pr_data.get('updated_at'),
        }

    def _process_files(self, files_data: list) -> list:
        """处理文件变更数据"""
        processed_files = []

        for file_data in files_data:
            processed_file = {
                'filename': file_data.get('filename'),
                'status': file_data.get('status'),
                'additions': file_data.get('additions', 0),
                'deletions': file_data.get('deletions', 0),
                'changes': file_data.get('changes', 0),
                'patch': file_data.get('patch', ''),
                'language': self._infer_language(file_data.get('filename', '')),
                'is_test': self._is_test_file(file_data.get('filename', '')),
                'is_config': self._is_config_file(file_data.get('filename', '')),
            }

            # 如果有本地仓库，尝试读取完整文件内容
            if self.repo_path:
                full_content = self._read_file_content(file_data.get('filename'))
                if full_content:
                    processed_file['full_content'] = full_content

            processed_files.append(processed_file)

        return processed_files

    def _calculate_statistics(self, files_data: list) -> dict:
        """计算变更统计信息"""
        total_additions = sum(f.get('additions', 0) for f in files_data)
        total_deletions = sum(f.get('deletions', 0) for f in files_data)

        return {
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_changes': total_additions + total_deletions,
            'files_added': sum(1 for f in files_data if f.get('status') == 'added'),
            'files_modified': sum(1 for f in files_data if f.get('status') == 'modified'),
            'files_deleted': sum(1 for f in files_data if f.get('status') == 'removed'),
            'files_renamed': sum(1 for f in files_data if f.get('status') == 'renamed'),
        }

    def _detect_languages(self, files_data: list) -> List[str]:
        """检测涉及的编程语言"""
        languages = set()
        for file_data in files_data:
            lang = self._infer_language(file_data.get('filename', ''))
            if lang != 'text':
                languages.add(lang)
        return sorted(list(languages))

    def _count_change_types(self, files_data: list) -> dict:
        """统计变更类型"""
        types = {}
        for file_data in files_data:
            status = file_data.get('status', 'unknown')
            types[status] = types.get(status, 0) + 1
        return types

    def _infer_language(self, filename: str) -> str:
        """推断文件语言"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
        }

        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                return lang

        return 'text'

    def _is_test_file(self, filename: str) -> bool:
        """判断是否为测试文件"""
        test_patterns = [
            'test_', '_test.', '.test.',
            '/tests/', '/test/',
            'spec.', '.spec.',
            '__tests__/'
        ]

        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in test_patterns)

    def _is_config_file(self, filename: str) -> bool:
        """判断是否为配置文件"""
        config_patterns = [
            '.json', '.yaml', '.yml', '.toml', '.ini',
            '.config', 'config.', '.env',
            'package.json', 'requirements.txt', 'Cargo.toml',
            'pom.xml', 'build.gradle'
        ]

        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in config_patterns)

    def _read_file_content(self, filename: str) -> Optional[str]:
        """读取文件完整内容"""
        if not self.repo_path:
            return None

        file_path = Path(self.repo_path) / filename

        try:
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"警告：无法读取文件 {filename}: {e}")

        return None

    def filter_files_by_language(self, files: list, languages: List[str]) -> list:
        """按语言过滤文件"""
        return [f for f in files if f.get('language') in languages]

    def filter_large_files(self, files: list, max_changes: int = 500) -> tuple:
        """
        过滤大文件

        Args:
            files: 文件列表
            max_changes: 最大变更行数阈值

        Returns:
            (小文件列表, 大文件列表)
        """
        small_files = []
        large_files = []

        for f in files:
            if f.get('changes', 0) > max_changes:
                large_files.append(f)
            else:
                small_files.append(f)

        return small_files, large_files

    def prioritize_files(self, files: list) -> list:
        """
        对文件进行优先级排序

        优先级规则：
        1. 非测试文件 > 测试文件
        2. 代码文件 > 配置文件
        3. 变更行数多的优先

        Args:
            files: 文件列表

        Returns:
            排序后的文件列表
        """
        def priority_score(file_data):
            score = 0

            # 非测试文件加分
            if not file_data.get('is_test', False):
                score += 1000

            # 非配置文件加分
            if not file_data.get('is_config', False):
                score += 500

            # 变更行数
            score += file_data.get('changes', 0)

            return score

        return sorted(files, key=priority_score, reverse=True)
