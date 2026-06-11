#!/usr/bin/env python3
"""
CASCADE 领域知识自动更新器 —— 扫描外部引用、检测过时、生成更新建议。
用法: python cascade_updater.py <skill_dir> [--threshold <days>] [--output <dir>]
      --threshold: 过时阈值天数，默认 90
      --output: 更新建议输出目录，默认 stdout JSON
输出: JSON 过时引用报告，含搜索查询建议。
"""
import sys, json, re, os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── 北京时间 ──
CST = timezone(timedelta(hours=8))

# ── 引用解析 ──
def parse_arxiv_refs(text: str) -> list[dict]:
    """提取 arXiv ID 及其上下文"""
    refs = []
    for m in re.finditer(r"arXiv[:\s]*(\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE):
        refs.append({"type": "arxiv", "id": m.group(1), "context": m.group(0).strip(), "line": text[:m.start()].count("\n") + 1})
    return refs


def parse_url_refs(text: str) -> list[dict]:
    """提取外部 URL 及其上下文"""
    refs = []
    for m in re.finditer(r"\[([^\]]*)\]\((https?://[^\)]+)\)", text):
        label = m.group(1).strip()
        url = m.group(2).strip()
        refs.append({"type": "url", "label": label, "url": url, "line": text[:m.start()].count("\n") + 1})
    return refs


def parse_version_refs(text: str) -> list[dict]:
    """提取版本号引用（API vX, 工具版本等）"""
    refs = []
    for m in re.finditer(r"(?:[Vv]ersion|[Vv])\s*(\d+\.\d+(?:\.\d+)?)", text):
        refs.append({"type": "version", "version": m.group(1), "context": m.group(0).strip(), "line": text[:m.start()].count("\n") + 1})
    return refs


def parse_standard_refs(text: str) -> list[dict]:
    """提取标准/规范引用（RFC, ISO 等）"""
    refs = []
    for pattern, label in [(r"RFC[:\s]*(\d+)", "RFC"), (r"ISO[:\s]*(\d+(?:[:/-]\d+)?)", "ISO")]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            refs.append({"type": "standard", "standard": f"{label} {m.group(1)}", "line": text[:m.start()].count("\n") + 1})
    return refs


# ── 文件时间获取 ──
def get_file_mtime(filepath: Path) -> datetime | None:
    """获取文件的最后修改时间（CST）"""
    try:
        ts = os.path.getmtime(str(filepath))
        return datetime.fromtimestamp(ts, tz=CST)
    except OSError:
        return None


def get_git_last_modified(filepath: Path) -> datetime | None:
    """尝试从 git 获取文件最后提交时间，失败时回退到文件系统 mtime"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(filepath.parent), "log", "-1", "--format=%at", "--", filepath.name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            ts = int(result.stdout.strip())
            return datetime.fromtimestamp(ts, tz=CST)
    except Exception:
        pass
    return get_file_mtime(filepath)


# ── 过时检测 ──
def check_staleness(skill_dir: Path, threshold_days: int) -> dict:
    """扫描所有文件，检测过时引用"""
    now = datetime.now(tz=CST)
    cutoff = now - timedelta(days=threshold_days)

    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return {"error": f"SKILL.md 不存在: {sm}"}

    skill_text = sm.read_text(encoding="utf-8")
    sm_mtime = get_git_last_modified(sm)

    stale_refs = []
    fresh_refs = []

    # arxiv refs
    for ref in parse_arxiv_refs(skill_text):
        last_updated = sm_mtime
        ref["last_updated"] = last_updated.isoformat() if last_updated else "unknown"
        ref["days_since"] = (now - last_updated).days if last_updated else -1
        if last_updated and last_updated < cutoff:
            ref["status"] = "stale"
            ref["search_query"] = f"site:arxiv.org {ref['id']}"
            stale_refs.append(ref)
        else:
            ref["status"] = "fresh"
            fresh_refs.append(ref)

    # url refs
    for ref in parse_url_refs(skill_text):
        last_updated = sm_mtime
        ref["last_updated"] = last_updated.isoformat() if last_updated else "unknown"
        ref["days_since"] = (now - last_updated).days if last_updated else -1
        if last_updated and last_updated < cutoff:
            ref["status"] = "stale"
            ref["search_query"] = f"{ref['label']} latest version update changelog"
            stale_refs.append(ref)
        else:
            ref["status"] = "fresh"
            fresh_refs.append(ref)

    # references/ 文件
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for ref_file in ref_dir.rglob("*"):
            if not ref_file.is_file():
                continue
            rel = str(ref_file.relative_to(skill_dir)).replace("\\", "/")
            mtime = get_git_last_modified(ref_file)
            file_text = ref_file.read_text(encoding="utf-8")
            # extract arXiv refs from reference files
            for ar in parse_arxiv_refs(file_text):
                ar["source_file"] = rel
                ar["last_updated"] = mtime.isoformat() if mtime else "unknown"
                ar["days_since"] = (now - mtime).days if mtime else -1
                if mtime and mtime < cutoff:
                    ar["status"] = "stale"
                    ar["search_query"] = f"site:arxiv.org {ar['id']}"
                    stale_refs.append(ar)
                else:
                    ar["status"] = "fresh"
                    fresh_refs.append(ar)

    # version refs
    for ref in parse_version_refs(skill_text):
        ref["last_updated"] = sm_mtime.isoformat() if sm_mtime else "unknown"
        ref["days_since"] = (now - sm_mtime).days if sm_mtime else -1
        if sm_mtime and sm_mtime < cutoff:
            ref["status"] = "stale"
            ref["search_query"] = f"{ref['version']} changelog release notes"
            stale_refs.append(ref)
        else:
            ref["status"] = "fresh"
            fresh_refs.append(ref)

    # standard refs
    for ref in parse_standard_refs(skill_text):
        ref["last_updated"] = sm_mtime.isoformat() if sm_mtime else "unknown"
        ref["days_since"] = (now - sm_mtime).days if sm_mtime else -1
        if sm_mtime and sm_mtime < cutoff:
            ref["status"] = "stale"
            ref["search_query"] = f"{ref['standard']} latest version"
            stale_refs.append(ref)
        else:
            ref["status"] = "fresh"
            fresh_refs.append(ref)

    return {
        "skill_dir": str(skill_dir),
        "scanned_at": now.isoformat(),
        "threshold_days": threshold_days,
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "skill_last_modified": sm_mtime.isoformat() if sm_mtime else "unknown",
        "total_refs": len(stale_refs) + len(fresh_refs),
        "stale_count": len(stale_refs),
        "fresh_count": len(fresh_refs),
        "stale_refs": stale_refs,
        "fresh_refs": fresh_refs,
    }


# ── 更新建议生成 ──
def generate_update_suggestions(report: dict) -> list[dict]:
    """为每个过时引用生成更新建议"""
    suggestions = []
    for ref in report.get("stale_refs", []):
        sug = {
            "ref_id": ref.get("id") or ref.get("url") or ref.get("standard", "unknown"),
            "type": ref["type"],
            "days_since": ref.get("days_since", -1),
            "source_file": ref.get("source_file", "SKILL.md"),
            "action": "",
            "query": ref.get("search_query", ""),
            "update_instruction": "",
        }
        if ref["type"] == "arxiv":
            sug["action"] = "search_update"
            sug["update_instruction"] = f"web_search('{ref['search_query']}') 检查是否有版本更新或新结论"
        elif ref["type"] == "url":
            sug["action"] = "fetch_and_compare"
            sug["update_instruction"] = f"web_fetch('{ref['url']}') 抓取最新内容，对比差异"
        elif ref["type"] == "standard":
            sug["action"] = "search_update"
            sug["update_instruction"] = f"web_search('{ref['standard']} latest') 检查标准是否有更新"
        suggestions.append(sug)
    return suggestions


def output_update_script(skill_dir: Path, suggestions: list[dict], output_dir: Path | None = None) -> str:
    """生成可执行的更新指引脚本（Markdown 格式）"""
    lines = [
        f"# CASCADE 知识更新指引",
        f"",
        f"**技能目录**：{skill_dir}",
        f"**生成时间**：{datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**过时引用数**：{len(suggestions)}",
        f"",
        "---",
        "",
    ]
    for i, s in enumerate(suggestions, 1):
        lines.append(f"## {i}. {s['ref_id']}（{s['type']}，{s['days_since']} 天未更新）")
        lines.append(f"")
        lines.append(f"- **来源文件**：{s['source_file']}")
        lines.append(f"- **操作**：{s['action']}")
        lines.append(f"- **指令**：`{s['update_instruction']}`")
        lines.append(f"")
        lines.append(f"**落地方案**：更新后追加到 `{s['source_file']}`，格式：")
        lines.append(f"```markdown")
        lines.append(f"## [{datetime.now().strftime('%Y-%m-%d')}] CASCADE 自动更新：{s['ref_id']}")
        lines.append(f"")
        lines.append(f"[最新内容摘要]")
        lines.append(f"```")
        lines.append("")

    content = "\n".join(lines)
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "cascade_update_guide.md"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path)
    return content


# ── 主入口 ──
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python cascade_updater.py <skill_dir> [--threshold <days>] [--output <dir>]"}, ensure_ascii=False))
        sys.exit(1)

    sd = Path(sys.argv[1]).resolve()
    threshold = 90
    output_dir = None

    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        if idx + 1 < len(sys.argv):
            try:
                threshold = int(sys.argv[idx + 1])
            except ValueError:
                pass
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])

    report = check_staleness(sd, threshold)
    if "error" in report:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)
    suggestions = generate_update_suggestions(report)
    report["suggestions"] = suggestions

    if output_dir:
        guide_path = output_update_script(sd, suggestions, output_dir)
        report["update_guide"] = guide_path

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
