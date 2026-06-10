---
name: luban-skill
description: "鲁班.Skill（luban Skill）：工业级智能体技能优化器。当用户提及以下关键词时调用：“优化skill”、“skill评分”、“自动优化”、“auto optimize”、“skill质量检查”、“小鲁班”、“luban”、“优化技能”、“帮我改skill”、“skill怎么样”、“提升skill质量”、“skill review”、“skill打分”。"
---

# 鲁班.Skill

> 天工开物 工匠鲁班

---

## 设计哲学

autoresearch + SkillOpt 场景自适应
1. **单一可编辑资产** — 每次只改一个 SKILL.md
2. **双重评估** — 结构评分（静态分析）+ 效果验证（跑测试看输出）
3. **棘轮机制** — 只保留改进，自动回滚退步（基于文件对比）
4. **独立评分** — 评分用子agent，避免「自己改自己评」的偏差
5. **人在回路** — 每个skill优化完后暂停，用户确认再继续
6. **文本学习率预算** — 每次编辑控制 token 变化量 ≤ 原文件 10%，避免大步跳跃导致优化不稳定（SkillOpt bounded edit）
7. **拒绝编辑缓冲区** — 被回滚的编辑方案保留为负反馈，后续轮次审阅后避免重蹈覆辙（SkillOpt rejected-edit buffer）
8. **Epoch Meta-Review** — 跨 skill 汇总优化规律，沉淀可迁移经验供后续复用（SkillOpt slow/meta update）
9. **场景自适应双模** — quick 模式（个人/轻量 Self-Refine）与 full 模式（工业/完整循环 + 多维仪表盘监控），同一套技术栈按使用主体自动切换运行姿态（v4.0）
10. **ROI 前置评估** — 优化前预估改进空间，低收益 skill 提示跳过；工业模式严格核算成本收益，仅高价值 skill 启动完整优化（v4.0）
11. **消费者能力基线** — full 模式先测目标模型的裸能力，低于阈值时阻断优化避免无效投入（v4.0）
12. **全链路审计** — full 模式所有操作记录不可篡改日志，支持多维度追溯（v4.0）

与纯结构审查的区别：不只看 SKILL.md 写得规不规范，更看改完后**实际跑出来的效果是否更好**。

### 架构底座：L0-L4 分层治理

SA-DM 将能力解耦为 5 个正交层级，按场景模式动态激活：

| 层级 | 名称 | Quick 策略 | Full 策略 |
|:---|:---|:---|:---|
| L0 | 确定性执行层 | 默认启用 | 默认启用 |
| L1 | 多智能体协作层 | 按需（MVS 已定义待落地） | 按需（MVS 已定义待落地） |
| L2 | 技能自适应优化层 | 默认启用（鼓励探索） | 严格审查后启用 |
| L3 | 价值对齐层 | 软性约束（风格对齐） | 硬性约束（合规对齐） |
| L4 | 即时纠错与熔断层 | 轻量监控 | 全面监控（预扫+仪表盘） |

**L2→L4 跨层接口规范**：

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

---

## 评估 Rubric（10维度，总分102≈100）

> **设计依据**：基于 SkillLens 论文（arXiv 2605.23899）实证发现——LLM-as-judge 评估 skill 质量准确率仅 46.4%（接近随机），加入 meta-skill 三维度后提升到 73.8%。本 rubric 强化 dim3 / dim5 评分标准，新增 dim9「反例与黑名单」+ dim10「审查门控度」，权重平衡至 102。**目的：让评分对真实质量更敏感，减少 LLM judge 的乐观偏差。**

### 结构维度（69分）— 静态分析

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 1 | **Frontmatter质量** | 7 | 规范性 | name规范、description包含做什么+何时用+触发词、≤1024字符、禁结尾空话 |
| 2 | **工作流清晰度** | 11 | 可靠性 | 步骤明确可执行、有序号、每步有明确输入/输出 |
| 3 | **失败模式编码** | 11 | 可靠性 | 必须显式编码失败模式（"如果 X 失败→Y"的分支），只写正向流程扣 ≥3 分 |
| 4 | **检查点设计** | 6 | 可信任度 | 关键决策前有用户确认，检查点必须显性标记（🔴/STOP/CHECKPOINT） |
| 5 | **可执行具体性** | 18 | 有效性 | 不模糊、有具体参数/格式/示例；禁止"建议/可以考虑/灵活把握"等软化措辞 |
| 6 | **资源整合度** | 4 | 适用性 | references/scripts/assets 引用正确、路径可达 |
| 7 | **整体架构** | 12 | 规范性 | 结构清晰不冗余、与生态一致；AI 腔废话段落一处扣 1 分 |

