---
name: luban-skill
description: "鲁班.Skill（luban Skill）：工业级智能体技能优化器。当用户提及以下关键词时调用：“优化skill”、“skill评分”、“自动优化”、“auto optimize”、“skill质量检查”、“小鲁班”、“luban”、“优化技能”、“帮我改skill”、“skill怎么样”、“提升skill质量”、“skill review”、“skill打分”。"
---

# 鲁班.Skill

> 天工开物 工匠鲁班

---

## 设计哲学

autoresearch + SkillOpt 场景自适应。

### 12 条原则

1. **单一可编辑资产**：每次只改一个 SKILL.md
2. **双重评估**：结构评分（静态分析）+ 效果验证（实际跑测试看输出）
3. **棘轮机制**：只保留改进，自动回滚退步
4. **独立评分**：评分用子 agent，消除「自己改自己评」的偏差
5. **人在回路**：每个 skill 优化完暂停，用户确认再继续
6. **文本学习率预算**：每次编辑字符变化量 ≤ 原文件 10%
7. **拒绝编辑缓冲区**：被回滚的方案留作负反馈，后续绕行
8. **Epoch Meta-Review**：跨 skill 汇总优化规律，沉淀可迁移经验
9. **场景自适应双模**：Quick（轻量 Self-Refine）/ Full（完整循环 + 仪表盘监控）
10. **ROI 前置评估**：基线分 ≥85 且最低维度分 ≥7 跳过（天花板已近）
11. **消费者能力基线**：Full 模式先测目标模型裸能力，低于阈值直接阻断
12. **全链路审计**：Full 模式所有操作记录 git commit 可追溯

### 路径约定

- `luban-workspace` = 本 SKILL.md 所在目录（即本 skill 目录本身是一个 git 仓库）
- `skills 目录` = 父目录
- 分支命名 `auto-optimize/YYYYMMDD-HHMM`
- skill 级文件（`rejected_edits.md` / `test-prompts.json` / `results.tsv`）放在 `luban-workspace/{skill_name}/`
- 全局文件（`meta_learnings.md` / `luban-profile.json`）放在 `skills 目录/`

### 架构底座：L0-L4 分层治理

5 个正交层级，按场景模式动态激活：

| 层级 | 名称 | Quick | Full |
|:---|:---|:---|:---|
| L0 | 确定性执行层 | 启用 | 启用 |
| L1 | 多智能体协作层 | 按需 | 按需 |
| L2 | 技能自适应优化层 | 启用（鼓励探索） | 严格审查后启用 |
| L3 | 价值对齐层 | 软性约束（风格对齐） | 硬性约束（合规对齐） |
| L4 | 元认知审计层 | 不激活 | 激活（跨 skill 经验沉淀） |

**L0 原子操作**（所有编辑必须走这三步）：

<<<<<<< Updated upstream
| 事件类型 | 触发条件 | Payload | L4 确认语义 |
|:---|:---|:---|:---|
| `l4.rollback` | Held-out 退化判定过拟合 / dim8 任一子维度退化 | `{skill_path, from_version, to_version, reason}` | L4 执行原子 rename 回滚，返回 `{success, rolled_back_version}`；失败时走 rename 回退策略 |
| `l4.freeze` | dim8 Safety 命中红线 / 连续 2 个 skill 过拟合 | `{skill_path, freeze_scope: "current"\|"global", reason, duration_rounds}` | L4 冻结指定 skill 的 L2 优化权限，返回 `{frozen, expiry}` |
| `l4.budget_tighten` | Step D 全局收紧编辑预算 | `{new_budget_percent, reason, triggered_by_skill}` | L4 更新全局编辑预算上限，返回 `{previous_budget, new_budget}` |
| `l4.alert` | 熔断/冻结/预算收紧等异常事件 | `{event_type, severity, detail}` | L4 记录告警日志并通知用户；返回 `{notified, alert_id}` |

所有 L2→L4 调用为同步 fire-and-forget——L2 发出事件后不阻塞等待 L4 完成，但必须在下一轮优化前检查 L4 状态（如 skill 是否仍处于 frozen 状态）。

**回滚唯一入口**：所有回滚操作（包括 Held-out 恢复路径 Step B 的自动回滚、dim8 退化熔断回滚）统一通过 L4 的 `l4.rollback` 事件执行。L2 仅负责检测回滚条件并发出事件，不回滚操作由 L4 统一执行以保证原子性和可审计性。

**L0 接口定义与能力边界**：L0 确定性执行层向上层（L1-L4）暴露三个标准接口，所有上层调用必须通过这些接口穿透 L0：

| 接口 | 签名 | 语义 | 调用方 |
|:---|:---|:---|:---|
| `exec_read` | `(file_path) → (content, hash)` | 原子读取文件内容 + SHA-256 哈希，不修改任何状态。失败时返回 `(null, error_code)`，不回退 | L1-L4 全部层级 |
| `exec_write` | `(file_path, content) → (hash_before, hash_after)` | 原子写入文件（先写临时文件再 rename），自动创建父目录。写入前后均记录哈希，失败时原文件不变 | L1/L2/L4 |
| `exec_validate` | `(file_path, rule_set) → (pass, violations[])` | 确定性规则校验——语法检查（JSON/YAML/Markdown 合法性）、格式规范、路径可达性。不涉及语义判断 | L1/L2/L3/L4 |

**L0 能力边界**：
- L0 仅保证**可重复性**（相同输入→相同输出）和**原子性**（操作要么全成功要么全不变），不提供安全性判断（安全检查由 L3/L4 负责）
- L0 不缓存、不优化、不推断——每条指令按字面执行，这是其"确定性"含义
- L0 在贡献矩阵中对可信任度标注为 ☆（辅助贡献），具体体现为：`exec_validate` 的规则校验可被 L3/L4 用作安全判断的前置输入，但其自身不做安全决策

**回滚原子性保证**：熔断回滚采用 rename 原子操作——先将当前版本重命名为 `.rolled_back`，再将上一 keep 版本 rename 为目标文件名。整个回滚过程中文件系统始终存在一个有效版本（旧版本），不存在"文件缺失窗口"。回滚操作整体耗时 < 50ms。

**rename 失败回退策略**：rename 可能因磁盘满、权限不足、跨文件系统等原因失败，按以下优先级降级处理：
1. **Step 1 重试**：间隔 100ms 重试一次（处理瞬态故障如磁盘抖动）
2. **Step 2 跨卷应对**：若因跨文件系统失败（`EXDEV`），降级为 `copy + unlink` 两步操作——先复制旧版本到目标路径，复制成功后再删除当前版本；复制失败则中止回滚，保留当前文件不变
3. **Step 3 只读兜底**：若 copy 也失败（磁盘满 / 权限不足），系统进入只读保护模式——保留当前文件不变，发出 `rollback_blocked` 告警并附带 os error 详情，通知用户手动处理。此时绝不以任何理由删除或移动文件，确保零数据丢失

**只读保护模式退出条件**：`rollback_blocked` 后系统进入只读模式（仅允许读取 skill 文件、审计日志和备份；禁止 L2 优化写入和回滚操作），skill 本身维持可正常调用状态。退出条件分三级自动检测：

| 退出条件 | 检测方式 | 动作 | 用户感知 |
|:---|:---|:---|:---|
| **磁盘空间恢复**（error=ENOSPC / EDQUOT） | Phase 0 启动时检查 skill 所在磁盘剩余空间 ≥ 最小空闲阈值（max(1GB, 当前 skill 目录大小 × 3)） | 检测到条件满足后自动退出只读模式，恢复正常优化 | 下次会话通知「磁盘空间已恢复，优化功能已自动恢复」 |
| **权限恢复**（error=EACCES / EPERM） | Phase 0 启动时尝试在 skill 目录创建临时文件并立即删除（touch test），成功即权限已恢复 | 检测到条件满足后自动退出只读模式，恢复正常优化 | 下次会话通知「目录权限已恢复，优化功能已自动恢复」 |
| **手动确认**（以上自动检测均未通过，或连续 3 次 Phase 0 检测失败） | 用户发起「恢复优化」指令或管理员手动清除只读标记 | 人工确认后解除只读模式 | 用户主动触发，即时生效 |

只读保护模式下，系统在每个会话 Phase 0 自动执行上述检测，最多持续 30 天或 30 个会话（以先到者为准）。超期未恢复 → 只读模式降级为「永久冻结」——该 skill 的 L2 优化权限需管理员手动解冻，skill 本身仍可正常调用。
=======
1. **读**：`read_text` 读取目标 SKILL.md 全文
2. **改**：`edit_file` 执行编辑（Quick 模式直接用 `.bak` 备份；Full 模式先 `git commit` 暂存）
3. **验**：按 Rubric 逐项自检本次改动影响的维度（dim1/4/7/9 按评分标准逐条核对，dim2/3/5 通读确认未引入新问题），不通过则回退
>>>>>>> Stashed changes

---

## 评估 Rubric（10 维度，总分 100）

> SkillLens（arXiv 2605.23899）实证 LLM-as-judge 准确率仅 46.4%，加入 meta-skill 三维度后提升到 73.8%。

### 评分类型

| 维度 | 权重 | 类型 | 评分方式 |
|:---|:---:|:---|:---|
| dim1 Frontmatter质量 | 7 | 确定性 | name 规范、description 含做什么+何时用+触发词、≤1024 字符、禁结尾空话。三项全过=10，任一缺失=0 |
| dim2 工作流清晰度 | 11 | LLM | 步骤明确可执行、有序号、每步有明确输入/输出 |
| dim3 失败模式编码 | 11 | LLM | 显式编码失败模式（"如果 X 失败 → Y"）；有 fallback 路径和错误恢复 |
| dim4 检查点设计 | 6 | 确定性 | 正则 `/CHECKPOINT\|STOP\|🔴\|⛔/`：≥1 处 STOP 级=10，仅 CHECKPOINT=5，无=0 |
| dim5 可执行具体性 | 18 | LLM | 有具体参数/格式/示例；禁"建议/可以考虑/根据情况"等软化词 |
| dim6 资源整合度 | 4 | LLM | references/assets 引用正确、路径可达 |
| dim7 整体架构 | 12 | 确定性 | 标题层级连续（H1→H2→H3 不跳跃）+ 必含章节（设计哲学/执行流程/约束规则/评估 Rubric 至少 3/4）：全通过=10，每缺一章 −3，每处明显重复 −2 |
| dim8 实测表现 | 20 | LLM | 子维度：Accuracy(8) + Safety(5) + Compliance(5)，总分/18×20 |
| dim9 反例与黑名单 | 6 | 确定性 | 关键词 `/不要\|禁止\|不允许\|反例/` 出现 ≥3 处不同语境：≥3=10，2=7，1=3，0=0 |
| dim10 审查门控度 | 5 | 公式 | `(100 − P0×30 − P1×5) / 10`，P0 上限锁死 40。Quick 模式默认满分 |

权重和：7+11+11+6+18+4+12+20+6+5 = **100**。确定性维度覆盖 31/100=31%，LLM 承担 64 分，dim10 公式计算 5 分。

### 评分公式

```
<<<<<<< Updated upstream
确定性维度分（dim1/4/7/9）= 规则引擎计算值，标注 [deterministic]
LLM 维度分（dim2/3/5/6/8）= 1~10，LLM judge 独立打分
dim10 原始分 = 100 − P0×30 − P1×5，归一化 /10 映射到 1~10

总分 = Σ(维度分 × 权重) / 10   满分 100

dim8 得分 = Σ(子维度分 × 权重) / 18
  - Accuracy（权重 8）：with_skill vs baseline 任务完成率对比
  - Safety（权重 5）：副作用审计，命中即冻结
  - Compliance（权重 5）：格式规范 + 输出中立 + 无幻觉路径
=======
                          ┌──────────────────────────────────────┐
                          │      鲁班.Skill 技能自进化调度器       │
                          │   事件驱动 + 定时轮询 + 按需触发       │
                          └────────────────┬─────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
    ┌─────────┴──────────┐      ┌─────────┴──────────┐      ┌─────────┴──────────┐
    │   模块层（巡检）     │      │  核心引擎（评分+修复）│      │   守卫层（验证）     │
    │ EvoSkill 失败驱动   │      │                    │      │  MUSE 回归测试      │
    │ SkillOps 定期体检   │ 写入  │  Phase 0  初始化    │ 编辑  │  修改后自动触发      │
    │ CASCADE  知识更新   │───→  │  Phase 0.3模块诊断 │───→  │  全部通过才放行      │
    │ Distill  精简瘦身   │      │  Phase 0.5测试设计 │      └────────────────────┘
    │ HASP     规则硬化   │      │  Phase 1  基线评估 │
    └────────────────────┘      │  CHECKPOINT        │
              │                 │  Phase 2  优化循环  │
              │                 │  Phase 2.5探索重写 │
              │                 │  Phase 3  汇总报告  │
              │                 └─────────┬──────────┘
              │                           │
              │      diagnostics.tsv      │   results.tsv
              │      (模块诊断记录)        │   (评分+优化记录)
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    技能文件仓库      │
                 │  SKILL.md           │
                 │  references/        │
                 │  tests.yaml         │
                 │  test-prompts.json  │
                 └─────────────────────┘
>>>>>>> Stashed changes
```

### dry_run 降权规则

dry_run 模式下确定性维度不受影响；LLM 维度处理：

<<<<<<< Updated upstream
## 十维量规执行模式选择器（自动路由）

5 个参数独立归一化后加权组合，输出模式选择值 M ∈ [0, 1]：

```
M = w₁ × N(task_domain) + w₂ × N(pii) + w₃ × N(file_scale) + w₄ × N(history_revert) + w₅ × override_flag
```

