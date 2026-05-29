import os
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量读取配置
TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("OWNER", "qyw23AI")
REPO = os.getenv("REPO", "Insightor")
PR_NUMBER = int(os.getenv("PR_NUMBER", "1"))


def get_pr_info(owner: str, repo: str, pr_number: int, token: str = None) -> dict:
    """
    获取指定 PR 的基本信息

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        pr_number: PR 编号
        token: GitHub token（可选，默认使用环境变量）

    Returns:
        包含 PR 信息的字典
    """
    if token is None:
        token = TOKEN

    if not token:
        raise ValueError("请设置 GITHUB_TOKEN 环境变量或传入 token 参数")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"获取 PR 信息失败: {response.status_code} - {response.text}")


def get_pr_files(owner: str, repo: str, pr_number: int, token: str = None) -> list:
    """
    获取指定 PR 的文件变更列表

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        pr_number: PR 编号
        token: GitHub token（可选，默认使用环境变量）

    Returns:
        包含文件变更信息的列表
    """
    if token is None:
        token = TOKEN

    if not token:
        raise ValueError("请设置 GITHUB_TOKEN 环境变量或传入 token 参数")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"获取 PR 文件列表失败: {response.status_code} - {response.text}")


def print_pr_info(pr_info: dict):
    """打印 PR 基本信息"""
    print("\n=== PR 基本信息 ===")
    print(f"标题: {pr_info['title']}")
    print(f"状态: {pr_info['state']}")
    print(f"作者: {pr_info['user']['login']}")
    print(f"创建时间: {pr_info['created_at']}")
    print(f"更新时间: {pr_info['updated_at']}")
    print(f"源分支: {pr_info['head']['ref']}")
    print(f"目标分支: {pr_info['base']['ref']}")
    print(f"描述: {pr_info['body'] or '无'}")


def print_pr_files(files: list):
    """打印 PR 文件变更信息"""
    print("\n=== 文件变更 ===")
    print(f"共变更 {len(files)} 个文件\n")

    for file in files:
        print(f"文件: {file['filename']}")
        print(f"  状态: {file['status']}")
        print(f"  添加: +{file['additions']} 行")
        print(f"  删除: -{file['deletions']} 行")
        print(f"  变更: {file['changes']} 行")
        if file.get('patch'):
            print(f"  差异预览:")
            # 只显示前10行差异
            patch_lines = file['patch'].split('\n')
            for line in patch_lines[:10]:
                print(f"    {line}")
            if len(patch_lines) > 10:
                remaining_lines = len(patch_lines) - 10
                print(f"    ... (还有 {remaining_lines} 行)")
        print()


def main():
    """命令行脚本入口"""
    try:
        # 获取 PR 信息
        pr_info = get_pr_info(OWNER, REPO, PR_NUMBER)
        print_pr_info(pr_info)

        # 获取文件变更
        files = get_pr_files(OWNER, REPO, PR_NUMBER)
        print_pr_files(files)

    except Exception as e:
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
