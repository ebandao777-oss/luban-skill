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

---

## 评估 Rubric（9维度，总分100）

> **设计依据**：基于 SkillLens 论文（arXiv 2605.23899）实证发现——LLM-as-judge 评估 skill 质量准确率仅 46.4%（接近随机），加入 meta-skill 三维度后提升到 73.8%。本 rubric 强化 dim3 / dim5 评分标准，新增 dim9「反例与黑名单」，权重平衡到 100。**目的：让评分对真实质量更敏感，减少 LLM judge 的乐观偏差。**

### 结构维度（58分）— 静态分析

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 1 | **Frontmatter质量** | 7 | 规范性 | name规范、description包含做什么+何时用+触发词、≤1024字符、**禁结尾加"灵活应用/根据情况判断"等空话尾巴** |
| 2 | **工作流清晰度** | 12 | 可靠性 | 步骤明确可执行、有序号、每步有明确输入/输出 |
| 3 | **失败模式编码** | 12 | 可靠性 | **必须显式编码失败模式**（写出"如果 X 失败 → Y"的明确分支）；有fallback路径、错误恢复；**只写正向流程而不写失败分支扣 ≥3 分**（SkillLens meta-skill 维度） |
| 4 | **检查点设计** | 6 | 可信任度 | 关键决策前有用户确认、防止自主失控；**检查点必须显性标记（🔴/STOP/CHECKPOINT），仅靠"如果...建议..."措辞不算** |
| 5 | **可执行具体性** | 17 | 有效性 | 不模糊、有具体参数/格式/示例、可直接执行；**禁止"建议/可以考虑/根据情况/灵活把握/视情况而定"等软化措辞**——出现 ≥3 处扣 ≥3 分（SkillLens actionable specificity 维度） |
| 6 | **资源整合度** | 4 | 适用性 | 仅限评估技能文件（SKILL.md）和从该技能文件分拆出去的文件（如 references/ 下的证据文档、examples/ 下的示例、assets/ 下的资源等）。引用路径必须正确、内容必须与 SKILL.md 主体一致、可正常读取无安全拦截；仅检查路径存在而未读内容扣 ≥2 分 |

### 效果维度（35分）— 需要实测

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 7 | **整体架构** | 12 | 规范性 | 结构层次清晰、不冗余不遗漏、与花叔生态一致；**冗余/AI腔废话段落（说白了/换句话说/首先其次综上等花叔禁用词）出现一处扣 1 分** |
| 8 | **实测表现** | 23 | 有效性+可信任度+规范性 | 跑2-3个 test prompt（含主流/边界/异常三类场景），从 Accuracy/Safety/Compliance/Latency/Token Efficiency 五个子维度综合打分 |

### Meta-skill 维度（6分）— 反例与黑名单

| # | 维度 | 权重 | 架构五维映射 | 评分标准 |
|---|------|------|:---:|---------|
| 9 | **反例与黑名单** | 6 | 可信任度 | **skill 必须有"不要做什么"的反例清单**；只写"应该做 X"没有"不要做 Y"扣 ≥3 分；红灯/危险动作/反模式应单独章节列出（SkillLens risk-action blacklist 维度） |

### 评分规则
- 维度1-7、9：每个维度打 1-10 分，乘以权重得到该维度得分
- 维度8（实测表现）：跑2-3个测试prompt，按输出质量打1-10分
- **总分 = Σ(维度分 × 权重) / 10**，满分100
- 改进后总分必须 **严格高于** 改进前才保留

### Rubric 的实证基础

rubric 设计依据来自 **SkillLens 论文（arXiv 2605.23899）** + **本机 controlled study**：

- SkillLens 发现 LLM-as-judge 准确率仅 46.4%（接近随机），加入 meta-skill 三维度后升到 73.8%
- 本机对 huashu-research 做 4 类 degradation → 5 个独立 judge 盲测一致 V1>V2，Δ 均值 +46.5（5/5 high confidence）

**结论**：rubric 能识别 gross degradation，但 fine-grained quality difference 仍不可信，**重要决策必须人审**。

### 关于「实测表现」维度

这是与纯结构评分最大的区别。评分方式：

1. 为每个skill设计2-3个**典型用户prompt**（不是边缘case，是最常见的使用场景），每个 prompt 标注场景类型：
   - `主导航路径`：skill 宣称的核心功能
   - `边界条件`：稍复杂或有歧义的输入
   - `异常输入`：格式错误、超长输入、空输入
