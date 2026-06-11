#!/usr/bin/env python3
"""
HASP 规则硬化器 —— 分析执行日志，识别被忽略的软规则，生成 hardening 建议。
用法: python hasp_hardener.py <skill_dir> [--results <results.tsv>] [--log <execution_log.json>] [--output <report.json>] [--apply] [--dry-run]
      --results: results.tsv 路径（用于提取违规历史），默认 skill_dir/results.tsv
      --log: 执行日志 JSON 路径
      --output: 报告输出路径，默认 skill_dir/hardening_report.json
      --apply: 将硬化建议实际写入 SKILL.md（含备份）
      --dry-run: 模拟 apply，只报告不写入
输出: JSON 硬化建议报告。
"""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── 中文分词 ──
try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False

CST = timezone(timedelta(hours=8))

# ── 软规则检测 ──
SOFT_RULE_PATTERNS = [
    (r"建议(?!\s*(?:升级|安装|使用))", "建议句式"),
    (r"可以(?:考虑|选择|参考)", "软化建议"),
    (r"根据情况", "模糊兜底"),
    (r"是可选的", "可选声明"),
    (r"视情况而定", "弹性策略"),
    (r"(?:通常|一般|大多数)情况下", "非强制条件"),
    (r"如果(?:需要|必要|方便)的话", "条件软化"),
]

# ── 硬化适用性判断表（基于 SKILL.md 定义的规则类型） ──
HARDENABLE_CONDITIONS = {
    "输出格式约束": True,
    "文件大小限制": True,
    "必须包含的章节/字段": True,
    "触发词列表": True,
    "语义风格约束": False,
    "创造性建议": False,
    "自由度高的排版": False,
}


def extract_soft_rules(skill_text: str) -> list[dict]:
    """从 SKILL.md 提取所有软规则（建议/可以/模糊措辞）"""
    rules = []
    for lineno, line in enumerate(skill_text.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            continue
        for pattern, rule_type in SOFT_RULE_PATTERNS:
            if re.search(pattern, stripped):
                rules.append({
                    "line": lineno,
                    "text": stripped[:200],
                    "rule_type": rule_type,
                    "hardenable": _check_hardenable(stripped),
                })
                break
    return rules


def _check_hardenable(text: str) -> bool:
    """根据文本内容判断是否适合硬化"""
    if re.search(r"(?:输出|格式|章节|字段|文件大小|触发词|必须包含|强制|限制|≤|>=|<|>)", text):
        return True
    if re.search(r"(?:风格|创意|灵感|审美|感受|偏好)", text):
        return False
    return True  # 默认可尝试


def extract_hard_rules(skill_text: str) -> list[dict]:
    """提取已存在的 hard_rules"""
    fm_match = re.search(r"^---\s*\n(.*?)\n---", skill_text, re.DOTALL)
    if not fm_match:
        return []
    frontmatter = fm_match.group(1)
    rules = []
    # 尝试匹配 hard_rules 块
    hr_match = re.search(r"hard_rules\s*:\s*\n((?:\s+-.+\n?)+)", frontmatter)
    if hr_match:
        block = hr_match.group(1)
        for m in re.finditer(r"-\s*id\s*:\s*(.+?)\n(?:\s*should_activate\s*:\s*(.+?)\n)?", block):
            rules.append({"id": m.group(1).strip(), "should_activate": (m.group(2) or "").strip()})
    return rules


def parse_results_tsv(tsv_path: Path) -> list[dict]:
    """解析 results.tsv 提取违规记录"""
    records = []
    if not tsv_path.exists():
        return records
    lines = tsv_path.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) < 2:
        return records
    headers = lines[0].split("\t")
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) >= len(headers):
            rec = dict(zip(headers, fields))
            records.append(rec)
    return records


