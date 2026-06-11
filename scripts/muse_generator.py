#!/usr/bin/env python3
"""
MUSE 测试用例生成器 —— 从 SKILL.md 自动提取可测试项，生成 tests.yaml。
用法: python muse_generator.py <skill_dir> [--merge]
      --merge: 与现有 tests.yaml 合并（去重追加），否则覆盖输出。
"""
import sys, json, re
from pathlib import Path
from datetime import datetime

def extract_trigger_words(text: str) -> list[str]:
    """从 description 和正文提取触发词"""
    triggers = set()

    # 方式1: frontmatter description 中的逗号分隔词
    desc_match = re.search(r"^description\s*:\s*(.+)", text, re.MULTILINE)
    if desc_match:
        desc = desc_match.group(1)
        # 提取引号内的触发词
        for m in re.finditer(r"['\"「『]([^'\"」』]+)['\"」』]", desc):
            triggers.add(m.group(1))
        # 逗号分隔的词
        for part in desc.split(","):
            part = part.strip().strip("'\"").strip()
            if part and len(part) <= 20 and not part.startswith(("触发", "如", "例")):
                triggers.add(part)

    # 方式2: "触发词" 章节
    for m in re.finditer(r"(?:触发|关键词)[：:]\s*(.+)", text):
        for word in re.split(r"[,，、/]", m.group(1)):
            word = word.strip().strip("'\"").strip()
            if word and len(word) <= 30:
                triggers.add(word)

    return sorted(triggers) if triggers else ["__placeholder__"]

def extract_rules(text: str) -> dict[str, list[str]]:
    """提取 '必须' 和 '禁止' 规则"""
    must = []
    forbid = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 查找 "必须" 句式
        if "必须" in line:
            must.append(line[:120])
        # 查找 "禁止/严禁" 句式
        if re.search(r"(?:禁止|严禁|不得)", line):
            forbid.append(line[:120])

    return {"must": must[:10], "forbid": forbid[:10]}

def extract_format_constraints(text: str) -> list[str]:
    """提取输出格式约束"""
    constraints = []
    for m in re.finditer(r"(?:输出|格式|返回).*?(?:必须|要求|应|需).*?(?:JSON|YAML|Markdown|表格|列表|代码块)", text):
        constraints.append(m.group(0)[:120])
    return constraints[:5]

def extract_steps(text: str) -> list[str]:
    """提取步骤标题"""
    steps = re.findall(r"(?:Step\s*\d+|步骤\s*\d+)[：:\s]*(.+)", text)
    return steps[:10]

def generate_tests(skill_dir: Path) -> dict:
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return {"error": f"SKILL.md 不存在: {sm}"}

    text = sm.read_text(encoding="utf-8")
    triggers = extract_trigger_words(text)
    rules = extract_rules(text)
    formats = extract_format_constraints(text)
    steps = extract_steps(text)

    tests = []
    tid = 1

    # 1. 触发词识别
    for tw in triggers[:5]:
        tests.append({
            "id": f"trigger_{tid:03d}",
            "dimension": "触发词识别",
            "input": tw,
            "expected": "技能被触发并进入对应流程",
            "status": "pending",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
        })
        tid += 1

    # 2. 输入不触发（反例）
    tests.append({
        "id": f"trigger_{tid:03d}",
        "dimension": "触发词识别",
        "input": "写一段和该技能完全无关的代码",
        "expected": "技能不被触发",
        "status": "pending",
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
    })
    tid += 1

    # 3. 必须规则检查
    for rule in rules["must"][:3]:
        tests.append({
            "id": f"must_{tid:03d}",
            "dimension": "关键规则遵守",
            "rule": rule,
            "expected": "技能执行时遵守该规则",
            "status": "pending",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
        })
        tid += 1

    # 4. 禁止规则检查
    for rule in rules["forbid"][:2]:
        tests.append({
            "id": f"forbid_{tid:03d}",
            "dimension": "关键规则遵守",
            "rule": rule,
            "expected": "技能执行时不违反该规则",
            "status": "pending",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
        })
        tid += 1

    # 5. 输出格式
    for fc in formats[:3]:
        tests.append({
            "id": f"format_{tid:03d}",
            "dimension": "输出格式",
            "constraint": fc,
            "expected": "输出符合约束",
            "status": "pending",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
        })
        tid += 1

    # 6. references 可达性
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for ref_file in ref_dir.rglob("*"):
            if ref_file.is_file():
                rel = str(ref_file.relative_to(skill_dir)).replace("\\", "/")
                tests.append({
                    "id": f"refs_{tid:03d}",
                    "dimension": "references 可达性",
                    "file": rel,
                    "expected": "文件存在且可读取",
                    "status": "pending",
                    "generated_at": datetime.now().strftime("%Y-%m-%d"),
                })
                tid += 1

    return {
        "skill": sm.stem,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": len(tests),
        "tests": tests,
    }

def merge_with_existing(new_data: dict, existing_path: Path) -> dict:
    """与现有 tests.yaml 合并，去重追加"""
    import yaml  # type: ignore
    try:
        existing = yaml.safe_load(existing_path.read_text(encoding="utf-8")) or {}
    except Exception:
        existing = {}

    existing_tests = existing.get("tests", [])
    existing_ids = {t["id"] for t in existing_tests}

    for test in new_data["tests"]:
        if test["id"] not in existing_ids:
            existing_tests.append(test)
            existing_ids.add(test["id"])

    new_data["tests"] = existing_tests
    new_data["total_tests"] = len(existing_tests)
    return new_data

def output_yaml(data: dict, filepath: Path):
    """输出为 YAML 格式（纯文本写入，不依赖 PyYAML）"""
    lines = [
        f"skill: {data['skill']}",
        f"generated_at: {data['generated_at']}",
        f"total_tests: {data['total_tests']}",
        "tests:",
    ]
    for t in data["tests"]:
        lines.append(f"  - id: {t['id']}")
        lines.append(f"    dimension: {t['dimension']}")
        for key in ["input", "rule", "constraint", "file"]:
            if key in t and t[key]:
                lines.append(f"    {key}: \"{t[key]}\"")
        lines.append(f"    expected: \"{t['expected']}\"")
        lines.append(f"    status: {t['status']}")
        lines.append(f"    generated_at: {t['generated_at']}")
    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("用法: python muse_generator.py <skill_dir> [--merge]")
        sys.exit(1)

    sd = Path(sys.argv[1]).resolve()
    do_merge = "--merge" in sys.argv

    new_data = generate_tests(sd)
    out_path = sd / "tests.yaml"

    if do_merge and out_path.exists():
        new_data = merge_with_existing(new_data, out_path)

    output_yaml(new_data, out_path)

    report = {
        "skill": new_data["skill"],
        "total_tests": new_data["total_tests"],
        "output": str(out_path),
        "dimensions": list(set(t["dimension"] for t in new_data["tests"])),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