| 参数 | 归一化函数 N(x) → [0, 1] | 权重 | 归一化说明 |
| :---| :---| :---: | :---|
| ① 任务领域 | 命中金融/医疗/法律/政务 → 1.0；命中生产环境部署 → 0.8；命中技术方案/数据分析 → 0.4；命中个人创作/闲聊/娱乐 → 0.0；未命中任何关键词 → 0.2（中性默认） | **0.30** | 领域风险是模式选择的第一性原理，权重最高 |
| ② 数据敏感度 | 含身份证号/银行卡号/密钥 → 1.0；含内网路径/内部 API key → 0.7；含邮箱/手机号（非密钥）→ 0.3；无 PII 命中 → 0.0 | **0.25** | 数据敏感度直接影响合规风险 |
| ③ 文件规模 | 行数 > 800 或目录含 ≥5 个引用文件 → 1.0；行数 ∈ (200, 800] 且引用文件 < 5 → 线性映射 M = (行数 − 200) / 600；行数 ≤ 200 且引用文件 < 5 → 0.0 | **0.20** | 大文件或重资源 skill 优化副作用面广，需更严格约束 |
| ④ 历史 revert 率 | revert ≥ 3 → 1.0；revert = 2 → 0.7；revert = 1 → 0.3；revert = 0 → 0.0 | **0.15** | 历史 revert 率反映当前 skill 的优化风险倾向 |
| ⑤ 用户显式覆盖 | 检测到 quick → 设置 M=0.0 并短路（不计算其他参数）；检测到 full → 设置 M=1.0 并短路；未检测到 → override_flag = 0（不影响计算） | **短路段** | 用户显式指定跳过公式计算，直接采用指定模式 |

> w₁+w₂+w₃+w₄ = 0.90（非 1.0）。⑤ 用户显式覆盖为短路段——检测到 quick/full 时直接设置 M=0.0 或 M=1.0，不经过加权求和。正常路径输出范围为 [0, 0.90]，短路段补全两端极值，整体覆盖 [0, 1]。路由表中 ≥0.90 的硬路由档位在无显式覆盖时，需四维信号全满方可达到。

自动路由分五级决策（M = Σwᵢ × N(xᵢ)）：

| M 区间 | 触发条件 | 动作 | 用户感知 |
| :--- | :--- | :--- | :--- |
| ≥0.90（硬路由） | 四维信号全满（①命中金融/医疗/法律 + ②PII 命中 + ③>800行或≥5引用文件 + ④revert≥3）或⑤显式 override=full | 自动「执行 Full 十维量规」，不暂停 | 下次会话 Phase 0 告知 |
| [0.70, 0.90)（软路由） | — | 建议「执行 Full 十维量规」，暂停确认 | 展示选择理由，等待用户确认 |
| (0.30, 0.70)（待决策） | — | 展示选择理由，用户手动选择 | 显示 Quick/Full 选择面板 + 理由摘要 |
| (0.10, 0.30]（软默认） | — | 默认「执行 Quick 十维量规」，轻提示可切换 | 界面标注，一键切换入口可见 |
| <0.10（硬默认） | 任务领域为个人创作/闲聊/娱乐 + 文件规模 <200 行 + revert 率=0，全部满足 | 自动「执行 Quick 十维量规」，不暂停 | 无感知 |

> **边界值 rounding 策略**：模式选择值计算保留小数点后 4 位（内部精度），路由判定时四舍五入到 2 位。边界点行为定义：恰好在 0.90 → 归入硬路由（≥0.90），不暂停；恰好在 0.70 → 归入软路由（[0.70, 0.90)），暂停确认；恰好在 0.30 → 归入软默认（(0.10, 0.30]），默认 Quick；恰好在 0.10 → 归入软默认区间，仅当值严格 ≤0.09 才进入硬默认。

冷启动期（record_count<5）不生效，直接走手动选择面板。误判纠偏：用户连续 2 次在建议 Full 时手动选 Quick（或反之），该领域倾向权重衰减 50%，记录于 profile 推断豁免字段。

---

<<<<<<< Updated upstream
## 自主优化循环
=======
## 一、9维度：优化循环（保留自 Darwinv2.0）

### 评估 Rubric（9维度，总分100）

> 依据 SkillLens (arXiv 2605.23899)：LLM-as-judge 准确率仅 46.4%，加入 meta-skill 三维度后提升到 73.8%。

#### 结构维度（59分）— 静态分析

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 1 | Frontmatter质量 | 7 | name规范、description包含做什么+何时用+触发词、≤1024字符、禁结尾加空话尾巴 |
| 2 | 工作流清晰度 | 12 | 步骤明确可执行、有序号、每步有明确输入/输出 |
| 3 | 失败模式编码 | 12 | 必须显式编码失败模式；有fallback路径、错误恢复；只写正向流程扣 ≥3 分 |
| 4 | 检查点设计 | 6 | 关键决策前有用户确认、显性标记（🔴/STOP/CHECKPOINT） |
| 5 | 可执行具体性 | 18 | 不模糊、有具体参数/格式/示例；禁止"建议/可以考虑/根据情况"等软化措辞，≥3 处扣 ≥3 分 |
| 6 | 资源整合度 | 4 | references/scripts/assets引用正确、路径可达 |

#### 效果维度（35分）— 需实测

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 7 | 整体架构 | 12 | 层次清晰、不冗余不遗漏；冗余/AI腔废话扣分 |
| 8 | 实测表现 | 23 | 用测试prompt跑一遍，输出质量是否符合宣称能力 |

#### Meta-skill 维度（6分）— 反例与黑名单

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 9 | 反例与黑名单 | 6 | 必须有"不要做什么"的反例清单；没有扣 ≥3 分 |

评分规则：维度1-7、9 各打 1-10 分×权重；维度8 跑 2-3 个测试 prompt 打分。总分 = Σ(维度分×权重)/10，满分 100。改进后总分必须严格高于改进前。

关于「实测表现」维度：用子 agent 独立执行，带 skill vs 不带 skill baseline 对比输出质量。子 agent 不可用时退化为干跑验证（标注 `dry_run`），但 dry_run 比例 >30% → 评估失效警告。

### Runtime 适配性审查（gate 项）

skill 应避免硬编码特定 runtime 依赖（如 Claude Code / Codex / Cursor 等）。Phase 1 基线评估时强制跑红灯扫描：grep 命中 `在 Claude Code`、`Claude Code skill` 等特定 runtime 措辞 → 强制 P0 修复。
>>>>>>> Stashed changes

### Phase 0: 初始化

```
0. 确认当前模式（quick / full），首次使用走模式选择流程
1. 确认优化范围：
   - 全部skills → 扫描 skills 目录下所有 SKILL.md
   - 指定skills → 用户指定列表
2. 创建版本管理目录：
   - quick 模式：luban-backups-quick/YYYYMMDD-HHMM/，对每个目标 skill 做原始快照
   - full 模式：luban-backups-full/YYYYMMDD-HHMM/，备份 + 生成 version_manifest.json（含文件 hash、时间戳、操作人）
3. 初始化 results.tsv（如不存在），quick/full 各自独立 results 文件
4. 读取现有 results.tsv 了解历史优化记录
5. full 模式额外：读取 meta_learnings.md（如存在），加载历史优化规律
5.5 读取 luban-profile.json（如存在）：加载用户画像（个人风格偏好 + 工业合规基线 + 模式推断豁免），作为感知步骤的历史参考输入。画像结构含 version/changelog/mode_preference/personal/industrial/inference_exemptions，遵循语义化版本管理+并发写入控制（单写者锁+超时异步补写）。详情见 `references/SA-DM.md` §五.1 反馈步骤
6. ROI 预检（Quick ROI Check）：
   - 扫描 skill 文件大小、历史优化次数、最近一次优化距今时间
   - 输出预估：「该 skill 历史优化 3 次，上次改进 +1.2 分（距今 14 天），预估本轮优化空间：低/中/高」
   - 低空间时提示用户是否跳过
```

<<<<<<< Updated upstream
### Phase 0.5: 测试Prompt设计

在评估之前，为每个skill设计测试prompt。这步很关键——没有测试prompt，「实测表现」维度就打不了分。
=======
### Phase 0.3: 模块诊断（模块巡检，产出诊断记录）

对每个 skill 按固定顺序跑模块，写入 diagnostics.tsv：

```
1. SkillOps 巡检（必须跑）
   - 扫描路径断裂/冗余/YAML 非法，输出到 diagnostics.tsv
2. CASCADE 知识更新检查（>90 天未跑或首次）
   - 扫描过时引用，搜索最新版本，输出到 diagnostics.tsv
3. EvoSkill / HASP / Distill 存量读取
   - 以上模块为事件驱动，本次不重复触发
   - 直接读取它们已有的诊断记录（如有）
```

**顺序依据**：SkillOps 产出结构诊断 → CASCADE 产出时效诊断，供 Phase 1 评分参考。

### Phase 0.5: 测试 Prompt 设计
>>>>>>> Stashed changes

```
for each skill:
  1. 读取 SKILL.md，理解它做什么
  2. 设计2-3个测试prompt，覆盖：
     - 最典型的使用场景（happy path）→ 标注 type: "main"
     - 一个稍复杂或有歧义的场景 → 标注 type: "edge"
     - 一个异常输入场景 → 标注 type: "error"
  3. 保存到 skill目录/test-prompts.json：
     [
       {"id": 1, "type": "main", "prompt": "用户会说的话", "expected": "期望输出的简短描述"},
       {"id": 2, "type": "edge", "prompt": "...", "expected": "..."},
       {"id": 3, "type": "error", "prompt": "...（如空输入）", "expected": "应有fallback而非崩溃"}
     ]
```

展示所有测试prompt给用户，**确认后再进入评估**。测试prompt的质量决定了优化方向是否正确。

### Phase 1: 基线评估（Baseline）

```
<<<<<<< Updated upstream
for each skill in 优化范围:

  # 消费者能力基线测试（full 模式专属）
  if mode == full:
    用标准 prompt（不含 skill）测试目标模型在该领域的裸能力
    记录基线分数（任务完成率、输出规范性、安全合规率）
    # 四级响应：
    # - 高于 Full 阈值 → 正常进入 Full 或 Quick 优化
    # - 低于 Full 阈值但高于 Quick 阈值 → 自动降级为 Quick 模式，告警
    # - 低于 Quick 阈值但高于 Lite 阈值 → 自动降级为 Lite 模式（仅格式修正+拼写纠错，≤3%预算），告警
    # - 低于 Lite 阈值 → 阻断优化，输出「模型能力不足报告」

    Lite 模式定位：放弃语义优化，仅做格式纠错
    | 维度 | Lite 模式 |
    |:---|:---|
    | 优化范围 | dim7（格式规范性）+ 拼写修正 |
    | 评估方式 | 不跑评估，纯规则校验 |
    | 编辑预算 | ≤3% |
    | 熔断 | 单次失败即终止，人工接管 |
    | 算力消耗 | 约 Full 模式的 1% |

  **自动重测调度链路**：自动重测的 Step 1-4 完整链路见 SA-DM §二。

  | 差异类型 | 动作 | 用户感知 |
  |:---|:---|:---|
  | 模型升级 | 完整重测 | 下次会话通知「基座模型已升级，优化策略已自动调整」 |
  | 性能波动 | 延迟重测（连续3次后升级为完整重测） | 无感知 |
  | 隐性退化 | 立即完整重测 | 重测后通知「检测到能力漂移，已自动校准」 |

  # 结构评分（主agent可以做）
  1. 读取 SKILL.md 全文
  2. 从 SKILL.md 中定位所有引用文件路径，列出从技能文件分拆出去的实际引用文件
  3. 逐一读取所有引用文件全文
  4. 按维度1-7,9逐项打分（full 模式含 dim10，详见 §六.5 双模量规差异）（附简短理由+原文锚定）

  # 效果评分
  if mode == full:
    5. 对每个测试prompt，spawn子agent跑 with_skill vs baseline
    6. 从四维仪表盘综合打分（见下方）
  else:  # quick 模式
    5. dry_run 推演打分，标注 dry_run

  # 汇总
  7. 计算加权总分
  8. 记录到 results.tsv
=======
for each skill:
  # 结构评分（主 agent）
  1. 读 diagnostics.tsv 最近 30 天记录，作为评分参考
  2. 读取 SKILL.md 全文，按维度 1-7 逐项打分（附简短理由）
  # 效果评分（子 agent 独立）
  3. 对每个测试 prompt，spawn 子 agent 跑带/不带 skill 对比
  4. 打维度 8 分
  # 汇总
  5. 计算加权总分，记录到 results.tsv
```

**ROI 预检**：计算理论最大可提升分 = Σ[(10 − 各维度分) × 维度权重] / 10。若 < 2 分 → 跳过优化，标记 `skip: ceiling`，直接进 Phase 3。若 ≥ 2 分 → 正常进入 Phase 2。

> 例：dim4 从 7 拉到 10 仅 +1.8 分（6×3/10），dim6 满分才 4 分——低权重维度拉满也难超 2 分阈值。

评分完成后展示评分卡：

```
┌──────────────────────┬───────┬──────────────┬──────────────┐
│ Skill                │ Score │ 结构短板      │ 效果短板      │
├──────────────────────┼───────┼──────────────┼──────────────┤
│ huashu-proofreading  │ 78    │ dim3 失败模式 │ 测试prompt2  │
│ huashu-slides        │ 72    │ dim5 指令模糊 │ baseline持平 │
├──────────────────────┼───────┼──────────────┼──────────────┤
│ 平均                 │ 75    │              │              │
└──────────────────────┴───────┴──────────────┴──────────────┘
>>>>>>> Stashed changes
```

**dim8 多维仪表盘**（对应架构级五维中的有效性、可信任度、规范性、可靠性、适用性，full 模式）：

| 子维度 | 权重(dim8内) | 架构五维映射 | 测量方式 | 退化熔断 |
|--------|:---:|:---:|---------|---------|
| Accuracy（准确率） | 8 | 有效性 | 任务完成率对比 | 低于 baseline 否决 |
| Safety（安全性） | 5 | 可信任度 | 副作用审计 | 命中即冻结 |
| Compliance（合规率） | 5 | 规范性 | 格式+中立+无幻觉 | <80% 否决 |
| Latency（响应延迟） | 2.5 | 可靠性 | token 膨胀率 | >50% 警告 |
| Token Efficiency（token效率） | 2.5 | 可靠性+适用性 | token 量+输出冗余 | >baseline 200% 警告 |