2. 用子agent执行：一个带skill跑，一个不带skill跑（baseline）
3. 对比输出质量，从以下五个子维度综合打分（对应架构级五维）：

   **Accuracy（有效性）**
   - 相比不带skill的baseline，质量提升明显吗？
   - 任务完成率：skill 是否能独立完成整个任务，还是需要用户多次补充信息？

   **Safety（可信任度）**
   - **副作用审计**：skill 输出是否包含潜在危害——删除指令、覆盖文件、凭据泄露、有偏推荐（仅推荐特定工具/平台）、幻觉编造文件名/路径/API？

   **Compliance（规范性）**
   - 输出格式是否规范？是否 runtime 中立？
   - 场景覆盖率：test prompt 是否覆盖了 skill 宣称的全部场景？未覆盖的场景类型在评分中标注缺失。

   **Latency（可靠性）**
   - 带 skill 后 token 膨胀率是否在合理范围？
   - 同样 prompt 换措辞重跑（如"帮我找文件" vs "搜一下那个文档"），输出是否稳定一致？

   **Token Efficiency（可靠性+适用性）**
   - skill 自身 token 量是否冗余？
   - 用户意图匹配：输出是否端到端完成了用户意图？是否出现中间断链（如只给了分析未给结论、只列了步骤未执行）？
   - 遇到异常输入时是否有合理的 fallback 而非崩溃或返回空？

若子 agent 不可用（超时/资源限制），退化为「干跑验证」：读完 skill 后模拟一个典型 prompt 的执行思路，判断流程是否合理；必须在 results.tsv 标注 `dry_run`。**dry_run 比例 > 30% → 评估失效警告**（来自本机 controlled study：dim8 实测维度权重 23%，无 full_test 验证时分数不可信）。

#### dim8 幻觉防御：证据锚定

LLM judge 在评分时天然有编造倾向——可能不实际读取输出就给出"质量很好"的抽象评价。**dim8 评分必须附带证据锚定**：

- **full_test 模式**：judge 必须在评分中**引用 with-skill 和 baseline 两组的实际输出原文**（至少各 1 处关键片段），并标注引用来自哪一组、哪个 test prompt。未附原文引用的评分判定为 **⚠️ 疑似幻觉，dim8 分不可信**。
- **dry_run 模式**：judge 必须在评分中**引用被评 SKILL.md 的具体段落**（行号范围或关键句原文），说明基于哪段流程推演出的评分。未引用的 dry_run 评分同样打 ⚠️。
- 主 agent 在汇总评分前必须执行 **一步式真实性抽查**：随机抽 1 个 judge，检查其评分文本中的引用片段是否确实出现在 judge 声称的来源中。若 1 处不匹配 → 该 judge 的全部评分标记 **⚠️ FABRICATED**，整轮 dim8 评分作废重跑。

#### 双模量规差异

同一 9 维量规在 Quick/Full 模式下有不同的执行深度：

| 维度 | Quick 模式 | Full 模式 |
|:---|:---|:---|
| dim8 执行方式 | dry_run 推演（占比 ≤30%） | full_test 子 agent 实测（占比 ≥50%） |
| 评委数量 | 1 个（仅结构评分 dim1-7,9，可自己评） | ≥2 个独立评委取中位数 |
| dim8 执行频率 | 仅基线评估时 | Phase 2 每轮 + Phase 3 汇总 |
| 退化检测 | 无 | dim8 任一子维度退化→熔断回滚 |
| 告警阈值 | 宽松（Δ<0 才告警） | 严格（干跑>30%、偏差>5分告警） |

---

## Runtime 适配性审查（gate 项，独立于 9 维度评分）

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

所有优化任务首先经过模式路由，决定执行深度。灵感来自智能体技能全生命周期优化 v4.0 双模架构。

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

- **评估方式**：完整 9 维评分 + full_test 实测 + 消费者能力基线
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
    低于阈值 → 提示「消费者能力不足，建议先微调模型或更换更强模型，强行优化 skill 收益有限」

  # 结构评分（主agent可以做）
  1. 读取 SKILL.md 全文
  2. 从 SKILL.md 中定位所有引用文件路径，列出从技能文件分拆出去的实际引用文件
  3. 逐一读取所有引用文件全文
  4. 按维度1-7,9逐项打分（附简短理由+原文锚定）

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

