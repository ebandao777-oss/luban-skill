#!/usr/bin/env python3
"""
Sentinel —— luban 内嵌第 6 模块（Phase 0.3）。
对目标 skill 的 scripts/ + references/ 做正则安全扫描，输出扣分记录到 diagnostics.tsv。

用法：
    python security_audit.py <skill_dir> [--diagnostics <path>]

输出格式（追加到 diagnostics.tsv）：
    模块\t维度\t扣分\t文件\t行号\t详情
"""

import os
import re
import sys
import argparse

# ──────────── 检测规则 ────────────

RULES = [
    # 类别 1: 恶意指令
    {
        "category": "恶意指令",
        "dim": "dim10",
        "patterns": [
            (r'\bexec\s*\(',           "exec() 系统调用"),
            (r'\bsystem\s*\(',         "system() 系统调用"),
            (r'\bsubprocess\b',        "subprocess 模块调用"),
            (r'\bos\.system\b',        "os.system() 调用"),
            (r'\bpopen\b',             "popen 管道执行"),
            (r'\brm\s+-rf\b',          "rm -rf 递归强制删除"),
            (r'\bdel\s+/[fFqQ]',       "del /f 强制删除"),
            (r'\bformat\s+[a-zA-Z]:',  "format 磁盘格式化"),
            (r'\breg\s+delete\b',      "reg delete 注册表删除"),
            (r'\bkill\s+-9\b',         "kill -9 强制杀进程"),
        ],
        "deduction": 2,  # 每类 -2
        "cap": 4,        # 上限 -4
    },
    # 类别 2: 硬编码凭据
    {
        "category": "硬编码凭据",
        "dim": "dim10",
        "patterns": [
            (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{8,}', "API Key 明文赋值"),
            (r'(?i)password\s*[=:]\s*["\'][^"\']{3,}', "password 明文赋值"),
            (r'(?i)token\s*[=:]\s*["\'][a-zA-Z0-9_\-\.]{8,}', "token 明文赋值"),
            (r'(?i)secret\s*[=:]\s*["\'][a-zA-Z0-9_\-]{6,}', "secret 明文赋值"),
            (r'-----BEGIN\s+(RSA|EC|DSA|OPENSSH)?\s*PRIVATE KEY-----', "私钥明文嵌入"),
        ],
        "deduction": 2,  # 每处 -2
        "cap": 4,
    },
    # 类别 3: Prompt 注入
    {
        "category": "Prompt 注入",
        "dim": "dim10",
        "patterns": [
            (r'(?i)\bDAN\b',                                            "DAN 模式关键词"),
            (r'(?i)jailbreak',                                          "jailbreak 关键词"),
            (r'(?i)simulate\s+(that\s+)?(you\s+are|being)',           "模拟角色扮演注入"),
            (r'(?i)system\s+override',                                 "系统指令覆盖"),
            (r'(?i)ignore\s+(all\s+)?(previous|above|prior).*instruction', "忽略之前指令"),
            (r'(?i)developer\s*mode',                                  "developer mode 诱导"),
            (r'(?i)roleplay\s+as',                                     "角色扮演注入"),
            (r'(?i)you\s+are\s+now\s+.*(free|unrestricted|unlimited)', "解除限制注入"),
        ],
        "deduction": 2,  # 每处 -2
        "cap": 2,        # 不设累计上限（单处即-2）
    },
    # 类别 4: 数据外泄
    {
        "category": "数据外泄",
        "dim": "dim10",
        "patterns": [
            (r'(?i)smtp\s*(lib|send|connect)',     "SMTP 邮件外发"),
            (r'(?i)upload.*(external|remote)',      "上传到外部服务器"),
            (r'(?i)requests\.post\b',                "HTTP POST 外发数据"),
            (r'(?i)ftp\s*(upload|put|store)',        "FTP 上传"),
            (r'(?i)curl\s+.*\b(upload|post|put)\b', "curl 上传数据"),
            (r'(?i)scp\b',                           "SCP 文件传输"),
        ],
        "deduction": 2,
        "cap": 2,
    },
    # 类别 5: 权限越权
    {
        "category": "权限越权",
        "dim": "dim10",
        "patterns": [
            (r'\bchmod\s+[0-7]{3,4}\b',  "chmod 权限修改"),
            (r'\bchown\b',                "chown 所有者变更"),
            (r'\bsudo\b',                 "sudo 提权"),
            (r'\bsu\s+-',                 "su 切换用户"),
            (r'\bicacls\b',               "icacls Windows 权限修改"),
        ],
        "deduction": 2,
        "cap": 2,
    },
]

# ──────────── 核心逻辑 ────────────

def find_text_files(skill_dir: str) -> list[str]:
    """收集 skill 目录下所有文本文件。"""
    text_exts = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".cfg", ".txt", ".tsv", ".csv"}
    files = []
    # 仅扫描 scripts/ 和 references/，排除 SKILL.md（文档层描述非可执行代码）
    scan_dirs = [
        os.path.join(skill_dir, "scripts"),
        os.path.join(skill_dir, "references"),
    ]

    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, filenames in os.walk(d):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in text_exts:
                    fp = os.path.join(root, fname)
                    # 排除自身（正则模式含触发词，非实际漏洞）
                    if os.path.abspath(fp) == os.path.abspath(__file__):
                        continue
                    files.append(fp)
    return files


