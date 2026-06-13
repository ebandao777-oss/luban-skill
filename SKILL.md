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
- 被优化技能的数据文件（`diagnostics.tsv` / `rejected_edits.md` / `test-prompts.json` / `results.tsv`）放在**被优化 skill 自己的目录**下
- 鲁班全局文件（`meta_learnings.md` / `luban-profile.json` / `optimization-registry.tsv`）放在 `luban-workspace/`

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

1. **读**：`read_text` 读取目标 SKILL.md 全文
2. **改**：`edit_file` 执行编辑（Quick 模式直接用 `.bak` 备份；Full 模式先 `git commit` 暂存）
3. **验**：按 Rubric 逐项自检本次改动影响的维度（dim1/4/7a/9 按评分标准逐条核对，dim2/3/5 通读确认未引入新问题），不通过则回退

---

## 📋 阅读导航

| 如果你想… | 读哪里 | 预计耗时 |
|:---|:---|:---|
| 只想快速开始 | [QUICKSTART.md](./QUICKSTART.md) | 2 分钟 |
| 知道怎么评分 | [评估 Rubric](#评估-rubric10-维度总分-100) | 5 分钟 |
| 了解优化全流程 | [优化流程（Phase 0-3）](#优化流程phase-0-3) | 10 分钟 |
| 遇到错误不知道怎么处理 | [异常与边界条件](#异常与边界条件) / [反模式与FAQ](#反模式与faq) | 3 分钟 |
| 查某个模块做什么 | [资源文件速查](#资源文件速查) | 2 分钟 |
| 查优化策略怎么选 | [优化策略库](#优化策略库) | 5 分钟 |
| 了解学术背景 | [学术依据](#学术依据) | 1 分钟 |

---

> 📍 你在这里: 鲁班.Skill > 评估 Rubric

## 评估 Rubric（10 维度，总分 100）

> SkillLens（arXiv 2605.23899）实证 LLM-as-judge 准确率仅 46.4%，加入 meta-skill 三维度后提升到 73.8%。

### 评分类型

| 维度 | 权重 | 类型 | 评分方式 |
|:---|:---:|:---|:---|
| dim1 Frontmatter质量 | 7 | 确定性 | name 规范、description 含做什么+何时用+触发词、≤1024 字符、禁结尾空话。三项全过=10，任一缺失=0 |
| dim2 工作流清晰度 | 12 | LLM | 步骤明确可执行、有序号、每步有明确输入/输出 |
| dim3 失败模式编码 | 12 | LLM | 显式编码失败模式（"如果 X 失败 → Y"）；有 fallback 路径和错误恢复。只写正向流程不写失败分支扣 ≥3 分 |
| dim4 检查点设计 | 6 | 确定性 | 正则 `/CHECKPOINT\|STOP\|🔴\|⛔/`：≥1 处 STOP 级=10，仅 CHECKPOINT=5，无=0 |
| dim5 可执行具体性 | 17 | LLM | 有具体参数/格式/示例；前置扫描软化词（建议/可考虑/根据情况/灵活把握/视情况而定/可能/大概）注入评分上下文。HASP 模块独立产出 dim5 确定性子分 3/17。 |
| dim6 资源整合度 | 4 | LLM | references/assets 引用正确、路径可达。SkillOps 模块独立产出 dim6 确定性子分 3/4。 |
| dim7 整体架构 | 12 | 混合 | **7a 结构合规(6)**：确定性，标题层级连续不跳跃 + 含 ≥3/4 必含章节→6 分，每缺一项 −2。<br>**7b 语义质量(6)**：LLM judge，冗余段落/AI 腔废话（"说白了/换句话说/首先其次综上"/花叔禁用词）/重复描述→一处 −1，下限 0 |
| dim8 实测表现 | 20 | LLM | 子维度：**8a 意图完成度(8)**——输出是否完成用户意图、偏离程度；**8b 净提升幅度(7)**——带 skill vs 不带 baseline 质量提升是否明显；**8c 副作用(5)**——skill 是否引入过度冗余/跑偏/格式异常。总分/20×20 |
| dim9 反例与黑名单 | 6 | 混合 | **两段式**：①关键词扫描（`不要\|禁止\|不允许\|反例`）→≥3 处方进入 ②LLM judge 评估反例质量（是否独立章节、含反模式+为什么+替代做法、覆盖核心风险场景）。Step 1 不通过=0，通过后 Step 2 产出 0-10 映射为最终分 |
| dim10 安全与审查门控度 | 4 | 公式 | Sentinel 2 + P0/P1 审查 2 占比合并。Quick 模式默认满分。P0 任一未闭合→上限锁死 ≤40。 |

权重和：7+12+12+6+17+4+12+20+6+4 = **100**。确定性维度覆盖 25/100=25%，LLM 承担 71 分，dim10 公式计算 4 分。

### 评分公式

维度总分 = Module 子分 + Rubric 子分（同维占比加权合并）。dim5/dim6/dim7b/dim10 四维有模块介入，其余维度仅 Rubric。

```
加权原始分 = (dim1×7 + dim2×12 + dim3×12 + dim4×6 + dim5×17 + dim6×4 + dim7a×6 + dim7b×6 + dim8×20 + dim9×6 + dim10×4) / 10
```

### 架构总览

```
                          ┌──────────────────────────────────────┐
                          │      鲁班.Skill 技能自进化调度器       │
                          │   事件驱动 + 定时轮询 + 按需触发       │
                          └────────────────┬─────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
    ┌─────────┴──────────┐      ┌─────────┴──────────┐      ┌─────────┴────────────┐
    │   模块层（缺陷检测）   │    │ 核心引擎（评分+修复）│      │   事件钩子（旁路）    │
    │ SkillOps 定期体检   │      │                    │      │  编辑完成 → MUSE 回归 │
    │ EvoSkill 失败驱动   │ 子分 │  Phase 0   初始化   │      │  错误反馈 → EvoSkill  │
    │ HASP     规则硬化   │───→  │  Phase 0.3 模块检测 │      │  规则连续忽略 → HASP  │
    │ CASCADE  知识更新   │      │  🔴 CHECKPOINT     │      └──────────────────────┘
    │ Distill  精简瘦身   │      │  Runtime Gate      │
    │ Sentinel  安全审计  │      │  Phase 0.5 测试设计 │
    └────────────────────┘      │  🔴 CHECKPOINT     │
              │                 │  Phase 1  基线评估 │
              │                 │  🔴 CHECKPOINT     │
              │                 │  Phase 2  优化循环 │
              │                 │  Phase 2.5探索重写 │
              │                 │  Phase 3  汇总报告  │
              │                 └─────────┬──────────┘
              │                           │
              │      diagnostics.tsv      │   results.tsv
              │      (模块子分清单)        │   (评分+优化记录)
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
```

### dry_run 降权规则

dry_run 模式下确定性维度不受影响；LLM 维度处理：

| 维度 | dry_run 处理 | 原因 |
|:---|:---|:---|
| dim2/3/5/6/7b/9 | 标注 `[confidence: degraded]`，不降分 | 结构/语义维 LLM 评估不受执行模式影响 |
| dim8a 意图完成度 | 原始分 ×0.5 | 无实测，推演值置信度低 |
| dim8b 净提升幅度 | 原始分 ×0.3 | 无 baseline 对照，推演几乎无意义 |
| dim8c 副作用 | 正则扫描可用（冗余段落/格式异常检测），不降权 | 部分可静态检测 |
| dim10 | 默认 100（同 Quick 模式） | full_test 才能触发门控 |

反例 #6 强制约束：total dry_run_ratio > 30% 时必须至少跑 1 个 full_test。

### 模块子分规则（Phase 0.3 产出 → Phase 1 同维合并）

模块不独立扣分，而是产出同维内的确定性子分，与 Rubric LLM 子分合并为维度总分。

**子分占比**（模块 / Rubric）：

| 维度 | 权重 | Module 子分 | Rubric 子分 | 依据 |
|:---|:---:|:---|:---|:---|
| dim5 | 17 | HASP 3 | LLM 14 | 软化词是 gate，具体性是核心 |
| dim6 | 4 | SkillOps 3 | LLM 1 | 路径断裂是致命缺陷，编排判断在可用前提下才有意义 |
| dim7b | 6 | Distill 2 | LLM 4 | 文件级冗余信号粗，段落级语义细 |
| dim10 | 4 | Sentinel 2 | P0/P1 审查 2 | 模式覆盖广度 + 推理深度互补 |

**Module 子分计算**：

| 模块 | 检测项 | 子分计算 | 满分 | 关联维度 |
|:---|:---|:---|:---:|:---|
| SkillOps | 引用路径可达性 | 全完整=3，断裂 ≥3 处=0，1-2 处→线性 | 3 | dim6 |
| SkillOps | YAML/Frontmatter 非法 | 计入 dim1 确定性评分，不计子分 | — | dim1 |
| HASP | 软化词 ≥5 处 | 0 处=3，≥5=0，1-4→线性 | 3 | dim5 |
| HASP | 违规计数 ≥2 次 | 计入 Sentinel 子分，不计独立子分 | — | dim10 |
| CASCADE | 外部引用过期 >180 天 | 0 处过期=dim6 SkillOps 子分不变；≥1 处→标注但由 SkillOps 子分反映 | — | dim6 |
| Distill | 完全未被引用的 references | 0 个=2，≥1 个=0 | 2 | dim7b |
| Distill | F_approx ≥0.7 文件 ≥2 个 | ≥2 个→子分 −1（与死文件子分累加，下限 0） | — | dim7b |
| EvoSkill | 历史振荡（同维度 2+ 轮反复涨跌） | 仅标注 `[oscillation]`，**不产生子分** | — | dim3 |
| Sentinel | 恶意指令（exec/system/subprocess/rm−rf/format 等） | 0 类命中=2，每类命中 −0.5，下限 0 | 2 | dim10 |
| Sentinel | 硬编码凭据（API Key/密码/token 明文） | 同上 | 2 | dim10 |
| Sentinel | Prompt 注入模式（DAN/越狱/simulate/system override 等） | 同上 | 2 | dim10 |
| Sentinel | 数据外泄路径（SMTP/上传外网/SCP 等） | 同上 | 2 | dim10 |
| Sentinel | 权限越权（chmod/chown/sudo/icacls 等） | 同上 | 2 | dim10 |

**dim10 Sentinel 子分**：5 类独立计分，每类 0-2 分（0 命中=2，≥2 处命中=0，1 处=1），5 类取均值直接作为 Sentinel 子分（范围 [0,2]）。

**dim10 审查子分**：起始 2 分，P0 未闭合每项 −2.0，P1 未闭合每项 −0.5，下限 0。即 `审查子分 = max(0, 2 − P0未闭合数 × 2.0 − P1未闭合数 × 0.5)`。任一 P0 未闭合即清零审查子分，P1 累积 4 项可归零。结合 dim10 上限锁死 ≤40 规则形成双重门控。

模块子分存入 `diagnostics.tsv`（子分列替代原扣分列），Phase 1 从 diagnostics.tsv 读取，与 Rubric 子分合并为维度总分。

### Runtime 中立性 Gate（前置于 Phase 1）

参照 darwin 设为独立 gate，在 Phase 0.3 之后、Phase 1 之前执行。扫描 SKILL.md 全文：

| 检测项 | 判定 | 命中动作 |
|:---|:---|:---|
| 单 runtime 措辞（"在 Claude Code 里"/"Cursor 用户请"等） | ❌ 不通过 | 标记 `[runtime_gate: fail]`，强制 Phase 2 第一轮 P0 修复 |
| 安装路径写死单一工具链 | ❌ 不通过 | 同上 |
| 单一 badge/标识语 | ❌ 不通过 | 同上 |
| 例外：skill name 含单 runtime 标识（如 `xxx-codex`） | ✅ 豁免 | 不触发 gate |

命中任一项则打断流程，报告具体违规位置（行号+原文），要求修复后重新通过此 Gate → Phase 0.5。免检白名单：skill name 明确绑定单一 runtime。

### 十维执行模式

| 维度 | Quick 模式 | Full 模式 | 评分方 |
|:---|:---|:---|:---|
| dim1 Frontmatter | agent 按评分标准逐项检查 | 同 Quick | 确定性 |
| dim2 工作流 | LLM judge | LLM judge（多评委中位数） | LLM |
| dim3 失败模式 | LLM judge | LLM judge（多评委中位数） | LLM |
| dim4 检查点 | agent 正则扫描 CHECKPOINT/STOP/🔴/⛔ | 同 Quick | 确定性 |
| dim5 具体性 | LLM judge（前置软化词扫描注入上下文） | LLM judge（多评委中位数+软化词扫描）+ HASP 3 占比合并 | LLM |
| dim6 资源整合 | LLM judge | SkillOps 3 + LLM 1 占比合并 | 混合 |
| dim7a 结构合规 | agent 检查标题层级 + 必含章节 | 同 Quick | 确定性 |
| dim7b 语义质量 | LLM judge（冗余/AI 腔/重复） | Distill 2 + LLM 4 占比合并 | LLM |
| dim8 实测 | dry_run 推演（降权规则见上） | full_test（子 agent 跑 test-prompts） | LLM |
| dim9 反例 | 两段式：关键词扫描→LLM judge | 同 Quick | 混合 |
| dim10 安全与审查门控度 | 默认 100 | Sentinel 2 + P0/P1 审查 2 占比合并 | 公式 |

---

> 📍 你在这里: 鲁班.Skill > 双模策略

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

- **Quick→Full**：Quick 模式下 3 轮内 Δ > 5 分，自动升级 Full（有金矿）
- **Full→Quick**：Full 模式下连续 3 个 skill 稳定 delta < 3，后续降级 Quick（成熟稳定）

---

> 📍 你在这里: 鲁班.Skill > 约束规则

## 约束规则

1. **不改变 skill 核心功能和用途** — 只优化"怎么写"和"怎么执行"，不改"做什么" → 白话：鲁班只是润色师，不是重写师。skill 该干嘛还干嘛，只把话说得更清楚
2. **不引入新依赖** — 不添加 skill 原本没有的 scripts 或 references 文件 → 白话：不能为了让评分好看就给 skill 偷偷塞新文件，只能用现有的东西优化
3. **每轮只改一个维度** — 避免多个变更导致无法归因；相关簇（dim2/3/4）改其一时观察另两个是否跟涨 → 白话：一次只动一个地方，改完看效果，别东改西改不知道哪一步起了作用
4. **保持文件大小合理** — 优化后 SKILL.md ≤ 原文件 150% 体积 → 白话：优化不是堆字数，膨胀超过一半就是水内容了
5. **尊重花叔风格** — 中文为主、简洁为上 → 白话：别把简洁的中文改成长篇英文论文腔
6. **可回滚** — 所有改动在 git 分支上，用 `git checkout` 而非 `git reset --hard` → 白话：改坏了能一键退回，而且退回记录留痕可查
7. **评分独立性** — 效果维度必须用子 agent 独立评分，禁止同一 context「改完直接评」→ 白话：不能自己改完自己打分，那等于既当运动员又当裁判
8. **Runtime 中立性** — skill 必须能在 Claude Code、Codex、Cursor、OpenClaw 等任何 skills-compatible runtime 正常运行。除非 skill name 明确绑定单一 runtime（如 `xxx-codex`），任何单 runtime 措辞、单一 badge、安装路径写死均视为 gate 不通过，须在 P0 优先修复 → 白话：skill 不能只在某一个工具里能用，写的时候要通用，除非名字本身就标明了只给某个工具用
9. **编辑同源检测** — 编辑 agent 与评分 agent 来自同一 context → dim8 所有子维度分 ×0.5，results.tsv 记录 `redline_1_violation=true` → 白话：如果编辑和评分是同一个 agent 做的，效果分直接砍半——因为很可能有偏见

### 架构红线运行时检测

1. **禁止 self-edit-self-evaluate**：同一 agent 不得既编辑又评分。违反 → dim8 降权 ×0.5
2. **禁止跨维度打包修改**：一轮只改一个维度。违反 → 整轮回滚
3. **禁止 dry_run 为 full_test**：dim8 全部 dry_run 等于跳过效果验证。违反 → results.tsv 标记 invalid
4. **禁止 bypass gate**：P0 未闭合不得进入下一 phase。违反 → 中断流程

---

> 📍 你在这里: 鲁班.Skill > 多评委与多角色评分

## 多评委与多角色评分（Full 模式）

### 同质多评委（压制采样噪声）

Full 模式采用 2 个独立 file-agent 评委（dispatch_task），评分取中位数。2 个评委读同一份 SKILL.md 和同一套量规，系统性高估方向一致——中位数不纠正共享偏误。

### 异质评委（按需触发）

| 触发条件 | 异质评委 | 复核焦点 |
|:---|:---|:---|
| dim1≥9 且 dim8a ≤5 | search-agent | dim1/dim3 真实性抽查 |
| dim8c =5 且 dim9≤3 | computer-agent | 副作用复核 |
| dim4≥9 但从未触发过 revert | computer-agent | dim4/dim10 架构抽查 |

异质评委不计入标准评委数量，结果以 `[orthogonality]` 标注追加到评分卡。

### 多角色并行审查（P0/P1/P2 分级）

当 dim8c < 5 或 dim10 原始分 < 60 时触发。角色组合按文档类型选派：

| 文档类型 | 角色组合 |
|:---|:---|
| 架构设计 | 系统架构师（分层一致性/接口完整性/模块耦合度）+ 安全架构师（审计链完整性/熔断回滚安全性/红线可绕过性）+ SRE（故障恢复路径/降级策略覆盖/告警闭环） |
| 安全规范 | 安全架构师 + 系统架构师 + 技术文档编辑（术语一致性/引用完整性/格式规范） |
| ML 论文 | ML 研究员（测量有效性/退化检测/偏差控制/过拟合防御）+ 系统架构师 + 技术文档编辑 |
| 综合类 | 系统架构师 + 安全架构师 + SRE + ML 研究员 + 技术文档编辑 |

**审查严重度分级**（直接影响 dim10 审查子分）：

| 级别 | 定义 | 审查影响 | 门控 |
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
| 同质多评委 | 主 agent 单次 LLM 评分，不取中位数 | `judge_count=1`，`eval_mode=fallback` |
| 异质评委 | 跳过，不执行 | — |
| 多角色并行审查 | 跳过阶段 0-4，dim10 默认 100 | `eval_mode=fallback` |
| dim8 效果维度 | 无法跑 full_test，降为 dry_run 推演 | `eval_mode=fallback_dry` |
| Phase 2 Step 5 重评 | 主 agent 单次评分，不 spawn 子 agent | `judge_count=1` |

降级模式下 dim8 子维度处理：8a 意图完成度 → 推演值 ×0.3（无实测置信度低）、8b 净提升 → 推演值 ×0.3（无 baseline 对照）、8c 副作用 → 正则扫描（格式异常/冗余文本检测）。降级原因写入 results.tsv note 字段。

**警告**：降级模式评分不可与 full_test 评分直接比较——降级分虚高。连续 3 轮降级需在汇总报告中显式标注。

---

> 📍 你在这里: 鲁班.Skill > 优化流程

## 优化流程（Phase 0-3）

### Phase 0: 初始化

> **Quick 模式**：跳过 step 2（不建 git 分支），其余相同。

```
1. 确认优化范围：全部 skills 或用户指定列表
2. git checkout -b auto-optimize/YYYYMMDD-HHMM
3. 检查 results.tsv 是否存在，不存在则创建并写入表头（12 列）
4. 读取 results.tsv 了解历史评分
5. ROI 前置评估：若历史基线分 ≥85 且最低维度分 ≥7 → 跳过优化，告知用户「天花板已近，建议仅评估不改」
6. 从 results.tsv 读取 status=revert 的历史维度，标记为「绕行」；对照反例黑名单 8 条，确认当前方案不命中
7. 检查 diagnostics.tsv 是否存在，不存在则创建并写入表头（模块/维度/子分/文件/行号/详情）
```

### Phase 0.3: 模块缺陷检测（子分清单）

六模块对目标 skill 做静态检测，输出确定性子分到 diagnostics.tsv。**模块不产生评分，只产子分**。

```
for each skill:
  1. 按优先级顺序执行：SkillOps → EvoSkill → HASP → CASCADE → Distill → Sentinel
  2. 每模块按「模块子分规则」逐项检测
  3. 命中缺陷 → 追加 diagnostics.tsv 一行（模块/维度/子分/文件/行号/详情）
  4. 模块完成后不回写 SKILL.md，仅写入子分记录
```

EvoSkill 例外：振荡检测仅标注 `[oscillation]`，不产生子分，供 Phase 2 Step 1 人工决策。

Sentinel 执行方式：运行 `scripts/security_audit.py <skill_dir> --diagnostics <path>`，扫描目标 skill 的 scripts/ + references/ 中所有文本文件（排除 SKILL.md 文档层描述），匹配 5 类模式：
- **恶意指令**：`exec(` / `system(` / `subprocess` / `rm -rf` / `format` / `del /f` / `reg delete`
- **硬编码凭据**：`api_key=` / `password=` / `token=` / `secret=` / 私钥 PEM
- **Prompt 注入**：`DAN` / `jailbreak` / `simulate` / `system override` / `ignore.*instructions`
- **数据外泄**：`smtp` / `upload.*external` / `scp` / `ftp upload`
- **权限越权**：`chmod` / `chown` / `sudo` / `su -` / `icacls`

🔴 CHECKPOINT：展示子分摘要（各维度子分、哪些模块有输出、EvoSkill 振荡告警、Sentinel 安全告警），确认后进入 Runtime 中立性 Gate → Phase 0.5。

### Runtime 中立性 Gate

扫描 SKILL.md 全文，命中 Runtime 中立性 Gate 中任一未豁免项则打断流程，报告违规行号+原文，要求修复后重新进 Phase 1。通过后进入 Phase 0.5。

### Phase 0.5: 测试 Prompt 设计

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

展示所有 prompt 给用户，🔴 CHECKPOINT · 🛑 STOP 确认后进入 Phase 1。

### Phase 1: 基线评估

维度总分 = Module 子分 + Rubric 子分（同维内按比例加权合并）。dim5/dim6/dim7b/dim10 四维有模块介入，其余维度仅 Rubric。

```
for each skill:
  1. 按 Rubric 表逐维评分，得各维度 Rubric 子分
  2. 读取 diagnostics.tsv，取 Module 子分
  3. 同维合并：dim5 = (HASP子分 × 3 + Rubric子分 × 14) / 17 × 10
              dim6 = (SkillOps子分 × 3 + Rubric子分 × 1) / 4 × 10  # SkillOps=0 不归零 Rubric（Rubric 评估语义完整性，与引用可达性正交）
              dim7b = (Distill子分 × 2 + Rubric子分 × 4) / 6 × 10
              dim10 = (Sentinel子分 × 2 + P0/P1审查子分 × 2) / 4 × 10
              其余维度 = Rubric子分 × 10
  4. 效果评分：spawn 子 agent 跑 test-prompts
     - with_skill: 带 SKILL.md 执行
     - baseline: 不带 skill 直接执行（裸 prompt）
  5. 加权计算总分，记录到 results.tsv
```

Full 模式额外执行消费者能力基线测试：若 `references/baseline-skill.md` 不存在，则按当前所评估 skill 的核心领域自动生成一份通用基线 skill（含 name/description/workflow/约束规则 等基本结构），保存到该路径。用 baseline-skill 测目标模型裸能力，若 baseline-skill 评分 < 60 则输出能力不足报告并阻断后续优化。此测试独立于 dim8 的 with_skill vs baseline 对比，不要混淆。

🔴 CHECKPOINT：展示基线分 + diagnostics 诊断摘要，确认后进入 Phase 2。

### Phase 2: 优化循环

> **Quick 模式**：不建 git 分支，Step 3 用 `cp SKILL.md SKILL.md.bak` 代替 git commit，Step 6 用 `cp SKILL.md.bak SKILL.md` 代替 git checkout 回滚。

```
for each skill（按基线分数升序，先优化最弱的）:
  round = 0
  while round < MAX_ROUNDS:
    round += 1

    # Step 0: 模块检测（每轮重新执行）
    重新运行 Phase 0.3 六模块检测 → 更新 diagnostics.tsv（子分清单）
    EvoSkill 读取最新的 results.tsv，HASP 读取最新的 SKILL.md，Distill 重算密度

    # Step 1: 诊断
    读取更新后的 diagnostics.tsv + results.tsv 最新评分
    找子分最低或得分最低维度。注意 dim2/3/4 是相关簇——修一个时另两个常跟涨。
    EvoSkill 振荡标注 `[oscillation]` 的维度→跳过不改，除非用户明确要求。

    # Step 2: 提方案
    1 个具体改进方案：改什么（段落/行）+ 为什么（对应 rubric 哪条）+ 预期提升。
    对照反例黑名单 8 条 + rejected_edits.md + luban-profile.json oscillation_guard，命中 → 改方案重写。

    # Step 3: 编辑前备份
    git add -A && git commit -m "pre-edit: {skill_name}"

    # Step 4: 执行改进
    编辑 SKILL.md（字符变化 ≤10%） → 按 Rubric 逐项自检 dim1/4/7a/9

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

**Phase 2 出口**：全部 skill 优化完成后 → 检查 Phase 2.5 触发条件：满足则进入 Phase 2.5，否则进入 Phase 3。

### Phase 2.5: 探索性重写（按需触发）

连续 2 个 skill 都在 round 1 break 时触发（或单 skill 连续 2 轮 round 1 break）：git stash → 从头重写 SKILL.md → 重新评估 → 重写版 > stash 版则采用，否则 git stash pop。🛑 STOP：必须征得用户同意。

### Phase 3: 汇总报告

展示全局战绩：

| 项目 | 内容 |
|:---|:---|
| 优化 skill 数 | N 个，保留 M 个 |
| 分数变化 | 表格（skill名/旧分/新分/Δ/主要改进维度） |
| 主要改进摘要 | 按维度聚类，标注高频改进方向 |
| 健康度仪表盘 | Full 模式：dry_run 比例、revert 率、同源检测触发次数、oscillation 告警 |

#### Epoch Meta-Review（Full 模式）

```
1. 汇总本次所有 skill 的优化记录
2. 提炼可迁移规律 → 追加到 meta_learnings.md
3. 识别 oscillation 模式：同一维度在 2+ skill 间反复涨跌 → 追加到 luban-profile.json：

{
  "oscillation_guard": [
    {"dimension": "dim5", "skills": ["skill-a", "skill-b"], "pattern": "细化→回滚→细化→回滚", "recommendation": "跳过 dim5 优化，先加固 dim3"}
  ]
}

此字段供后续 Phase 2 Step 2 查阅，命中则跳过该维度。
```

### 备份轮转策略

git 分支无限增长会导致仓库膨胀。Phase 3 完成后触发清理：

- 每个 skill 目录保留最近 **5 轮编辑**的备份（`latest-5`）
- baseline 备份和首轮备份**永久保留**，不受轮转影响
- 超出 5 轮的历史备份移至 `luban-backups-archive/{skill_name}/` 归档

---

> 📍 你在这里: 鲁班.Skill > 优化流程 > 异常与边界条件

## 异常与边界条件

流程假设环境理想，但实操常遇异常。以下预定义 fallback，保证优化不会「一跑就卡住」。

| 场景 | 触发条件 | 处理动作 | 通俗解释 |
|:---|:---|:---|:---|
| 不在 git 仓库 | `git rev-parse` 失败 | 询问用户：执行 `git init` 或回退到文件备份；用户选后者则 `cp SKILL.md SKILL.md.bak.YYYYMMDD-HHMM` 代替 revert | 找不到 Git 仓库，优化历史无法记录。可以新建仓库或用文件备份代替 |
| results.tsv 缺失 | 文件不存在 | 新建并写表头行（12 列） | 评分记录文件还没创建，这是第一次跑优化，自动建一个 |
| results.tsv 损坏 | 列数不匹配 / 非 TSV | 备份为 `.bak.YYYYMMDD-HHMM` 后重建，告知用户 | 评分记录文件格式坏了（可能是手动编辑过），旧文件备份后再建新的 |
| 分支已存在 | `git checkout -b` 失败 | 分支名末尾加 `-2` / `-3`；第 3 次失败切回现有分支并询问继续还是新起 | Git 分支名冲突了，自动换名字重试，最多 3 次 |
| git revert 失败 | 冲突 / 工作树脏 | 先 `git stash` 重试；仍失败则从上一个 commit 读出 SKILL.md 覆盖当前文件手动恢复 | 回滚时文件有冲突，先暂存当前修改再试，实在不行直接读上一个版本覆盖 |
| MAX_ROUNDS 触顶 | 已达上限仍有短板 | 不强制 break，展示当前最弱维度问用户「继续加 1 轮 / 进入探索性重写 / 收工」 | 优化轮数到上限了但还有改进空间，让你决定要不要继续 |
| 优化后超 150% 体积 | 新文件 > 原 × 1.5 | 拒绝提交，回精简（删冗余/合并重复）后重评 | 改完后文件膨胀太厉害（超过原来的 1.5 倍），先瘦身再提交 |
| test-prompts.json 已存在 | 文件已在 skill 目录 | 默认复用并展示，问用户「复用 / 重写 / 追加」三选一 | 测试题已经有了，问你是直接复用还是重新出题 |
| SKILL.md 找不到 | 目录存在但无 SKILL.md | 该 skill 终止，results.tsv 记 `status=error`，继续下一个 | 这个 skill 目录里没有主文件，跳过它继续处理下一个 |
| 消费者基线失败 | 目标模型裸能力不足 | 输出能力不足报告，阻断后续优化 | 当前模型的裸能力不够，强行优化效果会差，先停掉 |
| 子 Agent 不可用 | `dispatch_task` 返回错误 | 触发降级模式（见多评委章节），results.tsv 记 `eval_mode=fallback` | 独立评分工具不可用（环境限制），降级为单 agent 评分 |
| 分数精度漂移 | 总分差 < 0.05 | 总分保留 1 位小数，改进需严格 > 旧分（不靠四舍五入） | 分数变化太小（不到 0.05 分），不算真正提升 |

**原则**：异常先告知用户，再按规则处理；绝不静默跳过或静默失败。

---

> 📍 你在这里: 鲁班.Skill > 关键数据结构

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
- 文件位置：被优化 skill 目录下的 `results.tsv`

### diagnostics.tsv

模块子分清单（Phase 0.3 产出），每模块对目标 skill 的静态缺陷检测结果：

```
模块	维度	子分	文件	行号	详情
SkillOps	dim6	3	-	-	全引用路径可到达
HASP	dim5	1	SKILL.md	-	软化词 3 处（建议×2/可考虑×1）
EvoSkill	dim3	—	-	-	[oscillation] dim5 历史 3 轮回弹
```

- 文件位置：被优化 skill 目录下的 `diagnostics.tsv`
- Phase 0.3 每次运行前**清空重建**（保持最新一轮子分）
- Phase 1 读子分按维度取 Module 子分，与 Rubric 子分占比加权合并
- EvoSkill 不产生子分，`子分=—`，详情标注 `[oscillation]`

### optimization-registry.tsv

鲁班全局优化登记表（鲁班自己的目录下），记录每次对某个 skill 执行的优化：

- `skill_name`：被优化的 skill 名
- `timestamp`：运行时间戳（ISO 8601）
- `score_before`：优化前分数
- `score_after`：优化后分数
- `rounds`：本次运行的优化轮次
- `eval_mode`：`full_test` / `dry_run`
- 只增不删，每次 `luban optimize` 追加一行
- 文件位置：`luban-workspace/optimization-registry.tsv`

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

跨 skill 可迁移规律，Phase 3 Meta-Review 追加：

```markdown
## ML-{序号} | {时间戳}

- **规律**: dim2/3/4 相关簇——修 dim3（三段式 fallback）时 dim2 平均跟涨 1.5 分
- **来源 skill**: luban-slides, code-reviewer（2/2 验证）
- **置信度**: 高
- **可复用场景**: 任何有"步骤描述"+"错误处理"双薄弱点的 skill
```

---

> 📍 你在这里: 鲁班.Skill > 反例黑名单

## luban 操作反例黑名单

来自早期 40 次 0 revert 的教训。每轮 Phase 2 Step 2 改动前对照一次，命中 → 改方案重写。

| # | 反模式 | 替代做法 |
|---|--------|----------|
| 1 | 同 context 自评自改 | 必须 spawn 独立子 agent 评分 |
| 2 | `git reset --hard` 当回滚 | 用 `git checkout` 保留追溯链 |
| 3 | 为凑分增冗余 | 触顶信号（连续 2 轮 Δ<2）→ break |
| 4 | 跳过 test-prompts 直接评分 | Phase 0.5 强制设计 2-3 prompts |
| 5 | 轮内改多个维度 | 每轮 1 个维度 |
| 6 | dry_run 比例 > 30% | 强制至少 1 个 full_test |
| 7 | 静默跳过异常 | 异常表 fallback 必须先告知 |
| 8 | 忽视维度相关性单独优化 | 看相关簇短板再决定 |

> 📎 HASP / CASCADE / Distill / MUSE / 调度器 模块完整流程 → [references/modules.md](./references/modules.md)


## 优化策略库

按优先级排序，每轮只做最高优先级的一个。命中即停止向下检索。

### P0: 适配性与效果问题（gate 项，必须先修）

| 类型 | 识别特征 | 优化策略 | 关联维度 |
|:---|:---|:---|:---|
| Runtime 绑定 | SKILL.md 出现单 runtime 措辞（如「在 Claude Code 里」）、安装指引只给一种路径、工作流硬编码 runtime 工具无 fallback | 替换为 runtime-neutral 措辞；安装改为「一行命令自动检测 + 手动路径表」；标注「仅在某 runtime 可用」 | dim6/dim8 |
| 效果倒退 | 带 skill 比不带还差 | skill 过度约束，精简指令 | dim8 |
| 输出偏离 | 测试输出不符合预期 | 检查是否有误导性指令；补充明确输出模板 | dim8 |
| 副作用触发 | dim8c 命中 | 逐项检查副作用来源，修复后重测 | dim8/dim10 |
| Sentinel 安全告警 | security_audit.py 命中恶意指令/硬编码凭据/Prompt注入/数据外泄/权限越权 | 恶意指令→移除或授权；凭据→环境变量替代；注入→增加 guards；外泄→去除网络出口；越权→降级为普通操作 | dim10 |

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

> 📍 你在这里: 鲁班.Skill > HL 操作速查

## HL 操作速查

3 条高杠杆操作：

- **HL-1（dim4）显性视觉标记是杠杆**：加 🔴 CHECKPOINT / 🛑 STOP。4 行改动撬动 dim4 +3 分
- **HL-2（dim2/3/4 相关簇）三段式 fallback 一石三鸟**：修 dim3（触发条件/一线修复/仍失败兜底）→ dim2 跟涨 1-2 分，dim4 顺便补检查点
- **HL-3（Phase 2 退出）触顶自动 break**：+0.15 是停手信号，不是继续信号

完整红线定义见上文「架构红线运行时检测」4 条。

---

> 📎 HASP / CASCADE / Distill / MUSE / 调度器 模块完整流程 → [references/modules.md](./references/modules.md)

---

> 📍 你在这里: 鲁班.Skill > 资源文件速查

## 资源文件速查

| 路径 | 用途 |
|------|------|
| `optimization-registry.tsv` | 鲁班全局优化登记表（哪些 skill 跑过、分数） |
| `{skill目录}/test-prompts.json` | 每个 skill 的测试 prompt |
| `{skill目录}/tests.yaml` | MUSE 回归测试用例（持续沉淀） |
| `scripts/skillops_scanner.py` | SkillOps 工具化扫描（路径/YAML/引用链结构分析） |
| `scripts/evo_skill_patcher.py` | EvoSkill 失败驱动补丁建议生成 |
| `scripts/hasp_hardener.py` | HASP 规则硬化（软化词检测→Must/PF 升级） |
| `scripts/cascade_updater.py` | CASCADE 外部引用过时检测与更新建议 |
| `scripts/distill_analyzer.py` | Distill 引用矩阵构建与 F_approx 计算 |
| `scripts/muse_generator.py` | MUSE 测试用例自动生成与回归执行 |
| `scripts/security_audit.py` | Sentinel 安全审计（恶意指令/凭据/注入/外泄/越权） |
| `references/SA-DM.md` | SkillOps 设计方法论完整论文 |
| `references/baseline-skill.md` | 消费者能力基线测试参考 skill（首次运行时自动生成） |

---

> 📎 反模式、FAQ、架构红线 → [references/faq.md](./references/faq.md)