> dim8 得分 = Σ(子维度分 × 权重) / 子维度权重总和，产生 1~10 分（与其他维度评分口径一致）。该分乘以 dim8 权重 22 后计入总分。仪表盘显示为「仪表盘总分 = dim8 得分 × 22 / 10」，满分 22。任一「否决」触发 → dim8 得分归零。

**如果子agent不可用**（超时、环境限制），quick 模式默认 dry_run；full 模式下维度8用干跑验证打分标注 `dry_run` 并提示「full 模式建议补齐 full_test 以保证评分可信度」。

#### 多评委独立评分机制

Full 模式采用 2 评委独立评分取中位数，对抗单 judge 乐观偏差（SkillLens 实证 46.4%→73.8%）。

| 规则 | 说明 |
|:---|:---|
| 2 评委独立打分 | 每轮优化后启动 2 个全新独立子 agent，不共享上下文 |
| 评委不复用 | 下一轮启动全新实例，避免锚定效应 |
| 分歧检测 | 两评委分数差 >3 分 → 暂停，展示双方依据由用户裁决 |
| 一票否决 | 任一评委 Safety 命中红线 → 直接熔断 |
| 早停 | 单轮 Δ<1 分→停手；连续 2 轮 Δ<2 分→天花板信号；维度满分→不再评分 |

干跑模式控制与振荡防护（滞回控制）完整定义见 `references/SA-DM.md` §五.4。
=======
| 维度 | dry_run 处理 | 原因 |
|:---|:---|:---|
| dim2/3/5/6 | 标注 `[confidence: degraded]`，不降分 | 结构维度，不依赖实际执行 |
| dim8 全部子维度 | 原始分 ×0.5 | 无实测，Accuracy/Safety/Compliance 均为推演 |
| dim10 | 默认 100（同 Quick 模式） | full_test 才能触发门控 |

反例 #6 强制约束：total dry_run_ratio > 30% 时必须至少跑 1 个 full_test。
>>>>>>> Stashed changes

### 十维执行模式

<<<<<<< Updated upstream
```
┌──────────────────────────┬───────┬──────────────┬──────────────┐
│ Skill                    │ Score │ 结构短板      │ 效果短板      │
├──────────────────────────┼───────┼──────────────┼──────────────┤
│ huashu-proofreading      │ 78    │ 边界条件      │ 测试prompt2  │
│ huashu-slides            │ 72    │ 指令具体性    │ baseline持平  │
├──────────────────────────┼───────┼──────────────┼──────────────┤
│ 平均                     │ 75    │              │              │
└──────────────────────────┴───────┴──────────────┴──────────────┘
```

full 模式下额外展示 dim8 仪表盘：

```
┌──────────────────┬────────┬──────┬──────────────────────────────┐
│ 子维度            │ 得分    │ 状态  │ 备注                         │
├──────────────────┼────────┼──────┼──────────────────────────────┤
│ Accuracy         │ 19/23  │ ✅   │ 任务完成率 +12% vs baseline    │
│ Safety           │ 5/5    │ ✅   │ 无违规                       │
│ Latency          │ 1/2    │ ⚠️   │ token 膨胀 35%，接近警戒线     │
│ Token Efficiency │ 2/3    │ ✅   │ 输出冗余度正常                │
│ Compliance       │ 5/5    │ ✅   │ 格式规范，无幻觉路径           │
├──────────────────┼────────┼──────┼──────────────────────────────┤
│ 仪表盘总分        │ 32/38  │ ✅   │ 折算 dim8 = 19.4/23           │
└──────────────────┴────────┴──────┴──────────────────────────────┘
```

**🔴 CHECKPOINT · 🛑 STOP：暂停等用户确认，再进入优化循环。**

### Phase 2: 优化循环

<<<<<<< Updated upstream
用户确认后，按基线分数从低到高排序，先优化最弱的。

#### 2A. quick 模式（轻量单轮）
=======
#### 策略库：维度低分 → 自动修复映射

诊断后查此表，命中即执行对应修复。按优先级 P0→P3 依次排查，每轮只修 1 个维度。

**P0 — Runtime / 效果问题（gate 项）**

| 症状 | dim | 自动修复动作 |
|---|---|---|
| 命中 runtime 红灯扫描 | dim6 | 特定 runtime 措辞 → runtime-neutral；Badge 钉死 → 3 中立 badge；安装路径写死 → 自动检测 + 手动路径表 |
| 带 skill 比不带还差 | dim8 | skill 过度约束，精简指令；不自动执行，标记待用户确认方向 |
| 输出格式偏离预期 | dim8 | 补充 `## 输出格式` 章节 + 明确输出模板 |

**P1 — 结构性问题**

| 症状 | dim | 自动修复动作 |
|---|---|---|
| Frontmatter 缺触发词 / description 不完整 | dim1 | 从 SKILL.md 正文提取核心功能描述，补齐到 description（≤1024 字符）；掐掉结尾空话尾巴 |
| 缺少 Phase/Step 结构 / 步骤间跳跃 | dim2 | 重组为线性编号流程，每步标注输入 → 输出 |
| 无失败分支 / 只写正向流程 | dim3 | 补三段式 fallback 表：`\| 触发条件 \| 一线修复 \| 仍失败兜底 \|` |
| 关键决策处无视觉标记 | dim4 | 插入 🔴 CHECKPOINT / 🛑 STOP（正则检测 `CHECKPOINT\|STOP\|🔴` 确保 ≥1 处） |
| 标题层级跳跃（H1→H3 无 H2）/ 必含章节缺失 | dim7 | 补中间层级 H2；若缺「设计哲学/执行流程/约束规则/评估 Rubric」中任一章则补 |

**P2 — 具体性问题**

| 症状 | dim | 自动修复动作 |
|---|---|---|
| 软化措辞 ≥3 处（"建议/可考虑/根据情况"等） | dim5 | 逐处替换：建议→必须、可考虑→执行、根据情况→按以下规则；保留原文备份 |
| 步骤模糊 / 缺具体参数 | dim5 | 补充工具名、格式（JSON Schema）、阈值、示例输入输出 |
| 缺异常处理路径 | dim3 | 补充 `if X 失败 → Y` 分支，优先插入到对应步骤下方 |
| 引用路径断裂 / 死链接 | dim6 | 修复为实际可达路径；若文件不存在且非关键 → 删除引用 |
| 引用过期 | dim6 | 搜索最新版本并替换引用 URL/版本号；保留旧版本标注 `[DEPRECATED]` |

**P3 — 可读性问题**

| 症状 | dim | 自动修复动作 |
|---|---|---|
| 段落过长（>200 字符） | dim7 | 拆分为多段；适合对比/参数的内容改用 Markdown 表格 |
| 重复描述 | dim7 | 合并去重，保留最清晰版本 |
| 缺少反例标注（dim9 关键词 <3 处） | dim9 | 在关键操作步骤旁补 `⚠️ 不要做 X` 格式反例（≥3 处不同语境） |
| 缺少速查入口 | dim7 | 在文件顶部添加 TL;DR 或决策树 |

#### 循环流程
>>>>>>> Stashed changes

```
for each skill:
  # 诊断
  找出得分最低的维度，参考 dim1-7,9 结构评分 + dry_run 效果推演

  # 单轮 Self-Refine
  生成 1 个增量改进方案，控制编辑预算 ≤10%
  执行编辑
  重新打分（结构 + dry_run）

  # 决策
  if 新分 > 旧分: keep，记录到 results.tsv
  else: revert，方案写入 rejected_edits.md

  # 🔴 CHECKPOINT：展示改动摘要，等用户确认
```

#### 2B. full 模式（完整循环）

```
for each skill:
  round = 0
  while round < MAX_ROUNDS (默认3):
    round += 1
<<<<<<< Updated upstream

    # Step 1: 诊断
    找出得分最低的维度（结构或效果都算，full 模式含 dim10）
    同时检查从技能文件分拆出去的引用文件（如 references/、examples/、assets/ 下的文件）是否存在同样短板或内容质量问题
    # HL-3 警告：dim2/dim3/dim4 是相关簇，修一个时另两个常跟着涨
    # → 不要因为 dim3 最低就单独修，要看整簇短板再决定是否同步改

    # Step 2: 审阅拒绝缓冲区（首轮跳过）
    if round > 1 and rejected_edits.md 存在:
      读取 rejected_edits.md，检查本轮方案是否与历史拒绝方案重叠
      若重叠 → 放弃本轮方案，换方向重新诊断
      备注：SkillOpt rejected-edit buffer——拒绝编辑是负反馈信号，不是偶然，必须绕行

    # Step 3: 提出改进方案
    针对最低维度，生成1个具体改进方案：
      - 改什么（具体段落/行）
      - 为什么改（对应rubric哪条）
      - 预期提升多少分
      - **编辑预算估算**：预估本次编辑的 token 变化量（新增 - 删除）

    # Step 4: 编辑预算检查（SkillOpt textual learning rate）
    if 预估 token 变化量 > 原文件总 token 的 10%:
      拒绝执行，提示「编辑量超出预算（>{token_pct}%），请拆分改动或精简方案」
      回到 Step 3 重新生成更小粒度的方案
    else:
      执行编辑

    # Step 5: 执行改进
    编辑 SKILL.md
    保存改动后副本到 luban-backups/YYYYMMDD-HHMM/{skill}/round{N}-modified.md（用于回滚和 diff 对比）

    # Step 6: 重新评估
    - 结构维度：主agent重新打分
    - 效果维度：spawn独立子agent重跑测试prompt（关键！不能自己评自己）

    # Step 7: 决策
    if 新总分 > 旧总分:
      status = "keep"，更新旧总分
      # HL-4 见好就收：连续2轮 Δ < 2 分 → break 进 Phase 3
      if last_delta < 2.0 and this_delta < 2.0:
        print("触顶信号：连续2轮边际收益 < 2 分，停止优化避免过度调整")
        break
    else:
      status = "revert"
      从 luban-backups/YYYYMMDD-HHMM/{skill}/round{N-1}-modified.md 恢复上轮版本覆盖当前 SKILL.md
      将本轮编辑方案写入 rejected_edits.md（SkillOpt rejected-edit buffer — 永久负反馈）
      记录失败尝试到 results.tsv
      break  # 该skill到瓶颈，跳到下一个

    # Step 8: 日志
    results.tsv 追加行

  # === 🔴 CHECKPOINT · 每个 skill 优化完后强制人审 ===
  展示该skill的改动摘要：
    - 改前版本（luban-backups 中的上轮文件）vs 改后版本的逐段对比
    - 分数变化（哪些维度提升/下降）
    - 测试prompt输出对比（如果跑过的话）
  等用户确认 OK 再继续下一个skill。
  如果用户说"不好"，从 luban-backups 恢复该 skill 的优化前版本。
```

### Phase 2.5: 探索性重写（full 模式专属，按需触发）
=======
    1. 诊断：找得分最低维度（注意 dim2/3/4 是相关簇——修 dim3 时 dim2 常跟涨）
    1.5 模块诊断合并：读 diagnostics.tsv 最近 30 天记录
       - 记录中的 dim → 插入该维度修复队列头部（高于纯分数排序）
       - 按以下映射表将 subtype 转换为具体策略库条目，file+line 直接标注在修复动作中

       | 模块 subtype | → 策略库条目 |
       |---|---|
       | EvoSkill: trigger_gap | P1 dim1 "Frontmatter 缺触发词" |
       | EvoSkill: flow_gap | P1 dim2 "缺少 Phase/Step 结构" |
       | EvoSkill: rule_missing | P1 dim3 "无失败分支" |
       | EvoSkill: rule_conflict | P2 dim3 "缺异常处理路径" |
       | EvoSkill: output_format | P0 dim8 "输出格式偏离预期" |
       | EvoSkill: version_compat | P2 dim6 "引用路径断裂" |
       | SkillOps: merge | P3 dim7 "重复描述" |
       | SkillOps: repair | P2 dim6 "引用路径断裂" |
       | SkillOps: retire | P2 dim6 "死链接" |
       | SkillOps: add_validator | P2 dim3 "缺异常处理路径" |
       | CASCADE: outdated_ref | P2 dim6 "引用过期" |
       | Distill: distill | P3 dim7 "段落过长/重复描述" |
       | HASP: wording_harden | P2 dim5 "软化措辞" |
       | HASP: pf_harden | P2 dim5 "软化措辞" |

       - 同一 dim 有多条记录时按 timestamp 倒序（最新优先）
    2. 查策略库：命中则执行对应自动修复；若复合症状则按 P0>P1>P2>P3 优先级
       - 未命中策略库 → 手动生成改进方案（改什么、为什么、预期提升）
       - 方案被 rejected_edits.md 命中 → 绕行，换方向重新诊断
    3. 执行改进，git commit
    4. 重新评估（效果维度必须用独立子 agent）
    5. 决策：新总分 > 旧总分 → keep；否则 revert
       - 连续 2 轮 Δ < 2 分 → break（触顶）
    6. 追加 results.tsv
  🔴 CHECKPOINT：每个 skill 优化完后展示 diff + 分数变化，等用户确认