def find_violations(skill_text: str, results: list[dict], log_data: dict | None) -> list[dict]:
    """从历史数据中找出规则违规实例"""
    violations = []
    soft_rules = extract_soft_rules(skill_text)

    # 从 results.tsv 中找失败/回滚记录
    for rec in results:
        status = rec.get("status", "").lower()
        if status in ("revert", "rollback", "failed", "failure"):
            note = rec.get("note", "")
            dim = rec.get("dimension", "")
            # 关联到软规则（语义分词匹配）
            for rule in soft_rules:
                rule_keywords = _tokenize(rule["text"])
                note_keywords = _tokenize(note)
                overlap = rule_keywords & note_keywords
                if len(overlap) >= 2:
                    violations.append({
                        "rule_line": rule["line"],
                        "rule_text": rule["text"][:120],
                        "violated_at": rec.get("timestamp", ""),
                        "dimension": dim,
                        "context": note[:120],
                        "violation_count": 1,
                    })
                    break

    # 从日志中提取
    if log_data:
        log_entries = log_data.get("entries", log_data.get("failures", []))
        for entry in log_entries:
            entry_text = entry.get("message", entry.get("error", str(entry)))
            for rule in soft_rules:
                if _text_overlap(rule["text"], entry_text):
                    violations.append({
                        "rule_line": rule["line"],
                        "rule_text": rule["text"][:120],
                        "violated_at": entry.get("timestamp", ""),
                        "context": entry_text[:120],
                        "violation_count": 1,
                    })

    # 合并同一规则的多次违规
    merged: dict[int, dict] = {}
    for v in violations:
        line = v["rule_line"]
        if line in merged:
            merged[line]["violation_count"] += 1
        else:
            merged[line] = v
    return list(merged.values())


# ── 跑分弱项分析 ──

def find_score_gaps(results: list[dict]) -> list[dict]:
    """从 test_executor 的 fail 记录中提取可自动修复的弱项"""
    gaps = []
    for rec in results:
        status = rec.get("status", "").lower()
        if status not in ("fail", "revert"):
            continue

        note = rec.get("note", "")
        dim = rec.get("dimension", "")
        tid = rec.get("test_id", "")

        # 触发词缺失
        m = re.search(r"触发词 '(.+?)' 未在SKILL\.md中找到", note)
        if m:
            gaps.append({
                "type": "missing_trigger",
                "test_id": tid,
                "dimension": dim,
                "trigger_word": m.group(1),
                "note": note,
            })
            continue

        # 格式约束缺失
        m = re.search(r"格式约束 '(.+?)' 未在SKILL\.md中体现", note)
        if m:
            gaps.append({
                "type": "missing_format",
                "test_id": tid,
                "dimension": dim,
                "constraint": m.group(1),
                "note": note,
            })
            continue

        # 规则关键词不足（不可自动修复，仅报告）
        m = re.search(r"规则关键词仅匹配", note)
        if m:
            gaps.append({
                "type": "weak_rule",
                "test_id": tid,
                "dimension": dim,
                "note": note,
                "auto_fixable": False,
            })
            continue

        # 引用文件缺失（不可自动修复）
        m = re.search(r"引用文件 (.+?) 不存在", note)
        if m:
            gaps.append({
                "type": "missing_ref",
                "test_id": tid,
                "dimension": dim,
                "file": m.group(1),
                "note": note,
                "auto_fixable": False,
            })
            continue

        # 未识别类型
        gaps.append({
            "type": "unknown",
            "test_id": tid,
            "dimension": dim,
            "note": note,
            "auto_fixable": False,
        })

    return gaps


