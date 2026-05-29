import requests
import sys
from dotenv import load_dotenv
import os

load_dotenv()  # 自动加载 .env

# ===== 配置信息 =====
OWNER = os.getenv("OWNER", "qyw23AI")
REPO = os.getenv("REPO", "Insightor")
PR_NUMBER = int(os.getenv("PR_NUMBER", "1"))
TOKEN = os.getenv("GITHUB_TOKEN")
# ===================

if not TOKEN:
    print("❌ 错误: 请在 .env 文件中设置 GITHUB_TOKEN")
    print("在 fetch_pr/.env 文件中添加:")
    print("GITHUB_TOKEN=your_github_token_here")
    sys.exit(1)

url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/files"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    files = response.json()

    print(f"\n📋 PR #{PR_NUMBER} 的文件变更 ({OWNER}/{REPO})")
    print(f"共 {len(files)} 个文件\n")

    for file in files:
        print("=" * 50)
        print(f"📄 文件名: {file['filename']}")
        print(f"📝 修改类型: {file['status']}")
        print(f"➕ 新增行数: {file['additions']}")
        print(f"➖ 删除行数: {file['deletions']}")
        print(f"🔄 总变更: {file['changes']}")

        patch = file.get("patch")

        if patch:
            print("\n💻 Diff:")
            print(patch)
        else:
            print("\n(无 diff 内容，可能是二进制文件或文件过大)")

        print()

    print("=" * 50)
    print("✅ 完成")

except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP 错误: {e}")
    print(f"响应内容: {response.text}")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"❌ 请求错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 未知错误: {e}")
    sys.exit(1)