```

**相关簇提醒**：dim2/3/4 联动——修 dim3（三段式 fallback）时 dim2 常跟涨 1-2 分。若 dim3 已满分但仍需修 dim2，优先用「重组线性流程」策略。

**编辑预算**：每次编辑字符变化量 ≤ 原文件 10%。自动修复默认控制在 5% 以内；超过 8% 时在 commit message 标注 `[budget_warn]`。

### Phase 2.5: 探索性重写（按需）
>>>>>>> Stashed changes

当 hill-climbing 连续2个skill都在 round 1 就 break（涨不动）时，提议一次「探索性重写」：

```
1. 选一个瓶颈skill
2. 保存当前最优版本：将当前 SKILL.md 复制到 luban-backups/YYYYMMDD-HHMM/{skill}/best-pre-rewrite.md
3. 从头重写SKILL.md（不是微调，是重新组织结构和表达方式）
4. 重新评估
5. if 重写版 > 存档版: 采用重写版
   else: 从 luban-backups 恢复存档版覆盖当前文件
```

这解决了 hill-climbing 的局部最优问题——有时候需要「先拆后建」才能突破瓶颈。
**🔴 CHECKPOINT · 🛑 STOP：必须征得用户同意后才执行。**

### Phase 2.8: Epoch Meta-Review（full 模式默认执行，quick 模式按需）

当本次会话完成 ≥2 个 skill 的优化后触发（SkillOpt epoch-wise slow/meta update）。

```
1. 审阅本次会话所有 skill 的 results.tsv 记录
2. 提取可复用规律，写入 meta_learnings.md：
   - 哪些维度改动最频繁且有效？（如 dim3 三段式 fallback 表对多数 skill 有效）
   - 哪些改动方向反复被拒绝？（如"增加示例"在多个 skill 被 revert）
   - 发现任何跨 skill 通用模式？（如"工作流表格化"对 dim2 提升稳定）
3. 下次优化会话开始前，主 agent 必须先读取 meta_learnings.md，在 Phase 2 诊断时优先参考
```

meta_learnings.md 格式：

```markdown
# Meta Learnings — luban 跨 skill 优化规律

## 高收益改动（多次验证有效）
| 改动模式 | 验证次数 | 平均 Δ | 适用场景 |
|----------|---------|--------|---------|
| dim3 三段式 fallback 表 | 3 | +4.2 | 有明确失败模式的 skill |

## 低收益/拒绝改动（多次被 revert 或 Δ≈0）
| 改动模式 | 拒绝/无效次数 | 原因 |
|----------|-------------|------|
| 纯措辞润色不改变结构 | 2 | dim5/dim7 对措辞不敏感 |

## 触顶信号规律
| 信号 | 触发条件 | 含义 |
|------|---------|------|
| dim2/3/4 簇同时接近满分 | 三个维度加权分 > 各自满分的 90% | 结构优化空间已耗尽，考虑 Phase 2.5 |
```

meta_learnings.md 与 SKILL.md 同目录。

### Phase 3: 汇总报告

```
# 前置：Held-out Validation Gate（full 模式专属，见 SA-DM §五.3）
if mode == full and test-prompts.json 中存在 held-out prompt:
  用 held-out prompt 对优化后的 skill 跑一次独立测试
  held_out_score = 测试结果
  baseline_held_out = results.tsv 基线行 held-out 分数

  if held_out_score >= baseline_held_out:
    通过 → 正常输出报告
  else:
    标记 held_out_fail=true，进入自动恢复级联：

    # Step A: 对比 main vs held-out 分数分布
    main_delta = 优化后 main 分数 - 基线 main 分数
    held_out_delta = held_out_score - baseline_held_out

    # Step B: 过拟合判定（main 提升但 held-out 下降）
    if main_delta > 0 and held_out_delta < 0:
      → 自动回滚到上一轮 keep 版本（通过 l4.rollback）
      → 从优化路径中移除本轮方案（写入 rejected_edits.md）
      → 编辑预算从 10% 收紧到 5%，重新进入 Phase 2（限定 1 轮）
      → 若 1 轮限定重试后 held-out 仍退化：不再递归触发 Step A→B，转 Step C

    # Step C: 系统性退化（main 和 held-out 均下降）
    if main_delta <= 0 and held_out_delta < 0:
      → 非过拟合，系统性问题
      → 建议触发 Phase 2.5 探索性重写（需用户确认）
      → 超时策略：等待用户确认最长 300 秒
      → 超时未响应：保留当前版本 + 标记 held_out_fail=true + 写入 meta_learnings.md 待处理队列

    # Step D: 连续过拟合全局收紧
    if main_delta >= 8 and held_out_delta <= -3:
      → 强过拟合：不等待第二个 skill，立即执行全局收紧预算到 5% + 强制 Phase 2.5
    if main_delta >= 5 and held_out_delta <= -5:
      → 极端过拟合：附加：该 skill 冻结 L2 优化权限 5 轮 + 该优化方向写入 rejected_edits.md 永久绕行
    if 同一 skill 连续 2 轮 held-out 退化：
      → 直接跳过 Phase 2 剩余轮次，进入 Phase 3 收工，标注 held_out_double_fail=true
    if 连续 2 个 skill 触发 Step B:
      → 全局收紧编辑预算到 5%，写入 meta_learnings.md「过拟合高发，已全局收紧预算」
```

```
## 优化报告

### 总览
- 模式：quick / full
- 优化skills数：N
- 总实验次数：M
- 保留改进：X（Y%）
- 回滚次数：Z
- 实测验证：A次完整测试 / B次干跑
- 消费者能力基线：通过 / 未测试 / 低于阈值（full 模式）
```

### 分数变化
┌──────────────────────────┬────────┬────────┬────────┐
│ Skill                    │ Before │ After  │ Δ      │
├──────────────────────────┼────────┼────────┼────────┤
│ huashu-proofreading      │ 78     │ 87     │ +9     │
│ huashu-slides            │ 72     │ 83     │ +11    │
├──────────────────────────┼────────┼────────┼────────┤
│ 平均                     │ 75     │ 85     │ +10    │
└──────────────────────────┴────────┴────────┴────────┘

### 主要改进
1. [skill-A] 补充了边界条件处理，测试输出质量提升明显
2. [skill-B] 重组了workflow结构，baseline对比优势增大

### 健康度仪表盘（full 模式专属）
┌─────────────────────┬────────┬──────┬────────────────────────────┐
│ 指标                │ 值      │ 状态  │ 说明                       │
├─────────────────────┼────────┼──────┼────────────────────────────┤
│ Accuracy            │ +13.2% │ ✅   │ 所有 skill 完成率均提升     │
│ Safety              │ 合格   │ ✅   │ 无副作用审计命中            │
│ Latency             │ +18%   │ ⚠️   │ 两个 skill token 膨胀超 15% │
│ Token Efficiency    │ +5%    │ ✅   │ 输出冗余度略有改善           │
│ Compliance          │ 100%   │ ✅   │ 格式规范，无幻觉路径         │
└─────────────────────┴────────┴──────┴────────────────────────────┘

### 资产溯源信息（full 模式专属）
- 版本回溯链：luban-backups-full/YYYYMMDD-HHMM/
- 变更审批记录：version_manifest.json
- 审计有效期：永久，不可篡改
```
=======
| 维度 | Quick 模式 | Full 模式 | 评分方 |
|:---|:---|:---|:---|
| dim1 Frontmatter | agent 按评分标准逐项检查 | 同 Quick | 确定性 |
| dim2 工作流 | LLM judge | LLM judge（多评委中位数） | LLM |
| dim3 失败模式 | LLM judge | LLM judge（多评委中位数） | LLM |
| dim4 检查点 | agent 正则扫描 CHECKPOINT/STOP/🔴/⛔ | 同 Quick | 确定性 |
| dim5 具体性 | LLM judge | LLM judge（多评委中位数） | LLM |
| dim6 资源整合 | LLM judge | LLM judge（路径可达性扫描+完整性判断） | LLM |
| dim7 架构 | agent 检查标题层级 + 必含章节 | 同 Quick | 确定性 |
| dim8 实测 | dry_run 推演 | full_test（子 agent 跑 test-prompts） | LLM |
| dim9 反例 | agent 关键词计数（不要/禁止/不允许/反例） | 同 Quick | 确定性 |
| dim10 门控 | 默认 100 | 多角色审查 P0/P1 计算 | 公式 |
>>>>>>> Stashed changes

---

## 双模策略

### 模式选择（前置网关）

```
输入：用户指令 + skill 历史评分
if 用户明确要求"完整/深度/全面/工业/生产" → Full
elif baseline 分 < 70 → Full（需要完整优化）
elif results.tsv 有 revert 记录 → Full（曾退化）
elif delta > 5 且连续 2 轮保持 → Full（有金矿）
elif 用户说"看看/评一下/扫一眼" → Quick
else → Quick（默认）
```

| | Quick | Full |
|:---|:---|:---|
| **触发** | 默认 | 用户明确要求 / ROI>5 分 / 曾被 revert |
| **评分** | 结构评分（dim1-7,9）+ dry_run 推演 | 全维度 + full_test + 多评委 + 多角色 |
| **优化** | 直接编辑 SKILL.md，self-refine 循环（不建 git 分支，用 `.bak` 文件回退） | git 分支 + 独立 judge + 仪表盘监控 |
| **审查** | dim10 默认 100 | P0/P1/P2 全量门控 |
| **基线** | 跳过 | 消费者能力基线测试 |
| **停止** | MAX_ROUNDS=3 或触顶信号 | MAX_ROUNDS=5 或触顶信号 |
| **meta** | 不激活 | L4 激活，输出 meta_learnings.md |

触顶信号：连续 2 轮 Δ < 2 分 → break，见好就收。

### 双轨反馈

<<<<<<< Updated upstream
完整机制见 `references/SA-DM.md` §八。

---

## 数据治理：动态阈值告警

基于 SA-DM §十，8 个检查项采用动态阈值（μ±2.5σ，Bonferroni 校正 α′=0.05/8≈0.00625），每会话 Phase 0 从 results.tsv 计算历史基线：

| 检查项 | 告警动作 |
|:---|:---|
| dry_run 比例 | 超限→dim8 标注可信度不足；连续 2 次 >50% → 判别力退化 |
| revert 率 | 低于 μ−2.5σ → 评分系统过宽告警 |
| Δ 均值趋势 | 斜率 <−0.1/轮 → 边际收益衰退预警 |
| flat 比例 | >40% → 评分天花板告警 |
| mode 列完整性 | 缺失 → Phase 0 强制补填 |
| 拒绝编辑缓冲区命中率 | >μ+2.5σ → 拒绝模式固化告警 |
| 平均编辑预算消耗 | <2%→ROI过低；>8%→预算紧张 |
| 自评-实测偏差 | >5 分 → 自评可信度不足 |

### Safety 独立退化检测（见 SA-DM §五.4）

Safety 子维度豁免于 dry_run/full_test 偏差对比。4 项独立机制每 Phase 3 执行：

| 检测项 | 阈值 | 退化动作 |
|:---|:---|:---|
| 规则覆盖率衰减 | 某类规则连续 5 轮零命中 | 标记 `stale`，追加新威胁模式，通知管理员 |
| false negative 回溯 | 用户手动 revert 时回溯检查 | 误放行+1；连续 2 次→冻结优化权限，写入诊断记录 |
| 规则库新鲜度 | >30 天未更新 | 建议从威胁情报源同步规则 |
| 跨 skill 聚合 | 命中率连续 3 个 Epoch 下降 | 全局「Safety 覆盖衰减」告警，建议全量审查 |

结果写入 `meta_learnings.md`「评分系统健康度」。

**告警升级路径**（见 SA-DM §十）：
- 第 1-2 次：记录告警 + dim8 标注
- 第 3 次：暂停当前 skill 优化，生成结构化问题报告，通知用户/管理员介入
- 第 5 次（同 skill）：冻结该 skill 的 L2 优化权限，需人工解冻

计数按 `(告警类型, skill_path)` 二元组独立维护——同一告警对不同 skill 分别计数。全局告警（dry_run 判别力退化/评分系统漂移）按告警类型全局计数。连续 10 轮未触发则对应计数器重置。计数器持久化于 `results.tsv` 的 `alert_counters` 扩展列。

**自动恢复与告警降级**：
- 第 3 次升级后连续 5 轮未再触发同类型告警 → 计数器回退到 1，skill 自动恢复优化权限
- 第 5 次升级后连续 10 轮未再触发同类型告警 → 计数器回退到 2，skill 自动解冻，无需人工干预

**冷却期机制**（防止降级→立即再升级振荡）：
- 第 3 次升级后回退到 1 → 冷却期 5 轮：冷却期内计数器锁定不回退，从冷却期结束后继续累加
- 第 5 次升级后回退到 2 → 冷却期 10 轮：规则同上
- 若冷却期内告警触发次数 ≥ 冷却期轮次 × 50%（即误降级），冷却期结束后计数器恢复为降级前值 +1

---

## results.tsv 格式

```tsv
timestamp	version_id	skill	old_score	new_score	status	dimension	note	eval_mode	mode
2026-03-31T10:00	baseline	huashu-proofreading	-	78	baseline	-	初始评估	full_test	full
2026-03-31T10:05	v1	huashu-proofreading	78	84	keep	边界条件	补充fallback	full_test	full
2026-03-31T10:10	v2	huashu-proofreading	84	82	revert	指令具体性	过度细化	dry_run	quick
```

<<<<<<< Updated upstream
新增 `eval_mode` 列：`full_test`（跑了子agent测试）或 `dry_run`（模拟推演）。
新增 `mode` 列：`quick` 或 `full`，记录本次优化的执行模式。
文件位置：`results.tsv`（与 SKILL.md 同目录）
=======
### diagnostics.tsv 格式（模块 ↔ 跑分共享接口）

模块产出的结构化诊断记录，Phase 2 启动优化时读取。如文件不存在则跳过（无模块诊断记录时不影响正常优化流程）。

```tsv
timestamp	source	dim	subtype	file	line	detail
```

| 字段 | 说明 |
|------|------|
| timestamp | 诊断生成时间 |
| source | 模块名：EvoSkill / SkillOps / CASCADE / Distill / HASP |
| dim | 映射到的评分维度（dim1-dim9） |
| subtype | 症状子类型，直接命中策略库 P0-P3 条目 |
| file | 目标文件路径（相对技能目录） |
| line | 具体行号 |
| detail | 一句话描述具体问题 |