def apply_score_gaps(skill_path: Path, gaps: list[dict], dry_run: bool = False) -> dict:
    """自动修复跑分弱项"""
    text = skill_path.read_text(encoding="utf-8")
    fixed_triggers = 0
    fixed_formats = 0

    for gap in gaps:
        if gap["type"] == "missing_trigger" and gap.get("auto_fixable", True):
            tw = gap["trigger_word"]
            # 跳过反例测试（如"写一段完全无关的…"）
            if len(tw) > 30 or "无关" in tw or "反" in gap.get("test_id", ""):
                continue
            # 如果触发词已在文本中（假阳性），跳过
            if tw in text:
                continue
            # 追加到 description 行（在末尾引号之前插入）
            desc_match = re.search(r'^description\s*:\s*"(.+)"\s*$', text, re.MULTILINE)
            if desc_match:
                inner = desc_match.group(1)
                new_inner = inner.rstrip() + '，"' + tw + '"'
                text = text.replace(desc_match.group(0),
                                    f'description: "{new_inner}"', 1)
                fixed_triggers += 1

        elif gap["type"] == "missing_format" and gap.get("auto_fixable", True):
            constraint = gap["constraint"]
            # 在 SKILL.md 末尾添加格式说明（如果不存在）
            if constraint not in text:
                text = text.rstrip() + f"\n\n## 输出格式\n- {constraint}\n"
                fixed_formats += 1

    if not dry_run and (fixed_triggers or fixed_formats):
        backup = skill_path.with_suffix(skill_path.suffix + ".gap.bak")
        backup.write_text(skill_path.read_text(encoding="utf-8"), encoding="utf-8")
        skill_path.write_text(text, encoding="utf-8")

    return {
        "fixed_triggers": fixed_triggers,
        "fixed_formats": fixed_formats,
        "total_fixable": sum(1 for g in gaps if g.get("auto_fixable", True)),
    }


def _tokenize(text: str) -> set[str]:
    """中文分词，优先 jieba，降级到固定窗口切片"""
    if _JIEBA_AVAILABLE:
        words = jieba.lcut(text)
        # 过滤单字和纯标点
        return {w.strip() for w in words if len(w.strip()) >= 2 and not re.fullmatch(r"[\s\d\W_]+", w)}
    # 降级：2-6 字符窗口切片
    return set(re.findall(r"[\u4e00-\u9fff]{2,6}", text))

def _text_overlap(a: str, b: str, min_overlap: int = 2) -> bool:
    """检查两段文本的关键词重叠"""
    kw_a = _tokenize(a)
    kw_b = _tokenize(b)
    return len(kw_a & kw_b) >= min_overlap


# ── 硬化建议生成 ──
def generate_hardening(skill_text: str, violations: list[dict]) -> list[dict]:
    """生成分级硬化建议"""
    suggestions = []
    soft_rules = extract_soft_rules(skill_text)
    violation_lines = {v["rule_line"] for v in violations}

    for rule in soft_rules:
        if not rule["hardenable"]:
            continue

        count = 0
        for v in violations:
            if v["rule_line"] == rule["line"]:
                count = v.get("violation_count", 1)
                break

        tier = ""
        if count == 0 and rule["line"] not in violation_lines:
            tier = "T0-基线"
        elif count == 1:
            tier = "T0-基线"
        elif count == 2:
            tier = "T1-措辞强化"
        elif count >= 3:
            tier = "T2-PF硬化"

        if tier == "T0-基线":
            continue  # 未违规或仅违规1次，不生成建议

        sug = {
            "rule_line": rule["line"],
            "rule_text": rule["text"][:150],
            "rule_type": rule["rule_type"],
            "violation_count": count,
            "tier": tier,
            "hardenable": rule["hardenable"],
        }

        if tier == "T1-措辞强化":
            hardened_text = rule["text"]
            hardened_text = re.sub(r"建议", "必须", hardened_text)
            hardened_text = re.sub(r"可以(?:考虑|选择|参考)", "必须", hardened_text)
            hardened_text = re.sub(r"根据情况", "明确按以下步骤", hardened_text)
            hardened_text = re.sub(r"是可选的", "是强制必需的", hardened_text)
            sug["hardened_text"] = hardened_text[:200]
            sug["action"] = "replace_soft_with_must"
            sug["instruction"] = f"将行 {rule['line']} 的软规则替换为强制规则"

        elif tier == "T2-PF硬化":
            rule_id = f"rule_{rule['line']:03d}"
            # 提取激活条件
            condition = _extract_activating_condition(rule["text"])
            sug["pf_definition"] = {
                "id": rule_id,
                "should_activate": condition,
                "intervene": {
                    "type": "block_and_warn",
                    "action": f"违反规则: {rule['text'][:80]}",
                },
                "severity": "high" if count >= 5 else "medium",
                "last_violated": datetime.now(tz=CST).strftime("%Y-%m-%d"),
                "violation_count": count,
            }
            sug["action"] = "inject_pf_rule"
            sug["instruction"] = f"在 SKILL.md frontmatter 的 hard_rules 中注入 PF 规则 {rule_id}"
            sug["hardened_text"] = f"强制: {rule['text'][:150]}"

        suggestions.append(sug)

    # 按违规次数降序
    suggestions.sort(key=lambda x: x["violation_count"], reverse=True)
    return suggestions


