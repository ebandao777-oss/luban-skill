#!/usr/bin/env python3
"""
SkillOps 工具化扫描器 —— 对技能目录做结构化静态检查。
用法: python skillops_scanner.py <skill_dir>
输出: JSON 诊断报告。
"""
import sys, json, re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import socket

URL_TIMEOUT = 10
HEADERS = {"User-Agent": "SkillOps-Scanner/1.0"}

# ── YAML frontmatter 检查 ──
def check_frontmatter(filepath: Path) -> list[dict]:
    issues = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [{"file": str(filepath), "severity": "critical", "issue": f"无法读取: {e}"}]
    if not text.startswith("---"):
        issues.append({"file": str(filepath), "severity": "critical", "issue": "缺少 YAML frontmatter"})
        return issues
    parts = text.split("---", 2)
    if len(parts) < 3:
        issues.append({"file": str(filepath), "severity": "critical", "issue": "frontmatter 未正确闭合"})
        return issues
    yb = parts[1].strip()
    for field in ["name", "description"]:
        if not re.search(rf"^{field}\s*:", yb, re.MULTILINE):
            issues.append({"file": str(filepath), "severity": "high", "issue": f"缺少必需字段: {field}"})
    desc = re.search(r"^description\s*:\s*(.+)", yb, re.MULTILINE)
    if desc and len(desc.group(1)) > 1024:
        issues.append({"file": str(filepath), "severity": "warning", "issue": "description 超过 1024 字符"})
    name = re.search(r"^name\s*:\s*(.+)", yb, re.MULTILINE)
    if name and " " in name.group(1).strip():
        issues.append({"file": str(filepath), "severity": "warning", "issue": "name 含空格"})
    return issues

# ── 路径断裂检查 ──
def check_paths(skill_dir: Path) -> list[dict]:
    issues = []
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return [{"file": str(sm), "severity": "critical", "issue": "SKILL.md 不存在"}]
    text = sm.read_text(encoding="utf-8")
    for link_text, url in re.findall(r"\[([^\]]*)\]\(([^\)]+)\)", text):
        if url.startswith(("http://", "https://", "#")):
            continue
        target = (skill_dir / url).resolve()
        if not target.exists():
            issues.append({"file": str(sm), "severity": "high",
                           "issue": f"断裂: [{link_text}]({url}) → {target} 不存在", "location": url})
    return issues

# ── 引用链分析 ──
def check_ref_chain(skill_dir: Path) -> dict:
    sm = skill_dir / "SKILL.md"
    ref_dir = skill_dir / "references"
    result = {"references": [], "uncited": [], "missing": []}
    if not sm.exists():
        return result
    text = sm.read_text(encoding="utf-8")
    cited = {m.group(1) for m in re.finditer(r"references/([\w\-\/\.]+)", text)}
    if ref_dir.exists():
        for f in ref_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(ref_dir)).replace("\\", "/")
                result["references"].append({"file": rel, "cited": rel in cited})
                if rel not in cited:
                    result["uncited"].append(rel)
    for c in cited:
        if not (ref_dir / c).exists():
            result["missing"].append(c)
    return result

# ── 外部链接检查 ──
def check_urls(skill_dir: Path) -> list[dict]:
    issues = []
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return issues
    text = sm.read_text(encoding="utf-8")
    urls = set()
    for _, url in re.findall(r"\[([^\]]*)\]\(([^\)]+)\)", text):
        if url.startswith("http"):
            urls.add(url)
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for rf in ref_dir.rglob("*.md"):
            for _, url in re.findall(r"\[([^\]]*)\]\(([^\)]+)\)", rf.read_text(encoding="utf-8")):
                if url.startswith("http"):
                    urls.add(url)
    for url in sorted(urls):
        try:
            req = Request(url, headers=HEADERS)
            resp = urlopen(req, timeout=URL_TIMEOUT)
            if resp.status >= 400:
                issues.append({"file": "external", "severity": "warning",
                               "issue": f"HTTP {resp.status}: {url}"})
        except URLError as e:
            issues.append({"file": "external", "severity": "warning",
                           "issue": f"不可达: {url} ({e.reason})"})
        except socket.timeout:
            issues.append({"file": "external", "severity": "warning",
                           "issue": f"超时: {url}"})
    return issues

# ── 主入口 ──
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python skillops_scanner.py <skill_dir>"}, ensure_ascii=False))
        sys.exit(1)
    sd = Path(sys.argv[1]).resolve()
    if not sd.exists():
        print(json.dumps({"error": f"目录不存在: {sd}"}, ensure_ascii=False))
        sys.exit(1)
    sm = sd / "SKILL.md"
    if not sm.exists():
        print(json.dumps({"error": f"SKILL.md 不存在: {sm}"}, ensure_ascii=False))
        sys.exit(1)
    report = {
        "skill_dir": str(sd),
        "frontmatter": check_frontmatter(sd / "SKILL.md"),
        "broken_paths": check_paths(sd),
        "reference_chain": check_ref_chain(sd),
        "external_links": check_urls(sd),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
