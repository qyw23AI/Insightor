"""
测试 AI API 连接和基本功能
"""
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# 加载环境变量
load_dotenv(dotenv_path="../fetch_pr/.env")

def test_claude_api():
    """测试 Claude API 连接"""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ 错误: 请在 .env 文件中设置 ANTHROPIC_API_KEY")
        return False

    try:
        # 初始化 Anthropic 客户端
        client = Anthropic(api_key=api_key)

        print("🔄 正在测试 Claude API 连接...")

        # 发送一个简单的测试请求
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": "请用一句话介绍你自己，并说明你在代码审查方面的能力。"
                }
            ]
        )

        response_text = message.content[0].text

        print("✅ Claude API 连接成功！")
        print(f"\n📝 Claude 的回复:\n{response_text}")
        print(f"\n📊 Token 使用情况:")
        print(f"   - 输入 tokens: {message.usage.input_tokens}")
        print(f"   - 输出 tokens: {message.usage.output_tokens}")

        return True

    except Exception as e:
        print(f"❌ Claude API 测试失败: {str(e)}")
        return False

def test_code_analysis():
    """测试代码分析功能"""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ 错误: 请在 .env 文件中设置 ANTHROPIC_API_KEY")
        return False

    try:
        client = Anthropic(api_key=api_key)

        print("\n🔄 正在测试代码分析功能...")

        # 测试代码片段
        test_code = """
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price'] * item['quantity']
    return total
"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"""请分析以下 Python 代码，指出：
1. 代码的功能
2. 潜在的问题或风险
3. 改进建议

代码：
```python
{test_code}
```

请用中文回复，格式清晰。"""
                }
            ]
        )

        response_text = message.content[0].text

        print("✅ 代码分析测试成功！")
        print(f"\n📝 分析结果:\n{response_text}")
        print(f"\n📊 Token 使用情况:")
        print(f"   - 输入 tokens: {message.usage.input_tokens}")
        print(f"   - 输出 tokens: {message.usage.output_tokens}")

        return True

    except Exception as e:
        print(f"❌ 代码分析测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AI API 测试工具")
    print("=" * 60)

    # 测试 1: API 连接
    success1 = test_claude_api()

    if success1:
        # 测试 2: 代码分析
        success2 = test_code_analysis()

        if success2:
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！可以开始开发 AI 代码评审工具了。")
            print("=" * 60)
        else:
            print("\n⚠️ 代码分析测试失败，请检查配置。")
    else:
        print("\n⚠️ API 连接测试失败，请检查 API Key 配置。")