### 效果维度（22分）— 需要实测

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 8 | **实测表现** | 22 | 有效性+可信任度+规范性 | 跑2-3个test prompt，五子维度综合打分，详见 Phase 1 多维仪表盘 |

### Meta-skill 维度（11分）— 反例与黑名单

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 9 | **反例与黑名单** | 6 | 可信任度 | skill 必须有"不要做什么"的反例清单，缺少扣 ≥3 分 |
| 10 | **审查门控度** | 5 | 可信任度+可靠性+规范性 | 多角色审查中 P0/P1/P2 严重度门控通过情况：基础分 100，P0 每项未闭合 −30 且上限锁死 40（任一 P0 未闭合即触发，先扣 P0/P1 分后再应用锁死上限），P1 每项未闭合 −5，P2 不扣分，下限 0 |

#### 审查严重度分级（构成 dim10 审查门控度）

| 级别 | 定义 | 发布门控 | dim10 扣分 |
|:---|:---|:---|:---|
| P0 | 影响正确性或安全性 | 必须修复才可发布，任一未闭合→阻断 | −30/项，上限锁死 ≤40 |
| P1 | 影响可靠性或可维护性 | ≥3 个未闭合→阻断 | −5/项 |
| P2 | 影响一致性或可读性 | 不设门控 | 不扣分 |

完整多角色审查协议（阶段 0-4：前置→独立审查→问题归一化→编辑修复→复审闭环）见 `references/SA-DM.md` §十二。

### 评分规则
- 维度1-7、9：每个维度打 1-10 分，乘以权重得到该维度得分
- 维度8（实测表现）：跑2-3个测试prompt，从五子维度综合打分，按 dim8 公式折算为 1-10 分
- 维度10（审查门控度）：dim10 原始分(0~100) / 10 → 归一化到 1~10 区间参与加权计算；Quick 模式默认满分 100（归一化 10 分）
- **总分 = Σ(维度分 × 权重) / 10**，满分约100（权重总和102）
- 改进后总分必须 **严格高于** 改进前才保留；dim8 详细评分方式见 SA-DM §六.5。

#### dim8 幻觉防御：证据锚定
（详细评分方式及五子维度定义见 SA-DM §六.5；dry_run 降级条件见 SA-DM §五.4）

LLM judge 在评分时天然有编造倾向——可能不实际读取输出就给出"质量很好"的抽象评价。**dim8 评分必须附带证据锚定**：

- **full_test 模式**：judge 必须在评分中**引用 with-skill 和 baseline 两组的实际输出原文**（至少各 1 处关键片段），并标注引用来自哪一组、哪个 test prompt。未附原文引用的评分判定为 **⚠️ 疑似幻觉，dim8 分不可信**。
- **dry_run 模式**：judge 必须在评分中**引用被评 SKILL.md 的具体段落**（行号范围或关键句原文），说明基于哪段流程推演出的评分。未引用的 dry_run 评分同样打 ⚠️。
- 主 agent 在汇总评分前必须执行 **一步式真实性抽查**：随机抽 1 个 judge，检查其评分文本中的引用片段是否确实出现在 judge 声称的来源中。若 1 处不匹配 → 该 judge 的全部评分标记 **⚠️ FABRICATED**，整轮 dim8 评分作废重跑。

#### 双模量规差异

| 维度 | Quick 模式 | Full 模式 |
| :---| :---| :---|
| dim8 执行方式 | dry_run 推演（占比 ≤30%） | full_test 子 agent 实测（占比 ≥50%） |
| dim10 审查门控度 | 不执行（默认满分） | P0/P1/P2 全量门控 |
| 评委数量 | 1 个（仅结构评分） | ≥2 个独立评委取中位数 |
| dim8 执行频率 | 仅基线评估时 | Phase 2 每轮 + Phase 3 汇总 |
| 退化检测 | 无 | dim8 任一子维度退化→熔断回滚 |
| 告警阈值 | 宽松（Δ<0 才告警） | 严格（干跑>30%、偏差>5分告警） |

---

## Runtime 适配性审查（gate 项，独立于 10 维度评分）

skill 应当能在 Claude Code / Codex / Cursor / OpenClaw / Hermes / Gemini CLI / OpenCode 等 50+ skills-compatible runtime 通用——否则其他 agent 解析时会被「在 Claude Code 里」「Claude Code skill」等措辞误判为「不是给我用的」直接拒装（实例：nuwa-skill 因此被 Marvis agent 拒绝）。

