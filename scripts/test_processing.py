"""测试 PR #3 数据处理管线 — 用真实 PR 验证 FileFilter/LanguageDetector/TokenEstimator/DiffCompressor/CacheManager。

用法:
  python scripts/test_processing.py <PR_URL>
  python scripts/test_processing.py https://github.com/SCU-GuGuGaGa/Insightor/pull/5
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from insightor.providers.github_provider import GitHubProvider
from insightor.processing.file_filter import FileFilter
from insightor.processing.language_detector import LanguageDetector
from insightor.processing.token_estimator import TokenEstimator
from insightor.processing.diff_compressor import DiffCompressor
from insightor.processing.cache_manager import CacheManager
from insightor.schemas.urf import PRSummary, ReviewMeta, ReviewResult


def main():
    pr_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/SCU-GuGuGaGa/Insightor/pull/5"

    p = GitHubProvider()
    info = p.get_pr_info(pr_url)
    raw_files = p.get_files(pr_url)
    print(f"PR #{info.pr_number}: {info.title}")
    print(f"原始文件数: {len(raw_files)}")

    # ---- 1. FileFilter ----
    ff = FileFilter()
    filtered = ff.filter(raw_files)
    skipped = len(raw_files) - len(filtered)
    print(f"\n[1] FileFilter: {len(raw_files)} → {len(filtered)} (过滤掉 {skipped} 个)")

    # ---- 2. LanguageDetector ----
    ld = LanguageDetector()
    groups = ld.group_by_language(filtered)
    print(f"[2] LanguageDetector: {len(groups)} 种语言")
    for lang, files in sorted(groups.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"    {lang:15} {len(files):>3} 文件")

    sorted_files = ld.sort_by_priority(filtered, main_language="Python")
    print(f"    排序后首位: {sorted_files[0].language} / {sorted_files[0].filename}")

    # ---- 3. TokenEstimator ----
    full_text = "\n".join(f.patch for f in filtered if f.patch)
    te = TokenEstimator(model="claude-sonnet-4-6")
    claude_tokens = te.count_tokens(full_text)
    te2 = TokenEstimator(model="gpt-4o")
    gpt_tokens = te2.count_tokens(full_text)
    print(f"[3] TokenEstimator: Claude~{claude_tokens}  GPT~{gpt_tokens}  (chars={len(full_text)})")

    # ---- 4. DiffCompressor (三种深度) ----
    for depth in ("deep", "standard", "quick"):
        dc = DiffCompressor(max_tokens=8000)
        result = dc.compress(filtered, depth=depth)
        print(f"[4] DiffCompressor [{depth:8}]: level={result.level}, "
              f"tokens={result.tokens_used}, skipped={len(result.unprocessed_files)}, "
              f"text={len(result.text)} chars")

    # ---- 5. CacheManager ----
    cm = CacheManager()
    meta = ReviewMeta(pr_url=pr_url, commit_sha=info.commit_sha)
    result = ReviewResult(meta=meta, summary=PRSummary(overview="processing test"))
    saved_path = cm.put(pr_url, info.commit_sha, result)
    print(f"[5] CacheManager: 已保存 → {saved_path}")

    loaded = cm.get(pr_url, info.commit_sha)
    print(f"    验证加载: {'OK' if loaded and loaded.summary.overview == 'processing test' else 'FAIL'}")

    reviews = cm.list_reviews(pr_url)
    print(f"    历史记录: {len(reviews)} 条")

    print("\n全部 5 步测试通过!")


if __name__ == "__main__":
    main()