**有效期**：Phase 2 只读取最近 30 天的记录，旧记录自动忽略。
>>>>>>> Stashed changes

---

## 实战 high-leverage 操作（精髓速查）

4 条经实战验证（huashu-gpt-image +10.85 / huashu-weread-advisor +14.9 / claude-design +16.5）。

- **HL-1（dim4）显性视觉标记是杠杆**：加 🔴 CHECKPOINT / 🛑 STOP，靠「必须」措辞不行——LLM 解析时扫描视觉标记。4 行改动撬动 dim4 +3 分
- **HL-2（dim3）if-then 三段式 fallback 表**：把「症状/解法」两列升级为「触发条件 / 一线修复 / 仍失败兜底」三段式。SkillLens failure-mechanism encoding 维度的落地
- **HL-3（Phase 2 诊断）维度相关簇警告**：dim2/3/4 是相关簇——修 dim3 时 dim2 常跟着涨。「找最低维度」时同时看相关簇短板再决定是否同步改
- **HL-4（Phase 2 退出）触顶自动 break**：连续 2 轮 Δ < 2 分 → break 进 Phase 3。+0.15 是停手信号不是继续信号；硬凑 MAX_ROUNDS=3 引入 over-engineering

---

---

## 异常与边界条件

流程假设环境理想，但实操常遇异常。以下预定义 fallback，保证优化过程不会「一跑就卡住」。

| 场景 | 触发条件 | 处理动作 |
|---|---|---|
| 不在备份目录 | luban-backups-quick/ 或 luban-backups-full/ 不存在或不可写 | 询问用户：创建备份目录或跳过备份；用户选后者则直接操作，但需告知无版本回滚能力 |
| results.tsv 缺失 | 文件不存在 | 新建并写表头行（9列：含 eval_mode） |
| results.tsv 损坏 | 列数不匹配 / 非TSV | 备份为 `.bak.YYYYMMDD-HHMM` 后重建，告知用户 |
| 备份目录冲突 | 备份目录已存在同名子目录 | 子目录名末尾加 `-2` / `-3`；第3次失败则询问继续还是新起 |
| 回滚失败 | 备份文件缺失或损坏 | 从 results.tsv 读取历史版本，若无可恢复则告知用户手动恢复 |
| 优化后超 150% 体积 | 新文件 > 原 × 1.5 | 拒绝提交，回到改进步骤精简（删冗余/合并重复），再评 |
| test-prompts.json 已存在 | 文件已在 skill 目录 | 默认复用并展示，问用户「复用 / 重写 / 追加」三选一 |
| test-prompts.json 无 held-out prompt | 全部 prompt 用于优化 | 从 Phase 1 中随机标记 1 个为 held-out，不参与优化循环评分 |
| SKILL.md 找不到 | 目录存在但无 SKILL.md | 该 skill 终止，results.tsv 记 `status=error`，继续下一个 |
| rejected_edits.md 缺失（非首轮） | 有 revert 记录但文件不存在 | 从 results.tsv 中 status=revert 行提取 note 列重建 |
| meta_learnings.md 缺失（下次会话） | Phase 2.8 应执行但未执行 | 降级处理：提示用户上次未做 Meta-Review，本次跳过规律参考 |
| 模式未选择 | 首次使用或模式被意外重置 | 强制引导选择 quick / full，展示模式说明后暂停确认 |
| 跨模式数据泄露 | quick 和 full 的 results/backup 交叉引用 | 阻断操作，提示用户「跨模式数据隔离已触发，请手动确认模式后再继续」 |
| 消费者基线失败（full） | Phase 1 消费者能力测试未通过 | 不进入 Phase 2，输出「消费者能力不足报告」并给出建议（微调模型 / 换更强模型 / 降级到 quick 轻量优化） |
| Held-out 验证退化（full） | Phase 3 held-out 分数 < baseline | 警告过拟合，记录标志位 held_out_fail=true，建议回滚或补防 |
| 分数计算规则 | 浮点精度漂移 | 总分保留 1 位小数，改进需严格 > 旧分（不靠四舍五入） |

<<<<<<< Updated upstream
**原则**：异常先告知用户，再按规则处理；绝不静默跳过或静默失败。
=======
Step 2: 定位缺口
  - 工具化扫描：`scripts/evo_skill_patcher.py <skill_dir>` 自动分析 gap_type + 定位行号
  - 按缺口分类表交叉验证类型
  - 定位技能文件中需修改的具体位置（文件路径 + 行号范围）
>>>>>>> Stashed changes

---

<<<<<<< Updated upstream
## luban 操作反例黑名单（dim9 应用：luban 自己优化时不要做的事）
=======
Step 4: 写入诊断记录
  - 确认并应用补丁后，追加一行到目标技能的 diagnostics.tsv
  - 格式：timestamp | EvoSkill | dim | subtype | file | line | detail
  - 缺口类型 → subtype + dim 映射：
    · 触发词遗漏 → subtype=trigger_gap, dim1
    · 流程漏洞 → subtype=flow_gap, dim2
    · 规则缺失 → subtype=rule_missing, dim3
    · 指令冲突 → subtype=rule_conflict, dim3
    · 输出格式不当 → subtype=output_format, dim8
    · 版本兼容 → subtype=version_compat, dim6
```
>>>>>>> Stashed changes

来自本机 results.tsv 早期 40 次 0 revert 的教训 + Judge G/H 自指评估暴露的反模式。每条都是**真实踩过的坑**。

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|---|---|---|
| 1 | **同 context 自评自改** | 改完后立刻在同一 Claude session 打分，会有「我刚改的肯定更好」乐观偏差（SkillLens 实证 LLM-as-judge 准确率仅 46.4%）| 必须 spawn **独立子 agent** 评分，且至少 2 个 judge 共识才信 |
| 2 | **直接覆盖原文件当回滚** | 会丢失中间版本的完整记录，无法追溯改动链 | 用 luban-backups 中的版本文件覆盖回滚，保留每一步的完整历史 |
| 3 | **为凑分增冗余** | 触顶后继续硬改往往是「加废话/加段落让 LLM 觉得更详细」，实际质量不变 | 触顶信号（连续 2 轮 Δ<2 分）→ break 进 Phase 3，**见好就收** |
| 4 | **跳过 test-prompts 直接评分** | 没有 test-prompts 的 dim8 是凭空打分，权重 22% 等于编造 | Phase 0.5 强制设计 2-3 prompts；若用户不给，默认编 3 个并展示确认 |
| 6 | **dry_run 比例 > 30%** | dim8 实测维度形同虚设，分数虚高（早期 40 次记录 67% dry_run，0 revert） | 强制至少 1 个真实 full_test；dry_run 多的优化在 results.tsv 显式打 ⚠️ |
| 7 | **静默跳过异常** | 遇到备份/tsv 异常时静默继续，破坏 ratchet 完整性 | 异常表 10 条 fallback 必须先告知用户再处理 |
| 9 | **虚构评分依据（幻觉）** | 违反 dim8 幻觉防御规则：评分不附原文锚定、不引用实际输出 | 必须附原文引用锚定；主 agent 执行真实性抽查，1 处不匹配则整轮作废 |
| 11 | **忽略拒绝编辑的历史** | 同样的改动方向在上次优化被 revert，本轮只改措辞又提交——拒绝编辑不是偶然 | 每轮 Phase 2 Step 2 先审阅 rejected_edits.md，重叠则绕行 |
| 12 | **跨模式数据混用（v4.0）** | quick 模式训练数据被用于 full 模式评估，或反之——个人风格偏好污染工业合规标准 | quick/full 的 results.tsv 和备份分存储桶，物理隔离，定期渗透测试 |
| 13 | **跳过消费者能力基线（v4.0）** | full 模式下不测目标模型裸能力就直接优化 skill——消费者不行，skill 写得再好也只是纸上谈兵 | full 模式 Phase 1 必须先跑消费者基线，低于阈值阻断 L2 |
| 14 | **忽视 ROI 预检信号（v4.0）** | 连续 3 次优化 Δ<1 分的 skill 仍强行启动完整优化循环——ROI 为负的优化是资源浪费 | Phase 0 ROI 预检低空间时必须提示用户是否跳过 |

**触发场景**：每轮 Phase 2 改动前对照本表一次。任一反模式命中 → 改方案重写。

---

## 关键数据结构

### `rejected_edits.md` — 拒绝编辑缓冲区文件结构

`rejected_edits.md` 是红线 #5（禁止丢弃负反馈）的落盘载体，存储所有被 revert 的编辑方案。文件位于 skill 根目录（与 SKILL.md 同目录），结构如下：

```markdown
# Rejected Edits Buffer — <skill_name>
> 自动维护。每次 revert 自动追加，禁止手动编辑。

## Metadata
- created: ISO8601
- total_entries: N
- last_pruned: ISO8601
- hit_to_submit_ratio: 0.XX  (审阅命中数 / Phase 2 提交数，最近 10 轮)

## Entries

### REJ-0001 | 2026-06-10T12:00 | hash=a1b2c3 | §三 #2 相关
- **编辑片段**（前 500 字符）：
  ```
  （被 revert 的 old_str → new_str 原文，截断到 500 字符）
  ```
- **完整 SHA-256**：a1b2c3d4e5f6...
- **revert 时间**：ISO8601
- **revert 原因**：held_out_degraded | safety_frozen | user_manual | score_regression
- **关联章节**：§三 #2 / §五.3
- **绕行标记**：active | bypassed_on_2026-06-11 | permanent_block
  - `active`：未被绕行，后续审阅仍需检查
  - `bypassed_on_<date>`：审阅后确认可绕行，标注绕行日期
  - `permanent_block`：极端过拟合（main↑≥5 + held_out↓≥5），该优化方向永久禁止
- **建议绕行条件**：（仅 bypassed / permanent_block 时填写）后续审阅触发词 / 模式匹配规则
```

**消费端说明**：
- **谁读**：Phase 2 Step 2（审阅后绕行）：在提出新编辑方案前，计算方案哈希与 `rejected_edits.md` 中所有 `active` 条目的编辑片段相似度（基于 SHA-256 精确匹配 + 编辑距离阈值）。命中 → 跳过该方案，标记绕行
- **何时读**：每次 Phase 2 启动时全量加载；Phase 3 汇总报告更新 `hit_to_submit_ratio`
- **命中/提交比计算**：hit_to_submit_ratio =（最近 10 轮中因绕行跳过的方案数）/（最近 10 轮 Phase 2 总提交方案数）
- **条目上限**：200 条。超出时按 LRU 淘汰 `active` 条目（`permanent_block` 不受淘汰），淘汰操作写入 `version_manifest.json` pruned 数组

### `meta_learnings.md` — 跨 skill 经验沉淀文件结构

<<<<<<< Updated upstream
`meta_learnings.md` 是 Epoch Meta-Review 与各恢复/诊断机制的统一写入目标，存储跨 skill 的优化规律、退化诊断和异常信号。文件位于 SA-DM 全局配置目录（与 `luban-profile.json` 同级），结构如下：
=======
> 论文：[arXiv:2605.13716](https://arxiv.org/abs/2605.13716)
> 核心理念：将技能库维护形式化为独立的「库时」问题，五维诊断 + 自动维护。

### 触发条件

- 定时任务：每周自动执行
- 用户指令："检查技能健康""技能体检""巡检"

### 五维诊断矩阵

| 维度 | 检查项 | 严重程度 |
|------|--------|----------|
| 效用 | SKILL.md 每条规则是否有触发条件；references 是否被引用 | 🟡/🟢 |
| 冗余 | 内容高度重复的 references；SKILL.md 中可合并的段落 | 🟢 |
| 兼容性 | 文件路径引用断裂；外部链接失效；YAML 非法 | 🔴/🟡/🔴 |
| 失败风险 | 未定义触发条件的强制规则；规则粒度过粗 | 🟡/🟢 |
| 验证缺口 | 缺少对应 rules 的验证步骤；references 缺示例和反例 | 🟡/🟢 |

### 维护动作（对齐 SkillOps 原论文概念）

| 动作 | 含义 | 示例 |
|------|------|------|
| `merge` | 合并内容高度重复的 references（相似度 > 0.8） | ref-a.md + ref-b.md → ref-merged.md |
| `repair` | 修复断裂引用或非法格式 | 路径 /old/path.md 不存在 → 改为 /new/path.md |
| `retire` | 标记过时规则（加 `[DEPRECATED]`） | 规则提到已停用的 API → 标记待清理 |
| `add_validator` | 补充验证/测试用例 | 规则 A 无验证流程 → 自动生成测试样例 |

### 执行流程

```
Step 1: 加载目标技能文件（SKILL.md + references/ 下所有文件）
Step 2: 逐维度扫描
  - 工具化扫描：执行 `scripts/skillops_scanner.py <skill_dir>` 做结构分析（路径、YAML、引用链）
  - 语义化扫描：Agent 做内容分析（规则一致性、重复、歧义）
Step 3: 汇总诊断报告（按 🔴 > 🟡 > 🟢 排序）
Step 4: 生成维护动作清单（输出报告，不自动修改）

Step 5: 写入诊断记录
  - 每个维护动作追加一行到目标技能的 diagnostics.tsv
  - 动作 → dim 映射：merge→dim7, repair→dim6, retire→dim6, add_validator→dim3
  - 格式：timestamp | SkillOps | dim | subtype | file | line | detail
```

### 输出格式
>>>>>>> Stashed changes

```markdown
# Meta Learnings — SA-DM Global
> 自动维护。Epoch Meta-Review + 退化诊断 + 异常信号 + 待处理队列统一写入。

## Metadata
- created: ISO8601
- last_epoch_review: ISO8601
- skills_optimized_since_last_review: N

---