**dim8 多维仪表盘**（对应架构级五维中的有效性、可信任度、规范性，full 模式）：

| 子维度 | 权重 | 架构五维映射 | 测量方式 | 退化熔断 |
|--------|:---:|:---:|---------|---------|
| Accuracy（准确率） | 8 | 有效性 | with_skill vs baseline 任务完成率对比 | 低于 baseline 直接否决 |
| Safety（安全性） | 5 | 可信任度 | 输出含删除/覆盖/凭据泄露/有偏推荐检测 | 命中任一项 → 冻结优化 |
| Compliance（合规率） | 5 | 规范性 | 输出格式规范 / runtime 中立 / 无幻觉路径 | 不合格 < 80% 否决 |
| Latency（响应延迟） | 2.5 | 可靠性 | 带 skill 后 token 膨胀率 | 膨胀 >50% 警告 |
| Token Efficiency（token效率） | 2.5 | 可靠性+适用性 | skill 自身 token 量 + 输出冗余度 | 冗余 >baseline 200% 警告 |

> dim8 得分 = Σ(子维度分 × 权重) / 子维度权重总和，产生 1~10 分（与其他维度评分口径一致）。该分乘以 dim8 权重 23 后计入总分。仪表盘显示为「仪表盘总分 = dim8 得分 × 23 / 10」，满分 23。任一「否决」触发 → dim8 得分归零。

**如果子agent不可用**（超时、环境限制），quick 模式默认 dry_run；full 模式下维度8用干跑验证打分标注 `dry_run` 并提示「full 模式建议补齐 full_test 以保证评分可信度」。

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
    找出得分最低的维度（结构或效果都算）
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

当本次会话完成 ≥2 个 skill 的优化后触发。灵感来自 SkillOpt 的 epoch-wise slow/meta update——将跨 skill 的优化规律沉淀为可迁移经验。

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
# 前置：Held-out Validation Gate（full 模式专属）
if mode == full and test-prompts.json 中存在 held-out prompt:
  用 held-out prompt 对优化后的 skill 跑一次独立测试
  if held-out 分数 < baseline held-out 分数:
    警告：「Held-out 验证未通过，skill 可能存在过拟合，建议回滚或补防」
    记录到 results.tsv，标志 held_out_fail=true
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

## 优化策略库

按优先级排序，每轮只做最高优先级的一个：

### P0: 消费者能力基线（full 模式专属，Phase 1 前置）
- 目标模型在该领域裸能力不足 → 提示「消费者能力不足，建议先微调模型或更换更强模型」
- 基线分数低于阈值 → 阻断 L2 优化，触发 Agent 微调工单
- 强行优化低能力消费者上的 skill → 收益极低，ROI 为负

### P0: Runtime 适配性问题（gate 项命中 → 必须先修）
- README/SKILL.md 出现红灯措辞（如「在 Claude Code 里」「Claude Code skill」）→ 替换为 runtime-neutral 措辞
- Badge 钉死单一 runtime → 改为 `Agent Skills Standard` + `skills.sh` + `Multi-Runtime` 三个中立 badge
- 安装章节只给一种 runtime 的路径 → 改为「一行命令（auto-detect）+ 手动路径表 + 作为参考资料」三层结构
- 工作流硬编码 runtime-specific 工具且无 fallback → 给出通用替代方案或标注「仅在某 runtime 可用」
- 例外：skill 名明确标注单 runtime（如 `xxx-codex`）的，可跳过本项

### P0: 效果问题（实测发现的）
- 测试输出偏离用户意图 → 检查skill是否有误导性指令
- 带skill比不带还差 → skill可能过度约束，考虑精简
- 输出格式不符合预期 → 补充明确的输出模板
- **副作用审计命中** → skill 输出包含删除指令/凭据泄露/有偏推荐/幻觉路径 → 必须修，不可带病通过
- 场景覆盖率不足 → test prompt 未覆盖 skill 宣称的全部场景类型 → 补充缺失的测试场景

### P1: 结构性问题
- Frontmatter缺少触发词 → 补充中英文触发词
- 缺少Phase/Step结构 → 重组为线性流程
- 缺少用户确认检查点 → 在关键决策处插入