### Phase 1 基线评估时强制跑一次红灯扫描

逐行扫描 SKILL.md 和 README.md（如有），检查是否命中以下红灯关键词：

- `在 Claude Code`
- `Claude Code skill`
- `Claude Code 用户`
- `Cursor only`
- `Codex 中`
- `^[![Claude Code`
- `skills/[a-z]`（路径硬编码为特定 runtime 前缀）
- `/plugin install\b`

命中任一 = 红灯 → 强制把 Phase 2 第一轮定为 P0「runtime drift 修复」（写入 results.tsv 的 note 列 `runtime_warn=N`）。

### 例外（允许的「Claude Code 痕迹」）

frontmatter 触发词、花叔生态内部 skill 名引用、明确标注 runtime-specific 章节、commit message——这些正当出现，不算红灯。

---

## 场景模式选择（前置网关）

所有优化任务首先经过模式路由，决定执行深度。

### quick 模式（个人 / 轻量）

适用场景：个人开发者、快速试错、低算力环境

- **评估方式**：结构评分（dim1-7,9）+ dry_run 效果推演
- **优化策略**：单轮 Self-Refine 增量更新，不启动完整循环
- **验证门槛**：用户点赞/点踩信号驱动，ROI 阈值低
- **反思上限**：≤1 轮，失败仅记录不告警
- **资产管理**：自由编辑/导出/删除，无审批
- **算力消耗**：约为 full 模式的 10-15%

### full 模式（工业 / 完整）

适用场景：团队协作、生产环境、高合规要求

- **评估方式**：完整 10 维评分 + full_test 实测 + 消费者能力基线
- **优化策略**：Phase 2 完整循环（预算控制 + 拒绝缓冲 + Meta-Review）
- **验证门槛**：分数提升 + 合规检查 + 变更影响分析，三者缺一不可
- **反思上限**：≤3 轮，触及安全关键词硬性熔断
- **资产管理**：版本管控 + 灰度发布 + 变更审批 + 全链路审计
- **健康度监控**：多维仪表盘（Accuracy / Safety / Latency / Token Efficiency / Compliance）

### 模式选择流程

```
1. 首次使用 → 强制引导选择 quick / full
2. 后续使用 → 默认复用上次模式，可通过「切换 quick」「切换 full」指令变更
3. 混合场景 → 自动建议 full 模式并允许用户手动调节参数
4. 数据隔离 → quick / full 的 results.tsv 和备份分开存储，严禁跨模式混用
```

🔴 CHECKPOINT：首次使用或切换模式时，暂停确认后再继续。

---

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

## 自主优化循环

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

### Phase 0.5: 测试Prompt设计

在评估之前，为每个skill设计测试prompt。这步很关键——没有测试prompt，「实测表现」维度就打不了分。

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

**干跑模式控制与振荡防护（滞回控制）**：

为防止评委独立评分 + 退化检测 + 恢复流程形成"干跑→全测→干跑"振荡回路，SA-DM 采用滞回控制：

| 规则 | 参数 | 说明 |
|:---|:---|:---|
| **冷却期** | 5 会话 | 从 full_test 切回 dry_run 后，至少冷却 5 个会话才能再次切回 full_test |
| **full_test 最低比例锁定** | ≥30% | 重建基线期间（如退化检测触发全量重评），锁定 full_test 比例不低于 30%，冷却期内不释放该锁定 |
| **偏差 <3 分退出阈值** | 滞回带 3~5 分 | 连续 3 轮 full_test 与 dry_run 评分偏差 <3 分（进入滞回带）→ 可安全退出 full_test 回到干跑；若偏差在 3~5 分之间 → 维持现状不切换方向（滞回）；偏差 >5 分 → 继续 full_test |
| **冷却期状态持久化** | results.tsv `oscillation_guard` 列 | JSON 格式：`{"last_full_test_session": "ISO8601", "cooldown_until": "ISO8601", "full_test_ratio_locked": 0.30}` |

> 滞回控制确保干跑/全测切换不会因瞬时波动频繁翻转。`oscillation_guard` 列在 Phase 0 加载、Phase 3 更新，跨会话保持。

基线评估完成后，展示评分卡：

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

用户确认后，按基线分数从低到高排序，先优化最弱的。

#### 2A. quick 模式（轻量单轮）

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