def scan_file(filepath: str) -> list[tuple]:
    """对单文件执行全部规则扫描，返回命中列表。"""
    hits = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return hits

    for rule in RULES:
        for pattern, desc in rule["patterns"]:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    hits.append((
                        "Sentinel",
                        rule["dim"],
                        rule["deduction"],
                        filepath,
                        i,
                        f"[{rule['category']}] {desc}: {line.strip()[:120]}"
                    ))
    return hits


def apply_caps(hits: list[tuple]) -> list[tuple]:
    """按类别上限合并扣分。同类命中仅取 cap 内条目。"""
    from collections import defaultdict

    cat_hits: dict[str, list[tuple]] = defaultdict(list)
    for h in hits:
        category = h[5].split("]")[0][1:] if "]" in h[5] else h[0]
        cat_hits[category].append(h)

    capped = []
    for rule in RULES:
        cat = rule["category"]
        items = cat_hits.get(cat, [])
        capped.extend(items[: rule["cap"] // rule["deduction"] + 1])
    return capped


def write_diagnostics(hits: list[tuple], diag_path: str):
    """追加写入 diagnostics.tsv。"""
    os.makedirs(os.path.dirname(diag_path), exist_ok=True)
    with open(diag_path, "a", encoding="utf-8") as f:
        for h in hits:
            f.write("\t".join(str(x) for x in h) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Sentinel")
    parser.add_argument("skill_dir", help="目标 skill 目录路径")
    parser.add_argument("--diagnostics", default=None, help="diagnostics.tsv 路径")
    args = parser.parse_args()

    if not os.path.isdir(args.skill_dir):
        print(f"[Sentinel] 错误：目录不存在 {args.skill_dir}", file=sys.stderr)
        sys.exit(1)

    files = list(set(find_text_files(args.skill_dir)))
    print(f"[Sentinel] 扫描 {len(files)} 个文件")

    all_hits = []
    for fp in files:
        hits = scan_file(fp)
        all_hits.extend(hits)
        if hits:
            rel = os.path.relpath(fp, args.skill_dir)
            print(f"  {rel}: {len(hits)} 处命中")

    capped_hits = apply_caps(all_hits)

    # 汇总
    from collections import Counter
    cat_counts = Counter(h[5].split("]")[0][1:] if "]" in h[5] else "" for h in capped_hits)
    total_deduction = sum(h[2] for h in capped_hits)
    print(f"\n[Sentinel] 汇总：共 {len(all_hits)} 处命中，上限后 {len(capped_hits)} 条，累计扣分 {total_deduction}")
    for cat, count in cat_counts.items():
        print(f"  {cat}: {count} 条")

    if args.diagnostics and capped_hits:
        write_diagnostics(capped_hits, args.diagnostics)
        print(f"\n[Sentinel] 已写入 {args.diagnostics}")

    sys.exit(0 if total_deduction == 0 else 1)


if __name__ == "__main__":
    main()
