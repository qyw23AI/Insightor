"""
测试 Claude API 连接和基本功能
"""
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# 加载环境变量
load_dotenv()

def test_claude_api():
    """测试 Claude API 基本连接"""
    print("=== 测试 Claude API 连接 ===\n")

    # 获取 API 配置
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not api_key:
        print("❌ 错误：未找到 ANTHROPIC_API_KEY 环境变量")
        print("请在 .env 文件中设置 ANTHROPIC_API_KEY")
        return False

    print(f"✓ API Key: {api_key[:20]}...")
    if base_url:
        print(f"✓ Base URL: {base_url}")

    try:
        # 初始化客户端，支持自定义 base_url
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = Anthropic(**client_kwargs)

        # 尝试多个可能的模型名称
        models_to_try = [
            "claude-opus-4-8",
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022",
            "claude-3-sonnet-20240229"
        ]

        for model in models_to_try:
            print(f"\n尝试模型: {model}")
            try:
                message = client.messages.create(
                    model=model,
                    max_tokens=100,
                    messages=[
                        {"role": "user", "content": "Hello! Please respond with 'API connection successful'."}
                    ]
                )

                print(f"✓ 成功！模型 {model} 可用")
                print(f"响应: {message.content[0].text}")
                print(f"Token 使用: input={message.usage.input_tokens}, output={message.usage.output_tokens}")
                return True

            except Exception as e:
                print(f"✗ 模型 {model} 失败: {str(e)}")
                continue

        print("\n❌ 所有模型都失败了")
        return False

    except Exception as e:
        print(f"\n❌ API 连接失败: {str(e)}")
        return False

def test_code_analysis():
    """测试代码分析功能"""
    print("\n\n=== 测试代码分析功能 ===\n")

    # 获取 API 配置
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not api_key:
        print("❌ 错误：未找到 ANTHROPIC_API_KEY 环境变量")
        return False

    try:
        # 初始化客户端，支持自定义 base_url
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = Anthropic(**client_kwargs)

        # 示例代码
        sample_code = """
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price'] * item['quantity']
    return total
"""

        print("分析以下代码：")
        print(sample_code)
        print("\n正在分析...")

        message = client.messages.create(
            model="claude-opus-4-8",  # 使用用户确认的模型
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": f"请分析以下 Python 代码，指出潜在问题并提供改进建议：\n\n{sample_code}"
                }
            ]
        )

        print("\n分析结果：")
        print(message.content[0].text)
        print(f"\nToken 使用: input={message.usage.input_tokens}, output={message.usage.output_tokens}")
        return True

    except Exception as e:
        print(f"\n❌ 代码分析失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 运行测试
    api_ok = test_claude_api()

    if api_ok:
        test_code_analysis()
    else:
        print("\n⚠️  API 连接测试失败，跳过代码分析测试")