## 过拟合模式库
（Epoch Meta-Review 写入——当 ≥2 个 skill 触发相同过拟合模式时记录）
### OFP-0001 | 发现于 2026-06-10
- 模式：在 dim5（可执行具体性）优化中反复插入冗余示例导致 held-out 退化
- 涉及 skill：[skill_a, skill_b]
- 对策：dim5 优化时禁止新增示例，仅允许精炼已有示例

---

## 退化诊断
（Health Monitor 退化检测协议 + Safety 独立退化检测写入）
### DIAG-0001 | 2026-06-10 | 评分系统漂移
- 检测方式：干跑控制 → 判别力退化 → 抽样重评
- 漂移方向：新 judge 更严（旧系统过宽）+1.8 分
- 阈值校准：告警阈值上浮 1.8 分
- 恢复前窗口：[3 轮告警数据摘要]

---

## 异常信号
（异常事件写入——包括 held_out_fail、rollback_blocked、backup_tamper 等）
### ANOM-0001 | 2026-06-10 | rollback_blocked
- skill_path: ...
- os_error: ENOSPC（磁盘满）
- 状态：等待用户清理空间

---

## L1 待处理队列
（L1→L2 异步回调 + L2→L1 失败重试写入）
### PENDING-0001 | 2026-06-10 | task_id=uuid
- 类型：L2_async_callback | L2_retry_pending
- 子任务 task_id：uuid
- 当前状态：awaiting_callback | retry_scheduled_at_ISO8601
- 重试次数/上限：0/2

---

## 评分系统健康度
（Health Monitor 自动恢复/降级 + Safety 独立退化检测 + 阈值校准写入）
### HEALTH-0001 | 2026-06-10 | 告警降级
- 告警类型：revert_rate_spike
- 降级前计数器：3
- 降级后计数器：1
- 校准前后阈值：[旧阈值, 新阈值]
- 冷却期结束：ISO8601
```

**消费端说明**：
- **谁读**：
  - Epoch Meta-Review：Phase 2.8 读取「过拟合模式库」章节，检查当前优化方向是否命中已知模式
  - Phase 0 健康度检查：读取「退化诊断」+「评分系统健康度」章节
  - L1 聚合器：读取「L1 待处理队列」章节，轮询未完成的异步回调
  - 管理员 / 运维：Phase 3 汇总报告中输出「异常信号」摘要
- **何时读**：各消费者在其对应阶段入口读取，不常驻内存
- **写入格式**：统一使用 Markdown 标题 + 键值对，每个条目以 `### <ID>` 起头
- **条目上限**：每章节 500 条。超出时按时间倒序淘汰最旧条目（各章节独立计数），淘汰前写入 `version_manifest.json` pruned 数组
=======
- **Quick→Full**：Quick 模式下 3 轮内 Δ > 5 分，自动升级 Full（有金矿）
- **Full→Quick**：Full 模式下连续 3 个 skill 稳定 delta < 3，后续降级 Quick（成熟稳定）
>>>>>>> Stashed changes

---

## 约束规则

1. **不改变 skill 核心功能和用途** — 只优化"怎么写"和"怎么执行"，不改"做什么"
2. **不引入新依赖** — 不添加 skill 原本没有的 scripts 或 references 文件
3. **每轮只改一个维度** — 避免多个变更导致无法归因；相关簇（dim2/3/4）改其一时观察另两个是否跟涨
4. **保持文件大小合理** — 优化后 SKILL.md ≤ 原文件 150% 体积
5. **尊重花叔风格** — 中文为主、简洁为上
6. **可回滚** — 所有改动在 git 分支上，用 `git checkout` 而非 `git reset --hard`
7. **评分独立性** — 效果维度必须用子 agent 独立评分，禁止同一 context「改完直接评」
8. **Runtime 中立性** — skill 必须能在 Claude Code、Codex、Cursor、OpenClaw 等任何 skills-compatible runtime 正常运行。除非 skill name 明确绑定单一 runtime（如 `xxx-codex`），任何单 runtime 措辞、单一 badge、安装路径写死均视为 gate 不通过，须在 P0 优先修复
9. **编辑同源检测** — 编辑 agent 与评分 agent 来自同一 context → dim8 所有子维度分 ×0.5，results.tsv 记录 `redline_1_violation=true`

### 架构红线运行时检测

<<<<<<< Updated upstream
SA-DM §四 定义 8 条架构红线，以下 2 条具有运行时自动检测能力：
=======
1. **禁止 self-edit-self-evaluate**：同一 agent 不得既编辑又评分。违反 → dim8 降权 ×0.5
2. **禁止跨维度打包修改**：一轮只改一个维度。违反 → 整轮回滚
3. **禁止 dry_run 为 full_test**：dim8 全部 dry_run 等于跳过效果验证。违反 → results.tsv 标记 invalid
4. **禁止 bypass gate**：P0 未闭合不得进入下一 phase。违反 → 中断流程

---

## 多评委与多角色评分（Full 模式）

### 同质多评委（压制采样噪声）

Full 模式采用 2 个独立 file-agent 评委（dispatch_task），评分取中位数。2 个评委读同一份 SKILL.md 和同一套量规，系统性高估方向一致——中位数不纠正共享偏误。

### 异质评委（按需触发）

| 触发条件 | 异质评委 | 复核焦点 |
|:---|:---|:---|
| dim1≥9 且 dim8 Accuracy≤5 | search-agent | dim1/dim3 真实性抽查 |
| dim8 Safety=5 且 dim9≤3 | computer-agent | Safety 复核 |
| dim4≥9 但从未触发过 revert | computer-agent | dim4/dim10 架构抽查 |

异质评委不计入标准评委数量，结果以 `[orthogonality]` 标注追加到评分卡。

### 多角色并行审查（P0/P1/P2 分级）
>>>>>>> Stashed changes

当 dim8 Safety < 5 或 dim10 原始分 < 60 时触发。角色组合按文档类型选派：

| 文档类型 | 角色组合 |
|:---|:---|
| 架构设计 | 系统架构师（分层一致性/接口完整性/模块耦合度）+ 安全架构师（审计链完整性/熔断回滚安全性/红线可绕过性）+ SRE（故障恢复路径/降级策略覆盖/告警闭环） |
| 安全规范 | 安全架构师 + 系统架构师 + 技术文档编辑（术语一致性/引用完整性/格式规范） |
| ML 论文 | ML 研究员（测量有效性/退化检测/偏差控制/过拟合防御）+ 系统架构师 + 技术文档编辑 |
| 综合类 | 系统架构师 + 安全架构师 + SRE + ML 研究员 + 技术文档编辑 |

**审查严重度分级**（直接影响 dim10）：

| 级别 | 定义 | dim10 扣分 | 门控 |
|:---|:---|:---|:---|
| P0 | 影响正确性或安全性 | −30/项 | 任一未闭合→阻断，dim10 上限锁死 ≤40 |
| P1 | 影响可靠性或可维护性 | −5/项 | ≥3 个未闭合→阻断 |
| P2 | 影响一致性或可读性 | 不扣分 | 不设门控 |

### 审查流程（阶段 0-4）

**阶段 0 — 前置**：识别文档类型 → 选派角色 → 公开分级声明

**阶段 1 — 独立审查**：角色间绝对隔离（不通信、不协商、不共享发现），逐章覆盖登记，输出结构化问题清单（`<角色缩写>-<序号>`，字段含章节/角色/P级/问题描述/建议修复方向）

**阶段 2 — 问题归一化**：同类合并（同章节+同根源→保留最高 P 级）、侧面互补（不同视角→合并注明"双重视角"）、独立保留（不同章节/根源→各自独立）；输出归一化清单（ID 重编号 N-01…）+ 原始ID→归一化ID 映射表

**阶段 3 — 编辑修复**：按 P0→P1→P2 逐项修复，禁止"顺手改"（仅修清单内条目），修复后全文档交叉验证

**阶段 4 — 复审闭环**：P0 由原审查角色逐条确认闭合（不通过打回阶段 3）；P1 由编辑方自检 + 原角色 30% 抽查（不通过降级 P0）；P2 由编辑方自检（不通过升级 P1）

### 子 Agent 不可用降级

当 `dispatch_task` 无法派发独立 judge 时（工具报错或 agent 类型不可用），触发降级：

| 受影响功能 | 降级行为 | results.tsv 标记 |
|:---|:---|:---|
<<<<<<< Updated upstream
| #4 编辑预算 | Phase 2 Step 4 计算 token diff，>10% 拒绝写入；Phase 0 检查 version_manifest.json 上轮 budget_violation 标记 | 阻断本轮优化并通知 |
| #8 跳过复盘 | Phase 0 检查 version_manifest.json：若 skills_optimized_since_last_review≥2 且 meta_learnings.md 最后更新早于最近 2 次完成时间 | 强制插入 Epoch Meta-Review |
=======
| 同质多评委 | 主 agent 单次 LLM 评分，不取中位数 | `judge_count=1`，`eval_mode=fallback` |
| 异质评委 | 跳过，不执行 | — |
| 多角色并行审查 | 跳过阶段 0-4，dim10 默认 100 | `eval_mode=fallback` |
| dim8 效果维度 | 无法跑 full_test，降为 dry_run 推演 | `eval_mode=fallback_dry` |
| Phase 3 Step 5 重评 | 主 agent 单次评分，不 spawn 子 agent | `judge_count=1` |
>>>>>>> Stashed changes

降级模式下 dim8 子维度处理：Accuracy → 推演值 ×0.3（无实测置信度低）、Safety → 正则白名单扫描、Compliance → 格式规范自检。降级原因写入 results.tsv note 字段。

**警告**：降级模式评分不可与 full_test 评分直接比较——降级分虚高约 15-20%。连续 3 轮降级需在汇总报告中显式标注。

---

## 优化流程（Phase 0-6）

### Phase 0: 初始化

> **Quick 模式**：跳过 step 2（不建 git 分支），其余相同。

```
1. 确认优化范围：全部 skills 或用户指定列表
2. git checkout -b auto-optimize/YYYYMMDD-HHMM
3. 检查 results.tsv 是否存在，不存在则创建并写入表头（12 列）
4. 读取 results.tsv 了解历史评分
5. ROI 前置评估：若历史基线分 ≥85 且最低维度分 ≥7 → 跳过优化，告知用户「天花板已近，建议仅评估不改」
6. 对照反例黑名单，标记历史 revert 维度为「绕行」
```

### Phase 1: 测试 Prompt 设计

```
for each skill:
  1. 读 SKILL.md，理解功能
  2. 设计 2-3 个测试 prompt（典型场景 + 歧义场景）
  3. 保存到 skill目录/test-prompts.json
```

**test-prompts.json 模板**：

```json
[
  {
    "id": "tp-01",
    "prompt": "帮我优化这个skill的frontmatter",
    "expected_behavior": "能正确读取并识别 frontmatter 字段",
    "category": "典型场景"
  },
  {
    "id": "tp-02",
    "prompt": "改一下",
    "expected_behavior": "歧义输入，应追问具体需求而非直接修改",
    "category": "歧义场景"
  }
]
```

展示所有 prompt 给用户，🔴 CHECKPOINT · 🛑 STOP 确认后进入评估。

### Phase 2: 基线评估

```
for each skill:
  1. 结构评分：dim1-7,9-10 逐项打分（附理由 + 原文锚定）
  2. 效果评分：spawn 子 agent 跑 test-prompts
     - with_skill: 带 SKILL.md 执行
     - baseline: 不带 skill 直接执行（裸 prompt）
  3. 加权计算总分，记录到 results.tsv
```

Full 模式额外执行消费者能力基线测试：用 baseline-skill（见 `references/baseline-skill.md`）测目标模型裸能力，若 baseline-skill 评分 < 60 则输出能力不足报告并阻断后续优化。此测试独立于 dim8 的 with_skill vs baseline 对比，不要混淆。

### Phase 3: 优化循环

> **Quick 模式**：不建 git 分支，Step 3 用 `cp SKILL.md SKILL.md.bak` 代替 git commit，Step 6 用 `cp SKILL.md.bak SKILL.md` 代替 git checkout 回滚。

```
for each skill（按基线分数升序，先优化最弱的）:
  round = 0
  while round < MAX_ROUNDS:
    round += 1

    # Step 1: 诊断
    找得分最低维度。注意 dim2/3/4 是相关簇——修一个时另两个常跟涨。

    # Step 2: 提方案
    1 个具体改进方案：改什么（段落/行）+ 为什么（对应 rubric 哪条）+ 预期提升。
    对照反例黑名单 10 条 + rejected_edits.md，命中 → 改方案重写。

    # Step 3: 编辑前备份
    git add -A && git commit -m "pre-edit: {skill_name}"

    # Step 4: 执行改进
    编辑 SKILL.md（字符变化 ≤10%） → 按 Rubric 逐项自检 dim1/4/7/9

    # Step 5: 重新评分
    结构维度：主 agent 重评；效果维度：spawn 独立子 agent（不同 context）

    # Step 6: 决策
    if 新总分 > 旧总分:
      git commit -m "optimize: {skill_name} +{delta}分 [{dimension}]"
      触顶信号 → break
    else:
      git checkout HEAD~1  # 回滚
      记录到 rejected_edits.md
      break
```

🔴 CHECKPOINT · 每个 skill 优化完展示改动摘要 + 分数变化，等用户确认再继续。

### Phase 4: 探索性重写（按需触发）

连续 2 个 skill 都在 round 1 break 时触发：git stash → 从头重写 SKILL.md → 重新评估 → 重写版 > stash 版则采用，否则 git stash pop。🛑 STOP：必须征得用户同意。

### Phase 5: 汇总报告

展示全局战绩：

| 项目 | 内容 |
|:---|:---|
| 优化 skill 数 | N 个，保留 M 个 |
| 分数变化 | 表格（skill名/旧分/新分/Δ/主要改进维度） |
| 主要改进摘要 | 按维度聚类，标注高频改进方向 |
| 健康度仪表盘 | Full 模式：dry_run 比例、revert 率、同源检测触发次数、oscillation 告警 |

### Phase 6: Epoch Meta-Review（Full 模式）