def _extract_activating_condition(text: str) -> str:
    """从规则文本中提取触发条件"""
    # 尝试匹配"当/如果/若"句式
    cond = re.search(r"(?:当|如果|若)(.+?)(?:时|，|,|则|应)", text)
    if cond:
        return cond.group(1).strip()[:100]
    # 尝试匹配条件描述
    cond2 = re.search(r"(?:在|遇到|出现)(.+?)(?:时|场景|情况)", text)
    if cond2:
        return cond2.group(1).strip()[:100]
    return "相关场景发生"


def apply_hardening(skill_path: Path, suggestions: list[dict], dry_run: bool = False) -> dict:
    """将硬化建议写入 SKILL.md"""
    text = skill_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    applied_t1 = 0
    applied_t2 = 0
    pf_defs = []

    for sug in suggestions:
        if sug["tier"] == "T1-措辞强化":
            line_no = sug["rule_line"] - 1  # 0-based
            if 0 <= line_no < len(lines):
                old = lines[line_no]
                # 在行内做措辞替换（保留表格结构，只换措辞）
                new = old
                new = re.sub(r"建议", "必须", new)
                new = re.sub(r"可以(?:考虑|选择|参考)", "必须", new)
                new = re.sub(r"根据情况", "明确按以下步骤", new)
                if new != old:
                    lines[line_no] = new
                    applied_t1 += 1

        elif sug["tier"] == "T2-PF硬化":
            pf = sug.get("pf_definition", {})
            if pf:
                pf_defs.append(pf)
                applied_t2 += 1

    # T2: 注入 PF 规则到 frontmatter
    if pf_defs:
        fm_match = re.search(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
        if fm_match:
            fm_body = fm_match.group(2)
            # 已有 hard_rules 块则追加，否则新建
            hr_match = re.search(r"(hard_rules\s*:\s*\n)", fm_body)
            if hr_match:
                insert_pos = fm_match.start(1) + hr_match.end()
                indent = "    "
                for pf in pf_defs:
                    lines.insert(
                        lines[:fm_match.end(3)].count("\n") if "\n".join(lines).find(hr_match.group(1)) >= 0 else 0,
                        f"{indent}- id: {pf['id']}\n"
                        f"{indent}  should_activate: {pf['should_activate']}\n"
                        f"{indent}  intervene: {pf['intervene']}\n"
                        f"{indent}  severity: {pf['severity']}"
                    )
                # Actually, simpler approach: rebuild the frontmatter block
                pf_yaml_lines = []
                for pf in pf_defs:
                    pf_yaml_lines.append(f"  - id: {pf['id']}")
                    pf_yaml_lines.append(f"    should_activate: {pf['should_activate']}")
                    pf_yaml_lines.append(f"    intervene:")
                    pf_yaml_lines.append(f"      type: {pf['intervene']['type']}")
                    pf_yaml_lines.append(f"      action: \"{pf['intervene']['action']}\"")
                    pf_yaml_lines.append(f"    severity: {pf['severity']}")
                    pf_yaml_lines.append(f"    last_violated: {pf.get('last_violated','')}")
                    pf_yaml_lines.append(f"    violation_count: {pf.get('violation_count',0)}")

                # Replace the closing --- to inject hard_rules before it
                closing = fm_match.end(3)
                injection = "hard_rules:\n" + "\n".join(pf_yaml_lines) + "\n"
                lines.insert(lines.index("---", fm_match.start(1) + 1), injection.rstrip("\n"))
            else:
                # 新建 hard_rules 在 frontmatter 内
                pf_yaml_lines = ["hard_rules:"]
                for pf in pf_defs:
                    pf_yaml_lines.append(f"  - id: {pf['id']}")
                    pf_yaml_lines.append(f"    should_activate: {pf['should_activate']}")
                    pf_yaml_lines.append(f"    intervene:")
                    pf_yaml_lines.append(f"      type: {pf['intervene']['type']}")
                    pf_yaml_lines.append(f"      action: \"{pf['intervene']['action']}\"")
                    pf_yaml_lines.append(f"    severity: {pf['severity']}")
                    pf_yaml_lines.append(f"    last_violated: {pf.get('last_violated','')}")
                    pf_yaml_lines.append(f"    violation_count: {pf.get('violation_count',0)}")
                insert_at = lines.index("---", 1)  # 第二个 ---
                for i, pf_line in enumerate(pf_yaml_lines):
                    lines.insert(insert_at + i, pf_line)

    result_text = "\n".join(lines)
    if not dry_run:
        # 备份
        backup = skill_path.with_suffix(skill_path.suffix + ".bak")
        backup.write_text(text, encoding="utf-8")
        skill_path.write_text(result_text, encoding="utf-8")

    return {
        "applied_t1": applied_t1,
        "applied_t2": applied_t2,
        "backup": str(backup) if not dry_run else None,
        "applied_lines": [s["rule_line"] for s in suggestions if s["tier"] in ("T1-措辞强化", "T2-PF硬化")],
    }


# ── 主入口 ──
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python hasp_hardener.py <skill_dir> [--results <tsv>] [--log <json>] [--output <json>] [--apply] [--dry-run]"}, ensure_ascii=False))
        sys.exit(1)

    sd = Path(sys.argv[1]).resolve()
    sm = sd / "SKILL.md"

    if not sm.exists():
        print(json.dumps({"error": f"SKILL.md 不存在: {sm}"}, ensure_ascii=False))
        sys.exit(1)

    skill_text = sm.read_text(encoding="utf-8")
    soft_rules = extract_soft_rules(skill_text)
    existing_hard = extract_hard_rules(skill_text)

    # 加载结果和历史
    results = []
    log_data = None

    if "--results" in sys.argv:
        idx = sys.argv.index("--results")
        if idx + 1 < len(sys.argv):
            results = parse_results_tsv(Path(sys.argv[idx + 1]))
    else:
        default_tsv = sd / "results.tsv"
        results = parse_results_tsv(default_tsv)

    if "--log" in sys.argv:
        idx = sys.argv.index("--log")
        if idx + 1 < len(sys.argv):
            log_path = Path(sys.argv[idx + 1])
            if log_path.exists():
                log_data = json.loads(log_path.read_text(encoding="utf-8"))

    violations = find_violations(skill_text, results, log_data)
    suggestions = generate_hardening(skill_text, violations)

    t1_count = sum(1 for s in suggestions if s["tier"] == "T1-措辞强化")
    t2_count = sum(1 for s in suggestions if s["tier"] == "T2-PF硬化")

    report = {
        "skill_dir": str(sd),
        "skill_name": sm.stem,
        "scanned_at": datetime.now(tz=CST).isoformat(),
        "summary": {
            "total_soft_rules": len(soft_rules),
            "hardening_candidates": len(suggestions),
            "t1_wording_strengthen": t1_count,
            "t2_pf_injection": t2_count,
            "existing_hard_rules": len(existing_hard),
            "total_violations_found": len(violations),
        },
        "soft_rules": soft_rules,
        "existing_hard_rules": existing_hard,
        "violations": violations,
        "suggestions": suggestions,
    }

    # 写入报告
    output_path = sd / "hardening_report.json"
    if "--output" in sys.argv:
        oi = sys.argv.index("--output")
        if oi + 1 < len(sys.argv):
            output_path = Path(sys.argv[oi + 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 硬化应用
    if "--apply" in sys.argv or "--dry-run" in sys.argv:
        dry = "--dry-run" in sys.argv

        # 跑分弱项自动修复
        score_gaps = find_score_gaps(results)
        report["score_gaps"] = score_gaps
        gap_fix = apply_score_gaps(sm, score_gaps, dry_run=dry)
        report["gap_fix"] = gap_fix

        # 硬化规则注入
        apply_result = apply_hardening(sm, suggestions, dry_run=dry)
        report["apply"] = apply_result
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