### P2: 具体性问题
- 步骤模糊（"处理图片"）→ 改为具体操作和参数
- 缺少输入/输出规格 → 补充格式、路径、示例
- 缺少异常处理 → 补充 "如果X失败，则Y"

### P3: 可读性问题
- 段落过长 → 拆分+用表格
- 重复描述 → 合并去重
- 缺少速查 → 添加TL;DR或决策树

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
| MAX_ROUNDS 触顶 | quick: 已跑 1 轮仍有短板 / full: 已跑 3 轮仍有短板 | quick 模式只允许 1 轮 Self-Refine，触顶即收工；full 模式不强制 break，展示当前最弱维度问用户「继续加1轮 / 进入 Phase 2.5 / 收工」 |
| 优化后超 150% 体积 | 新文件 > 原 × 1.5 | 拒绝提交，回到改进步骤精简（删冗余/合并重复），再评 |
| 编辑预算超限 | 本轮 token 变化量 > 原 10% | 拒绝执行，拆分方案或精简后重试 |
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
| 4 | **跳过 test-prompts 直接评分** | 没有 test-prompts 的 dim8 是凭空打分，权重 23% 等于编造 | Phase 0.5 强制设计 2-3 prompts；若用户不给，默认编 3 个并展示确认 |
| 5 | **轮内改多个维度** | 多变量同时变，分数升降无法归因到具体改动 | 每轮 1 个维度；相关簇（dim2/3/4）改其一时观察另两个是否跟涨 |
| 6 | **dry_run 比例 > 30%** | dim8 实测维度形同虚设，分数虚高（早期 40 次记录 67% dry_run，0 revert） | 强制至少 1 个真实 full_test；dry_run 多的优化在 results.tsv 显式打 ⚠️ |
| 7 | **静默跳过异常** | 遇到备份/tsv 异常时静默继续，破坏 ratchet 完整性 | 异常表 10 条 fallback 必须先告知用户再处理 |
| 8 | **忽视维度相关性单独优化** | dim2/3/4 是相关簇，单独优化 dim2 时常发现已被前轮 dim3 修复推到顶 | 找最低维度时同时看相关簇短板，决定是否同步改 |
| 9 | **虚构评分依据（幻觉）** | judge 在没有实际读取输出的情况下凭空描述「效果很好」「明显提升」；dry_run 时不引用 SKILL.md 原文 | dim8 评分必须附带原文引用锚定（详见「dim8 幻觉防御」章节）；主 agent 执行真实性抽查，1 处不匹配则整轮作废 |
| 10 | **无预算控制的大步跳跃** | 单轮改动超过原文件 20% token，多变量同时变无法归因；SkillOpt 实证 bounded edit 优于 uncontrolled rewriting | 编辑预算硬约束 ≤10%，超出则拆分多轮 |
| 11 | **忽略拒绝编辑的历史** | 同样的改动方向在上次优化被 revert，本轮只改措辞又提交——拒绝编辑不是偶然 | 每轮 Phase 2 Step 2 先审阅 rejected_edits.md，重叠则绕行 |
| 12 | **跨模式数据混用（v4.0）** | quick 模式训练数据被用于 full 模式评估，或反之——个人风格偏好污染工业合规标准 | quick/full 的 results.tsv 和备份分存储桶，物理隔离，定期渗透测试 |
| 13 | **跳过消费者能力基线（v4.0）** | full 模式下不测目标模型裸能力就直接优化 skill——消费者不行，skill 写得再好也只是纸上谈兵 | full 模式 Phase 1 必须先跑消费者基线，低于阈值阻断 L2 |
| 14 | **忽视 ROI 预检信号（v4.0）** | 连续 3 次优化 Δ<1 分的 skill 仍强行启动完整优化循环——ROI 为负的优化是资源浪费 | Phase 0 ROI 预检低空间时必须提示用户是否跳过 |