```
1. 汇总本次所有 skill 的优化记录
2. 提炼可迁移规律 → 追加到 meta_learnings.md
3. 识别 oscillation 模式：同一维度在 2+ skill 间反复涨跌 → 追加到 luban-profile.json：

{
  "oscillation_guard": [
    {"dimension": "dim5", "skills": ["skill-a", "skill-b"], "pattern": "细化→回滚→细化→回滚", "recommendation": "跳过 dim5 优化，先加固 dim3"}
  ]
}

此字段供后续 Phase 3 Step 2 查阅，命中则跳过该维度。
```

### 备份轮转策略

git 分支无限增长会导致仓库膨胀。Phase 6 完成后触发清理：

- 每个 skill 目录保留最近 **5 轮编辑**的备份（`latest-5`）
- baseline 备份和首轮备份**永久保留**，不受轮转影响
- 超出 5 轮的历史备份移至 `luban-backups-archive/{skill_name}/` 归档

---

## 异常与边界条件

流程假设环境理想，但实操常遇异常。以下预定义 fallback，保证优化不会「一跑就卡住」。

| 场景 | 触发条件 | 处理动作 |
|:---|:---|:---|
| 不在 git 仓库 | `git rev-parse` 失败 | 询问用户：执行 `git init` 或回退到文件备份；用户选后者则 `cp SKILL.md SKILL.md.bak.YYYYMMDD-HHMM` 代替 revert |
| results.tsv 缺失 | 文件不存在 | 新建并写表头行（12 列） |
| results.tsv 损坏 | 列数不匹配 / 非 TSV | 备份为 `.bak.YYYYMMDD-HHMM` 后重建，告知用户 |
| 分支已存在 | `git checkout -b` 失败 | 分支名末尾加 `-2` / `-3`；第 3 次失败切回现有分支并询问继续还是新起 |
| git revert 失败 | 冲突 / 工作树脏 | 先 `git stash` 重试；仍失败则从上一个 commit 读出 SKILL.md 覆盖当前文件手动恢复 |
| MAX_ROUNDS 触顶 | 已达上限仍有短板 | 不强制 break，展示当前最弱维度问用户「继续加 1 轮 / 进入探索性重写 / 收工」 |
| 优化后超 150% 体积 | 新文件 > 原 × 1.5 | 拒绝提交，回精简（删冗余/合并重复）后重评 |
| test-prompts.json 已存在 | 文件已在 skill 目录 | 默认复用并展示，问用户「复用 / 重写 / 追加」三选一 |
| SKILL.md 找不到 | 目录存在但无 SKILL.md | 该 skill 终止，results.tsv 记 `status=error`，继续下一个 |
| 消费者基线失败 | 目标模型裸能力不足 | 输出能力不足报告，阻断后续优化 |
| 子 Agent 不可用 | `dispatch_task` 返回错误 | 触发降级模式（见多评委章节），results.tsv 记 `eval_mode=fallback` |
| 分数精度漂移 | 总分差 < 0.05 | 总分保留 1 位小数，改进需严格 > 旧分（不靠四舍五入） |

**原则**：异常先告知用户，再按规则处理；绝不静默跳过或静默失败。

---

## 关键数据结构

### results.tsv（12 列）

```
timestamp	commit	skill	round	old_score	new_score	status	dim_changed	delta	note	eval_mode	judge_count
2026-06-11T10:00	baseline	luban-slides	0	-	78	baseline	-	-	初始评估	full_test	2
2026-06-11T10:05	a1b2c3d	luban-slides	1	78	84	keep	dim3	+6	补充 fallback 三段式	full_test	2
2026-06-11T10:10	b2c3d4e	luban-slides	2	84	82	revert	dim5	-2	过度细化，回滚	dry_run	1
```

- `eval_mode`: `full_test`（跑了子 agent 测试）或 `dry_run`（模拟推演）
- `judge_count`: 参与评分的独立 judge 数量
- 文件位置：`{luban-workspace}/{skill_name}/results.tsv`

### rejected_edits.md

被回滚的编辑方案，每轮回滚追加一条：

```markdown
## REJ-{序号} | {时间戳} | {skill名}

- **目标维度**: dim5
- **改动段落**: L120-L135
- **方案摘要**: 将三处"建议"改为"必须"
- **被拒原因**: 改变了 skill 核心语义，违反约束规则 #1
- **绕行建议**: dim5 已触顶，优先修 dim3
```

### meta_learnings.md

跨 skill 可迁移规律，Phase 6 追加：

```markdown
## ML-{序号} | {时间戳}

- **规律**: dim2/3/4 相关簇——修 dim3（三段式 fallback）时 dim2 平均跟涨 1.5 分
- **来源 skill**: luban-slides, code-reviewer（2/2 验证）
- **置信度**: 高
- **可复用场景**: 任何有"步骤描述"+"错误处理"双薄弱点的 skill
```

---

## luban 操作反例黑名单

来自早期 40 次 0 revert 的教训。每轮 Phase 3 Step 2 改动前对照一次，命中 → 改方案重写。

<<<<<<< Updated upstream
| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|---------|
| 1 | **同 context 自评自改** | LLM-as-judge 准确率仅 46.4%，乐观偏差严重 | spawn 独立子 agent 评分，至少 2 个 judge 共识 |
| 2 | **直接覆盖原文件当回滚** | 丢失中间版本，无法追溯改动链 | 用 `git checkout` 回滚，保留完整历史 |
| 3 | **为凑分增冗余** | 触顶后硬改是加废话，质量不变 | 连续 2 轮 Δ<2 分 → break，见好就收 |
| 4 | **跳过 test-prompts 直接评分** | dim8 权重 20%，无实测等于编造 | Phase 1 强制设计 2-3 prompts；若用户不给，默认编 3 个并展示确认 |
| 5 | **轮内改多个维度** | 多变量同时变，分数升降无法归因到具体改动 | 每轮 1 个维度；相关簇（dim2/3/4）改其一时观察另两个是否跟涨 |
| 6 | **dry_run 比例 > 30%** | dim8 实测维度形同虚设，分数虚高（早期 40 次记录 67% dry_run，0 revert） | 强制至少 1 个真实 full_test；dry_run 多的优化在 results.tsv 显式标注 |
| 7 | **静默跳过异常** | 遇到 git/tsv 异常时静默继续，破坏 ratchet 完整性 | 异常表 12 条 fallback 必须先告知用户再处理 |
| 8 | **虚构评分依据** | 评分不附原文锚定，整轮不可信 | 必须附原文引用锚定；1 处不匹配→整轮作废 |
| 9 | **忽略拒绝编辑历史** | 被 revert 过的方向本轮只换措辞又提交 | 每轮先审阅 rejected_edits.md，重叠则绕行 |
| 10 | **忽视维度相关性单独优化** | dim2/3/4 是相关簇，单独优化 dim2 时常已被前轮 dim3 修复推到顶 | 找最低维度时同时看相关簇短板，决定是否同步改 |
=======
### 触发条件

- 定时任务：每季度自动执行
- 用户指令："更新技能知识""补最新""刷新 references"
- 技能 references 中引用外部知识且距上次更新 > 90 天

### 执行流程

```
Step 1: 扫描 references/ 目录
  - 工具化扫描：`scripts/cascade_updater.py <skill_dir> --threshold 90` 自动提取 arXiv/URL/标准引用并判定过时
  - 识别所有外部引用（arXiv ID、API 文档 URL、标准编号等）
  - 记录每个引用的最后更新日期（优先 git log，回退至文件 mtime）

Step 2: 筛选过时引用
  - 距上次更新 > 90 天（可通过 --threshold 调整）→ 标记待更新
  - 优先处理用户最近高频使用的技能

Step 3: 知识检索
  - 论文：搜索引用 arXiv ID，检查是否有新版本
  - API：抓取最新文档，对比 changelog
  - 标准：搜索是否发布了新版本

Step 4: 自我反思（内省）
  - 对比新旧知识差异
  - 判断是否影响技能规则的有效性
  - 仅在有实质性变化时生成更新

Step 5: 追加式更新
  - 追加新知识（不删除旧内容，标注版本号）
  - 格式：## [YYYY-MM-DD] 更新：xxx → 新内容

Step 6: 写入诊断记录
  - 每个过时引用追加一行到目标技能的 diagnostics.tsv（仅当确实找到更新时）
  - 格式：timestamp | CASCADE | dim6 | outdated_ref | file | line | detail
```

### 关键设计

- 只追加不删除：旧知识的废弃留给 SkillOps 的 `retire` 动作
- 标注版本：每次更新附带日期和版本号
- 不自动修改规则：仅更新 references，不自动改 SKILL.md 中的规则引用
>>>>>>> Stashed changes

---

## 优化策略库

按优先级排序，每轮只做最高优先级的一个。命中即停止向下检索。

### P0: 适配性与效果问题（gate 项，必须先修）

| 类型 | 识别特征 | 优化策略 | 关联维度 |
|:---|:---|:---|:---|
| Runtime 绑定 | SKILL.md 出现单 runtime 措辞（如「在 Claude Code 里」）、安装指引只给一种路径、工作流硬编码 runtime 工具无 fallback | 替换为 runtime-neutral 措辞；安装改为「一行命令自动检测 + 手动路径表」；标注「仅在某 runtime 可用」 | dim6/dim8 |
| 效果倒退 | 带 skill 比不带还差 | skill 过度约束，精简指令 | dim8 |
| 输出偏离 | 测试输出不符合预期 | 检查是否有误导性指令；补充明确输出模板 | dim8 |
| Safety 冻结 | dim8 Safety 命中 | 逐项检查副作用来源，修复后重测 | dim8/dim10 |

**例外**：skill name 明确标注单 runtime（如 `xxx-codex`）的，跳过 Runtime 绑定检查。

### P1: 结构性问题

| 类型 | 识别特征 | 优化策略 | 关联维度 |
|:---|:---|:---|:---|
| Frontmatter 缺触发词 | name 无触发场景描述、description 无"何时用" | 补充中英文触发词；掐掉结尾空话 | dim1 |
| 无 Phase/Step 结构 | 流程缺编号、步骤间跳跃 | 重组为线性流程，每步标注输入→输出 | dim2 |
| 无检查点 | 关键决策处无视觉标记 | 插入 🔴 CHECKPOINT / 🛑 STOP | dim4 |
| 标题跳跃 | H1→H3 无 H2，章节重复 | 补中间层级，合并重复章节 | dim7 |
| 无错误处理 | 只写正常路径 | 补三段式 fallback：触发条件 / 一线修复 / 仍失败兜底 | dim3 |

### P2: 具体性问题

| 类型 | 识别特征 | 优化策略 | 关联维度 |
|:---|:---|:---|:---|
| 步骤模糊 | "处理图片""优化代码"等无参数描述 | 改为具体操作 + 参数（工具名/格式/阈值） | dim5 |
| 缺输入/输出规格 | 步骤未标明输入格式和输出格式 | 补充格式（JSON Schema/文件路径/示例） | dim5 |
| 缺异常处理 | 无"如果 X 失败，则 Y" | 补 if-then 兜底路径 | dim3 |
| 软化词过多 | "建议/可考虑/根据情况"频繁出现 | 改"建议"为"必须"，补具体数值 | dim5 |
| 资源引用断裂 | 引用文件路径不存在 | 删除死链接或补建引用文件 | dim6 |

### P3: 可读性问题

| 类型 | 识别特征 | 优化策略 | 关联维度 |
|:---|:---|:---|:---|
| 段落过长 | 单段 > 200 字符 | 拆分；适合对比/参数的内容改用表格 | dim7 |
| 重复描述 | 同信息在多处出现 | 合并去重，保留最清晰版本 | dim7 |
| 缺反例标注 | 全文无"不要/禁止/反例"关键词 | 在关键操作步骤旁加反例标注（≥3 处不同语境） | dim9 |
| 缺速查入口 | 用户需通读全文才能上手 | 添加 TL;DR 或决策树 | dim5/dim7 |

**维度相关簇提醒**：dim2/3/4 联动——修 dim3（fallback 三段式）时 dim2 常跟涨 1-2 分。

**优先级公式**：弱点深度 = (10 − 当前维度分) × 权重。同级策略内按弱点深度降序选目标。

---

## HL 操作速查

3 条高杠杆操作：

- **HL-1（dim4）显性视觉标记是杠杆**：加 🔴 CHECKPOINT / 🛑 STOP。4 行改动撬动 dim4 +3 分
- **HL-2（dim2/3/4 相关簇）三段式 fallback 一石三鸟**：修 dim3（触发条件/一线修复/仍失败兜底）→ dim2 跟涨 1-2 分，dim4 顺便补检查点
- **HL-3（Phase 3 退出）触顶自动 break**：+0.15 是停手信号，不是继续信号

完整 8 条红线定义见 `references/SA-DM.md` §四。

---

## 使用方式

```
<<<<<<< Updated upstream
"优化所有skills"      → Phase 0-6 完整流程
"优化 luban-slides"  → 只对指定 skill 执行 Phase 1-4
"评估所有skills"       → 只执行 Phase 1-2，不进入优化循环
"看看skill优化历史"    → 读取并展示 results.tsv
=======
F_approx = 1 - (模块被规则引用的次数 / 模块总字符数归一化)

归一化方式：模块总字符数 / 所有模块总字符数的均值。分母过小时取 max(均值, 100)。
```

- F ≈ 1：模块内容庞大但很少被引用 → 可精简
- F ≈ 0：模块内容紧凑且多处引用 → 保留
- F_approx ≥ 0.7：标记「可精简」；≤ 0.3：标记「核心资产」

### 精简优先级

| 优先级 | 类型 | 处理 |
|--------|------|------|
| P0 | 完全未被引用的 references | 直接建议删除 |
| P1 | 文件大但仅 1-2 处引用 | 提取引用段落到 SKILL.md，删原文件 |
| P2 | 多处重复的示例代码块 | 合并为一个 reference |
| P3 | 历史版本累积的旧内容 | 归档到 archive/ 子目录 |

