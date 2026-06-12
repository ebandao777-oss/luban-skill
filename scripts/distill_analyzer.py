#!/usr/bin/env python3
"""
Skill Distill 引用矩阵分析器 —— 计算指标自由度 F_approx，生成精简建议。
用法: python distill_analyzer.py <skill_dir>
输出: JSON，包含每个 references 文件的 F_approx 评分和精简建议。
"""
import sys, json, re
from pathlib import Path

def extract_ref_citations(skill_md_text: str, ref_dir: Path) -> dict[str, int]:
    """统计每个 references 文件被 SKILL.md 引用的次数"""
    citations: dict[str, int] = {}
    for ref_file in ref_dir.rglob("*"):
        if not ref_file.is_file():
            continue
        rel = str(ref_file.relative_to(ref_dir)).replace("\\", "/")
        citations[rel] = 0
        # 统计 SKILL.md 中引用该文件的次数
        patterns = [
            rf"references/{re.escape(rel)}",
            rf"\[.*?\]\(.*?{re.escape(rel)}.*?\)",
        ]
        for p in patterns:
            citations[rel] += len(re.findall(p, skill_md_text))
    return citations

def compute_f_approx(citations: dict[str, int], ref_dir: Path) -> list[dict]:
    """
    F_approx = 1 - (被引用次数 / (文件字符数归一化))
    归一化: 字符数 / max(所有文件字符数)
    """
    if not ref_dir.exists():
        return []

    file_sizes: dict[str, int] = {}
    for ref_file in ref_dir.rglob("*"):
        if ref_file.is_file():
            rel = str(ref_file.relative_to(ref_dir)).replace("\\", "/")
            file_sizes[rel] = len(ref_file.read_text(encoding="utf-8"))

    if not file_sizes:
        return []

    mean_size = sum(file_sizes.values()) / len(file_sizes) if file_sizes else 1
    mean_size = max(mean_size, 100)  # SKILL.md 约定：分母过小取 max(均值, 100)
    results = []

    for rel, size in sorted(file_sizes.items(), key=lambda x: x[1], reverse=True):
        normalized_size = size / mean_size if mean_size > 0 else 1.0
        cite_count = citations.get(rel, 0)
        # 引用密度: 被引用次数 / 归一化大小
        density = cite_count / normalized_size if normalized_size > 0 else 0
        f_approx = round(1.0 - (cite_count / (normalized_size + 1e-6)), 3)
        f_approx = max(0.0, min(1.0, f_approx))

        priority = ""
        if f_approx >= 0.7:
            priority = "P0-可精简"
        elif f_approx >= 0.5:
            priority = "P1-考虑精简"
        elif f_approx <= 0.3:
            priority = "核心资产-保留"
        else:
            priority = "正常"

        results.append({
            "file": rel,
            "size_chars": size,
            "normalized_size": round(normalized_size, 3),
            "citations": cite_count,
            "f_approx": f_approx,
            "priority": priority,
        })

    return results

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python distill_analyzer.py <skill_dir>"}, ensure_ascii=False))
        sys.exit(1)

    sd = Path(sys.argv[1]).resolve()
    sm = sd / "SKILL.md"
    ref_dir = sd / "references"

    if not sm.exists():
        print(json.dumps({"error": f"SKILL.md 不存在: {sm}"}, ensure_ascii=False))
        sys.exit(1)

    text = sm.read_text(encoding="utf-8")
    citations = extract_ref_citations(text, ref_dir)
    results = compute_f_approx(citations, ref_dir)

    total_size = sum(r["size_chars"] for r in results)
    p0_count = sum(1 for r in results if r["priority"] == "P0-可精简")

    report = {
        "skill_dir": str(sd),
        "total_refs": len(results),
        "total_size_chars": total_size,
        "p0_count": p0_count,
        "analysis": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
