"""FingerprintGenerator — SHA256 去重指纹。

用于跨审查去重：相同文件+相同标题+相同类别的 finding 只保留首次出现。
"""

import hashlib

from insightor.schemas.urf import Finding


class FingerprintGenerator:
    """SHA256 去重指纹生成器。"""

    @staticmethod
    def generate(finding: Finding) -> str:
        raw = f"{finding.location.path}|{finding.title}|{finding.category}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def deduplicate(findings: list[Finding]) -> list[Finding]:
        seen: set[str] = set()
        result: list[Finding] = []
        for f in findings:
            fp = FingerprintGenerator.generate(f)
            if fp not in seen:
                seen.add(fp)
                f.fingerprint = fp
                result.append(f)
        return result