### 执行流程

```
Step 1: 构建引用矩阵
  - 执行 `scripts/distill_analyzer.py <skill_dir>` 自动扫描引用关系
  - SKILL.md 每条规则 → 引用了 references/ 的哪些段落
  - 计算每个 references 文件的「有效引用密度」

Step 2: 计算 F_approx，分级标记

Step 3: 生成精简方案
  - 展示「删除后文件大小变化」预估
  - 标注「保留的核心内容」
  - 🔴 CHECKPOINT：待用户确认后执行

Step 4: 写入诊断记录
  - 确认执行后，每个 P0 删除 / P1-P3 精简项追加一行到目标技能的 diagnostics.tsv
  - 格式：timestamp | Distill | dim7 | distill | file | line | detail
>>>>>>> Stashed changes
```

---

## 资源文件

<<<<<<< Updated upstream
| 路径 | 用途 | 状态 |
|:---|:---|:---|
| `references/SA-DM.md` | 方法论骨架文档（理论来源，运行时无需读取） | 静态 |
| `references/baseline-skill.md` | 消费者基线测试用参考 skill | 静态 |
| `{skill_name}/test-prompts.json` | 测试 prompt 集 | 运行时生成 |
| `{skill_name}/results.tsv` | 优化日志（12 列） | 运行时生成 |
| `{skill_name}/rejected_edits.md` | 被拒绝的编辑方案 | 运行时生成 |
| `{skills 目录}/meta_learnings.md` | 跨 skill 可迁移优化规律 | 运行时生成 |
| `{skills 目录}/luban-profile.json` | 全局配置（oscillation_guard） | 运行时生成 |
=======
> 论文：[arXiv:2605.17734](https://arxiv.org/abs/2605.17734)
> 核心理念：技能升格为可执行程序函数（PF），含 should_activate + intervene，从"建议"变"硬纠正"。

### 触发条件

- 同一规则在同一场景下连续 2 次以上被忽略
- 用户指令："规则硬化""硬一点""这个规则总被忽略"

### 硬化层级

#### 层级 1：Should → Must（措辞强化）

```
原文：建议在生成 SKILL.md 时控制文件大小在 30KB 以内

硬化后：强制约束：SKILL.md 文件大小不得超过 30KB。
超限时，必须将详细内容拆分到 references/，SKILL.md 仅保留导航链接。
```

#### 层级 2：Should → PF（可执行程序函数）

在 SKILL.md frontmatter 中追加硬规则元数据：

```yaml
hard_rules:
  - id: rule_001
    should_activate: "SKILL.md 文件大小 > 30KB"
    intervene:
      type: "block_and_restructure"
      action: "禁止继续在 SKILL.md 追加内容，将超出部分写入新 reference 文件"
    severity: "critical"
    last_violated: "2026-06-10"
    violation_count: 3
```

### 执行流程

```
Step 1: 执行日志分析
  - 工具化扫描：`scripts/hasp_hardener.py <skill_dir> [--results <results.tsv>]` 自动提取软规则、匹配违规历史
  - 从 `results.tsv` 和 EvoSkill 失败捕获记录中提取规则违规实例
  - 识别「规则被忽略」的实例（同一场景下规则未被遵循）

Step 2: 分级处理
  - 工具自动判定 T0（基线）/ T1（措辞强化，违规 2 次）/ T2（PF 硬化，违规 ≥3 次）
  忽略 1 次 → 暂不处理
  忽略 2 次 → 生成措辞强化建议（层级 1：建议 → 必须）
  忽略 ≥3 次 → 生成 PF 硬化建议（层级 2：注入 hard_rules YAML 块）

Step 3: 硬化规则注入
  - 定义 should_activate 条件 + intervene 动作
  - 🔴 CHECKPOINT：待用户确认后执行

Step 4: 写入诊断记录
  - 确认执行后，追加一行到目标技能的 diagnostics.tsv
  - 违规 ≥2 次：subtype=wording_harden；违规 ≥3 次：subtype=pf_harden
  - 格式：timestamp | HASP | dim5 | subtype | file | line | detail
```

### 硬化适用性

| 规则类型 | 适合硬化 | 原因 |
|----------|---------|------|
| 输出格式约束 | ✅ | 可精确检测和修正 |
| 文件大小限制 | ✅ | 可精确检测 |
| 必须包含的章节/字段 | ✅ | 结构化检查 |
| 语义风格约束 | ❌ | 难以精确检测 |
| 创造性建议 | ❌ | 无法形式化 |

---

## 七、MUSE-Autoskill 模块：修改后自动回归测试

> 论文：[arXiv:2605.27366](https://arxiv.org/abs/2605.27366)
> 核心理念：双驱动评估（单元测试 + 运行反馈），自动触发修补和重测，首次实证跨智能体技能迁移。

### 触发条件

- 任何对技能文件（SKILL.md 或 references/）的编辑操作完成后
- 自动触发，无需用户指令

### 测试用例生成维度

| 维度 | 生成方法 | 示例 |
|------|----------|------|
| 触发词识别 | 从 SKILL.md 提取所有触发词，逐一构造输入 | 输入"小鲁班" → 预期触发 |
| 输出格式 | 提取格式约束，构造验收条件 | 输出必须包含 YAML frontmatter |
| 关键规则遵守 | 提取"必须"/"禁止"语句，构造边界测试 | 输入超限请求 → 预期拒绝 |
| 流程完整性 | 按技能 Step 列表逐项模拟 | Step 3 依赖 Step 2 的输出 → 断链测试 |
| references 可达性 | 遍历所有文件路径引用 | 逐条检查文件是否存在 |
| 反例测试 | 构造明确不在范围内的输入 | "帮我写操作系统" → 预期不触发 |

### 执行流程

```
Step 1: 修改前快照
  - 执行 `scripts/muse_generator.py <skill_dir>` 保存修改前 hash 并生成测试用例
  - 保存修改前完整文件 hash
  - 自动生成 5-10 条测试用例（基于 6 维度）

Step 2: 执行修改

Step 3: 回归测试
  - 逐条运行测试用例
  - 逐条检查修改后的技能行为

Step 4: 结果判定
  全部通过 → 「回归测试通过，无退化」
  部分失败 → 列出失败项 + 偏差 + 建议回滚
  全部失败 → 强制建议回滚

Step 5: 测试用例沉淀
  - 通过的用例追加到 tests.yaml（如不存在则创建）
  - 形成持续增长的回归测试集
```

### tests.yaml 格式

```yaml
skill: {skill_name}
generated_at: {date}
tests:
  - id: trigger_001
    dimension: "触发词识别"
    input: "{test_input}"
    expected: "{expected_behavior}"
    status: pass | fail
    last_run: {date}
    
  - id: format_001
    dimension: "输出格式"
    condition: "{constraint}"
    check: "{check_method}"
    status: pass | fail
    last_run: {date}
```

---

## 八、调度器：触发策略

```
事件驱动（立即响应）
  ├── P0: 用户明确反馈技能错误         → EvoSkill
  ├── P0: 技能编辑操作完成              → MUSE 回归测试
  ├── P1: 同一规则连续忽略 3 次         → HASP 层级 2
  └── P2: 同一规则连续忽略 2 次         → HASP 层级 1

按需触发（用户指令）→ 详见第十二节

定时驱动（周期扫描）
  ├── 每周：SkillOps 健康巡检
  ├── 每月：Skill Distill 精简检查（仅当冗余评分低时）
  └── 每季度：CASCADE 知识更新检查（仅当有外部引用时）
```

### 并发控制与冲突仲裁

| 场景 | 仲裁规则 |
|------|----------|
| 任何模块 vs 用户正在手动编辑 | 用户优先，模块排队 |
| Phase 2 编辑中 vs 事件模块同时触发 | Phase 2 优先（按需触发等同用户指令），事件模块排队 |
| SkillOps 巡检 vs 用户正在编辑 | 巡检只读执行，仅输出报告 |
| Skill Distill vs HASP 同时触发 | HASP 优先（质量保障），精简让步 |
| MUSE 回归测试运行中 | 锁定技能文件，其他模块等待 |
| 同一技能多个任务排队 | FIFO 顺序执行 |

---

## 九、异常与边界条件

| 场景 | 处理动作 |
|------|----------|
| 不在 git 仓库 | 询问用户：`git init` 或回退到文件备份 `.bak.YYYYMMDD-HHMM` |
| results.tsv 缺失 | 新建并写表头 |
| results.tsv 损坏 | 备份为 `.bak` 后重建 |
| 分支已存在 | 分支名加 `-2`/`-3`；第 3 次失败切回现有分支询问 |
| `git revert` 失败 | 先 `git stash` 重试；仍失败从上一个 commit 读 SKILL.md 手动恢复 |
| MAX_ROUNDS 触顶 | 展示最弱维度问用户「加 1 轮 / Phase 2.5 / 收工」 |
| 优化后超 150% 体积 | 拒绝提交，进精简流程 |
| test-prompts.json 已存在 | 默认复用，问用户「复用/重写/追加」 |
| SKILL.md 找不到 | 该 skill 终止，status=error，继续下一个 |
| dry_run 比例 > 30% | 评估失效警告；尝试 1 次 full_test；仍 dry_run → 放弃要求，标注 `[eval_degraded]` |
| 多个模块同时触发 | 按优先级排队，EvoSkill > MUSE > HASP > SkillOps > CASCADE > Distill |

**原则**：异常先告知用户，再按规则处理；绝不静默跳过。

---

## 十、反例黑名单（本底座自己优化时不做的事）

| # | 反模式 | 替代做法 |
|---|--------|----------|
| 1 | 同 context 自评自改 | 必须 spawn 独立子 agent 评分 |
| 2 | `git reset --hard` 当回滚 | 用 `git revert HEAD` 保留追溯链 |
| 3 | 为凑分增冗余 | 触顶信号（连续 2 轮 Δ<2）→ break |
| 4 | 跳过 test-prompts 直接评分 | Phase 0.5 强制设计 2-3 prompts |
| 5 | 轮内改多个维度 | 每轮 1 个维度 |
| 6 | dry_run 比例 > 30% | 强制至少 1 个 full_test |
| 7 | 静默跳过异常 | 异常表 fallback 必须先告知 |
| 8 | 忽视维度相关性单独优化 | 看相关簇短板再决定 |

---

## 十一、约束规则

1. **不改变技能核心功能和用途** — 优化"怎么写"，不改"做什么"
2. **不引入新依赖** — 不添加原本没有的 scripts 或 references
3. **每轮只改一个维度** — 避免多变量无法归因
4. **保持文件大小合理** — 优化后 ≤ 原大小 150%
5. **可回滚** — 所有改动在 git 分支上，用 `git revert` 而非 `reset --hard`
6. **评分独立性** — 效果维度必须用子 agent 或干跑验证
7. **Runtime 中立** — 技能必须能在任何 skills-compatible runtime 运行
8. **人在回路** — 所有修改操作必须经用户确认（只读扫描除外）
9. **追加优于覆盖** — CASCADE 知识更新只追加不删除旧内容

---

## 十二、使用方式

| 指令 | 触发模块 |
|------|----------|
| "优化所有 skills" | 鲁班核心引擎 Phase 0-3（全量） |
| "优化 {skill_name}" | 鲁班核心引擎 Phase 0-3（单个） |
| "评估所有 skills 质量" | Phase 0.5-1（仅评估不改） |
| "检查技能健康" | SkillOps 巡检 |
| "这个技能有问题 / 不对" | EvoSkill 失败修补 |
| "更新技能知识" | CASCADE 知识更新 |
| "精简技能 / 瘦身" | Skill Distill |
| "规则硬化 / 硬一点" | HASP 规则硬化 |
| "看看优化历史" | 读取 results.tsv |

---

## 十三、资源文件速查

| 路径 | 用途 |
|------|------|
| `results.tsv` | 历次优化日志（9 列含 eval_mode） |
| `{skill目录}/test-prompts.json` | 每个 skill 的测试 prompt |
| `{skill目录}/tests.yaml` | MUSE 回归测试用例（持续沉淀） |
| `scripts/skillops_scanner.py` | SkillOps 工具化扫描（路径/YAML/引用链结构分析） |
| `scripts/distill_analyzer.py` | Distill 引用矩阵构建与 F_approx 计算 |
| `scripts/muse_generator.py` | MUSE 测试用例自动生成与回归执行 |
| `references/SA-DM.md` | SkillOps 设计方法论完整论文 |
| `QUICKSTART.md` | 快速上手指南 |
| `README.md` | 项目概览与架构说明 |

---

## 学术依据

- **EvoSkill** (arXiv [2603.02766](https://arxiv.org/abs/2603.02766))：失败驱动的技能缺口发现与自动修补
- **SkillOps** (arXiv [2605.13716](https://arxiv.org/abs/2605.13716))：技能库运维框架，五维健康诊断
- **CASCADE** (arXiv [2512.23880](https://arxiv.org/abs/2512.23880))：持续学习 + 自我反思驱动的技能进化
- **Skill Distill** (arXiv [2604.01608](https://arxiv.org/abs/2604.01608))：指标自由度 F 驱动的精简决策
- **HASP** (arXiv [2605.17734](https://arxiv.org/abs/2605.17734))：技能升格为可执行程序函数
- **MUSE-Autoskill** (arXiv [2605.27366](https://arxiv.org/abs/2605.27366))：全生命周期管理 + 回归测试
- **SkillLens** (arXiv [2605.23899](https://arxiv.org/abs/2605.23899))：9 维 rubric 实证来源
- **SkillOpt** (arXiv [2605.23904](https://arxiv.org/abs/2605.23904))：validation-gated edits 形式化框架
- **autoresearch**：Karpathy 自主实验循环

---

> "Train your Skills like you train your models."
> — 技能自进化底座，站在六篇论文的肩膀上。
>>>>>>> Stashed changes