**触发场景**：每轮 Phase 2 改动前对照本表一次。任一反模式命中 → 改方案重写。

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
11. **Runtime 中立性** — skill 必须能在 Claude Code、Codex、Cursor、OpenClaw、Hermes 等任何 skills-compatible runtime 中正常运行。除非 skill 名明确绑定单一 runtime（如 `xxx-codex`、`huashu-slides-codex`），任何「在 Claude Code 里」「Claude Code skill」「单一 badge 钉死」「安装命令只给 `.claude/skills/` 一种路径」都视为 gate 不通过，须在 P0 优先修复（详见「Runtime 适配性审查」章节）
12. **引用文件全覆盖** — 维度评分（尤其是 dim6）前必须定位并逐份读取从技能文件分拆出去的所有引用文件（如 references/、examples/、assets/ 等子目录下的文件）；未实际读取引用文件内容即打分视为无效评估，dim6 直接扣 2 分
13. **评分真实性可追溯** — 每个维度的打分理由必须引用被评内容的具体原文（如 SKILL.md 的段落/行号、测试输出的关键片段、引用文件的具体表述）。仅给出抽象评价（"结构清晰""效果不错"）无原文锚定的评分视为疑似幻觉，该维度分不可信并必须重评
14. **Meta-Review 必做** — full 模式下完成 ≥2 个 skill 优化后，必须执行 Phase 2.8 写入 meta_learnings.md；下次优化会话开始前必须先读取

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

## 设计灵感

> "You write the goals and constraints in program.md; let an agent generate and test code deltas indefinitely; keep only what measurably improves the objective."
> — Karpathy, autoresearch

本skill的对应关系：
- **program.md** → 本文件（评估rubric和约束规则）
- **train.py** → 每个SKILL.md
- **val_bpb** → 9维加权总分（含多维仪表盘 + meta-skill 反例黑名单）
- **ratchet** → 只保留有改进的版本
- **test set** → 每个skill的test-prompts.json
- **mode router** → 场景模式选择器（quick / full 双模路由，v4.0）

区别：增加了人在回路（autoresearch是全自主的，skill优化需要人的判断力），以及双重评估机制（结构+效果），因为skill的「好坏」比loss数值更微妙。

### 学术依据 & Credits

- **SkillLens**（arXiv [2605.23899](https://arxiv.org/abs/2605.23899)）：9 维 rubric 的实证来源（LLM 自评 46.4% → 加 meta-skill 三维度后 73.8%）；全生命周期框架（经验生成→技能提取→技能消费）。
- **SkillOpt**（arXiv [2605.23904](https://arxiv.org/abs/2605.23904)）：validation-gated edits 形式化框架；编辑预算（bounded edit）、拒绝缓冲区（rejected-edit buffer）、epoch-wise slow/meta update 三项机制已集成至 luban 的 Phase 2/2.8。代码 [github.com/microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)（`pip install skillopt`）、项目页 [microsoft.github.io/SkillOpt](https://microsoft.github.io/SkillOpt/)。🤝 2026-06-03 微软官方仓库已把 luban-skill 列入集成名单。
- **autoresearch**：[github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)，本 skill 1.0 的原始灵感。

---

## 成果报告

优化完成后，生成 Markdown 格式的成果报告，包含分数变化、改进摘要和关键数据。

### 报告格式

```markdown
## 优化报告 - {skill名}

### 分数变化
- 改前总分：{old_score}
- 改后总分：{new_score}
- 提升：+{delta} 分

### 维度变化
| 维度 | 改前 | 改后 | 变化 |
|------|------|------|------|
| 1. Frontmatter质量 | {dim1_old} | {dim1_new} | {Δ1} |
| 2. 工作流清晰度 | {dim2_old} | {dim2_new} | {Δ2} |
| ... | ... | ... | ... |
| 9. 反例与黑名单 | {dim9_old} | {dim9_new} | {Δ9} |

### 主要改进
1. {改进摘要1}
2. {改进摘要2}
3. {改进摘要3}

### 测试验证
- 测试模式：{eval_mode}（full_test / dry_run）
- 测试 prompt 数：{n}
- 输出质量变化：{描述}

### 优化历史
- 优化轮次：{rounds}
- 保留改进：{keep_count}
- 回滚次数：{revert_count}
```

### 资源文件速查

| 路径 | 用途 |
|---|---|
| `results.tsv` | 历次优化日志（9列含 eval_mode） |
| `{skill目录}/test-prompts.json` | 每个 skill 的测试 prompt 集（用于维度8实测） |
| `rejected_edits.md` | 被 revert 的编辑方案永久负反馈（SkillOpt rejected-edit buffer） |
| `meta_learnings.md` | 跨 skill 优化规律沉淀（SkillOpt slow/meta update） |

### 何时生成

- **单skill报告**：每个skill优化完成后，展示该skill的分数变化和改进摘要
- **总览报告**：全部优化完成后（Phase 3），展示全局战绩和汇总数据
