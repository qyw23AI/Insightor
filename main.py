"""
AI 代码评审工具 - 命令行入口
"""
import argparse
import sys
from pathlib import Path

from ai_reviewer.reviewer import PRReviewer


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI 代码评审工具 - 使用 Claude AI 自动评审 GitHub PR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 评审指定 PR
  python main.py --owner qyw23AI --repo Insightor --pr 1

  # 通过 URL 评审
  python main.py --url https://github.com/qyw23AI/Insightor/pull/1

  # 执行安全审查
  python main.py --owner qyw23AI --repo Insightor --pr 1 --type security

  # 保存报告到文件
  python main.py --owner qyw23AI --repo Insightor --pr 1 --output report.md

  # 指定本地仓库路径（可读取完整文件内容）
  python main.py --owner qyw23AI --repo Insightor --pr 1 --repo-path ./
        """
    )

    # PR 信息参数
    pr_group = parser.add_mutually_exclusive_group(required=True)
    pr_group.add_argument(
        '--url',
        type=str,
        help='PR URL (例如: https://github.com/owner/repo/pull/123)'
    )
    pr_group.add_argument(
        '--owner',
        type=str,
        help='仓库所有者'
    )

    parser.add_argument(
        '--repo',
        type=str,
        help='仓库名称（与 --owner 一起使用）'
    )
    parser.add_argument(
        '--pr',
        type=int,
        help='PR 编号（与 --owner 一起使用）'
    )

    # 评审选项
    parser.add_argument(
        '--type',
        type=str,
        nargs='+',
        choices=['comprehensive', 'security', 'performance', 'quality'],
        default=['comprehensive'],
        help='评审类型（可多选，默认: comprehensive）'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='输出文件路径（支持 .md 和 .json）'
    )
    parser.add_argument(
        '--repo-path',
        type=str,
        help='本地仓库路径（可选，用于读取完整文件内容）'
    )

    # AI 模型参数
    parser.add_argument(
        '--model',
        type=str,
        default='claude-opus-4-8',
        help='AI 模型名称（默认: claude-opus-4-8）'
    )
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=4096,
        help='最大输出 token 数（默认: 4096）'
    )

    args = parser.parse_args()

    # 验证参数
    if args.owner and (not args.repo or not args.pr):
        parser.error("使用 --owner 时必须同时指定 --repo 和 --pr")

    try:
        # 创建评审器
        reviewer = PRReviewer(
            repo_path=args.repo_path,
            model=args.model,
            max_tokens=args.max_tokens
        )

        # 执行评审
        if args.url:
            result = reviewer.review_pr_by_url(args.url, args.type)
        else:
            result = reviewer.review_pr(args.owner, args.repo, args.pr, args.type)

        # 输出结果
        if args.output:
            # 根据文件扩展名确定格式
            output_path = Path(args.output)
            if output_path.suffix == '.json':
                format_type = 'json'
            else:
                format_type = 'markdown'

            reviewer.save_report(result, str(output_path), format_type)
        else:
            # 打印到控制台
            print("\n" + "=" * 60)
            print("📝 评审结果")
            print("=" * 60)

            if 'summary' in result['reviews']:
                print("\n## 总结\n")
                print(result['reviews']['summary'])

            for review_type, content in result['reviews'].items():
                if review_type != 'summary':
                    print(f"\n## {review_type.upper()}\n")
                    print(content)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