meta_learnings.md 完整结构定义见上文「## 关键数据结构 → meta_learnings.md — 跨 skill 经验沉淀文件结构」，包含 6 个完整章节（Metadata / 过拟合模式库 OFP / 退化诊断 DIAG / 异常信号 ANOM / L1 待处理队列 PENDING / 评分系统健康度 HEALTH），条目上限 500 + 时间倒序淘汰规则。

meta_learnings.md 与 luban-profile.json 同级（SA-DM 全局配置目录）。

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

---

## 双轨反馈机制（Quick↔Full）

基于 SA-DM §八，Quick/Full 模式间通过受控管道相互滋养。

### Quick→Full：创新信号迁移
| 子阶段 | 内容 | 状态 |
|:---|:---|:---|
| Phase A | 从 results-quick.tsv 自动提取 Δ>3 且 revert=0 的创新模式 | ✅ 自动 |
| Phase B | dim8 Safety+Compliance 预检 + PII 扫描 + runtime 中立检查 | ✅ 自动 |
| Phase C | 1 个 held-out skill + dry_run baseline 对比，Δ>0 通过 | ✅ 自动 |
| Phase D | 自动生成变更影响报告，管理员一键审批 | 🟡 需确认 |

### Full→Quick：可靠基线反哺
| 子阶段 | 内容 | 状态 |
|:---|:---|:---|
| Phase A | 提取 Full 模式中经过大规模验证的可靠模式 | 🟡 手动 |
| Phase B | 根据个人偏好轻量适配 | 🟡 手动 |
| Phase C | 作为「专家推荐」推送给个人用户 | ⬜ 规划中 |
| Phase D | 用户可选采纳/微调/忽略（基于信任度自适应确认） | ✅ 已实现 |

**跨模式迁移约束**：禁止直接迁移（须经完整合规审查）、数据物理隔离、风格污染防护。

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

新增 `eval_mode` 列：`full_test`（跑了子agent测试）或 `dry_run`（模拟推演）。
新增 `mode` 列：`quick` 或 `full`，记录本次优化的执行模式。
文件位置：`results.tsv`（与 SKILL.md 同目录）

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

**原则**：异常先告知用户，再按规则处理；绝不静默跳过或静默失败。

---

## luban 操作反例黑名单（dim9 应用：luban 自己优化时不要做的事）

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

`meta_learnings.md` 是 Epoch Meta-Review 与各恢复/诊断机制的统一写入目标，存储跨 skill 的优化规律、退化诊断和异常信号。文件位于 SA-DM 全局配置目录（与 `luban-profile.json` 同级），结构如下：

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

---

## 约束规则

1. **不改变skill的核心功能和用途** — 只优化"怎么写"和"怎么执行"，不改"做什么"
2. **不引入新依赖** — 不添加skill原本没有的scripts或references文件
3. **每轮只改一个维度** — 避免多个变更导致无法归因
4. **保持文件大小合理** — 优化后SKILL.md不应超过原始大小的150%
5. **编辑预算硬约束** — 每轮 token 变化量 ≤ 原文件 10%（SkillOpt bounded edit）；若一轮不够，拆分多轮
6. **拒绝编辑永久保留** — 被 revert 的编辑方案写入 rejected_edits.md，后续轮次必须先审阅再规划（SkillOpt rejected-edit buffer）
7. **测试集隔离** — test-prompts.json 中至少保留 1 个 held-out prompt 不在优化循环中使用，仅在 Phase 3 最终验证时跑（SkillOpt held-out validation gate）
8. **尊重花叔风格** — 中文为主、简洁为上
9. **可回滚** — 所有改动在备份目录中保留完整历史，用文件覆盖而非直接删除
10. **评分独立性** — 效果维度必须用子agent或至少干跑验证，不能在同一上下文里「改完直接评」
11. **Runtime 中立性** — 见上文 Runtime 适配性审查章节（gate 项，命中红灯措辞须在 P0 优先修复）
12. **引用文件全覆盖** — 维度评分（尤其是 dim6）前必须定位并逐份读取从技能文件分拆出去的所有引用文件（如 references/、examples/、assets/ 等子目录下的文件）；未实际读取引用文件内容即打分视为无效评估，dim6 直接扣 2 分
13. **评分真实性可追溯** — 每个维度的打分理由必须引用被评内容的具体原文（如 SKILL.md 的段落/行号、测试输出的关键片段、引用文件的具体表述）。仅给出抽象评价（"结构清晰""效果不错"）无原文锚定的评分视为疑似幻觉，该维度分不可信并必须重评
14. **Meta-Review 必做** — full 模式下完成 ≥2 个 skill 优化后，必须执行 Phase 2.8 写入 meta_learnings.md；下次优化会话开始前必须先读取

### 架构红线运行时检测

SA-DM §四 定义 8 条架构红线，以下 2 条具有运行时自动检测能力：

| 红线 | 检测方式 | 违规动作 |
|:---|:---|:---|
| #4 编辑预算 | Phase 2 Step 4 计算 token diff，>10% 拒绝写入；Phase 0 检查 version_manifest.json 上轮 budget_violation 标记 | 阻断本轮优化并通知 |
| #8 跳过复盘 | Phase 0 检查 version_manifest.json：若 skills_optimized_since_last_review≥2 且 meta_learnings.md 最后更新早于最近 2 次完成时间 | 强制插入 Epoch Meta-Review |

告警通知统一通过 Phase 3 汇总报告输出为结构化告警摘要（meta_learnings.md「异常信号」章节 + Phase 3 终端输出）。

完整 8 条红线定义见 `references/SA-DM.md` §四。

---

## 使用方式

### 首次使用（模式选择）
```
用户："使用 luban-skill 优化"
→ 引导选择 quick / full 模式
→ 后续默认复用，可用「切换 quick」「切换 full」变更
```

### 全量优化
```
用户："优化所有skills"
→ Phase 0-3 完整流程（quick 跳 2.5 和 2.8）
→ 默认：先基线评估，按分数升序优先优化最低 5-10 个
```

### 切换模式
```
用户："切换 full 模式" 或 "切换 quick 模式"
→ 确认后生效，下次优化走新模式的执行路径
→ 数据隔离：results.tsv 和备份各自独立
```

### 单个优化
```
用户："优化 huashu-slides 这个skill"
→ 只对指定skill执行 Phase 0.5-2
```

### 仅评估不改
```
用户："评估所有skills的质量"
→ 只执行 Phase 0.5-1（设计测试prompt + 基线评估），不进入优化循环
```

### 查看历史
```
用户："看看skill优化历史"
→ 读取并展示 results.tsv
```

---

## 分类体系统一映射（架构五维↔L0-L4↔10维量规↔dim8子维度）

SA-DM 存在四套分类体系，本表为权威映射（冲突时以此为准）：

| 架构五维 | L0-L4 核心贡献层 | 10维量规 (dim#) | dim8 子维度 |
|:---|:---|:---|:---|
| 可信任度 | L3★ / L4★ / L2☆ / L0☆ | dim4 + dim9 + dim10 | Safety |
| 可靠性 | L0★ / L2★ / L4★ | dim2 + dim3 + dim10 | Latency + Token Efficiency |
| 适用性 | L3★ / L1☆ / L2☆ | dim6 | Token Efficiency + Accuracy |
| 规范性 | L3★ / L4★ / L0☆ / L2☆ | dim1 + dim7 + dim10 | Compliance |
| 有效性 | L0★ / L2★ / L1☆ | dim5 + dim8 | Accuracy |

完整映射+贡献矩阵见 `references/SA-DM.md` §六。

### 学术依据 & Credits

- **SkillLens**（arXiv [2605.23899](https://arxiv.org/abs/2605.23899)）：9 维 rubric 的实证来源（LLM 自评 46.4% → 加 meta-skill 三维度后 73.8%）；全生命周期框架（经验生成→技能提取→技能消费）。
- **SkillOpt**（arXiv [2605.23904](https://arxiv.org/abs/2605.23904)）：validation-gated edits 形式化框架；编辑预算（bounded edit）、拒绝缓冲区（rejected-edit buffer）、epoch-wise slow/meta update 三项机制已集成至 luban 的 Phase 2/2.8。代码 [github.com/microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)（`pip install skillopt`）、项目页 [microsoft.github.io/SkillOpt](https://microsoft.github.io/SkillOpt/)。🤝 2026-06-03 微软官方仓库已把 luban-skill 列入集成名单。
- **autoresearch**：[github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)，本 skill 1.0 的原始灵感。

---

## 资源文件速查

| 路径 | 用途 |
|---|---|
| `results.tsv` | 历次优化日志（9列含 eval_mode） |
| `{skill目录}/test-prompts.json` | 每个 skill 的测试 prompt 集（用于维度8实测） |
| `rejected_edits.md` | 被 revert 的编辑方案永久负反馈（SkillOpt rejected-edit buffer） |
| `meta_learnings.md` | 跨 skill 优化规律沉淀（SkillOpt slow/meta update） |
