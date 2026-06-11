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

1. **读**：`read_text` 读取目标 SKILL.md 全文
2. **改**：`edit_file` 执行编辑（Quick 模式直接用 `.bak` 备份；Full 模式先 `git commit` 暂存）
3. **验**：按 Rubric 逐项自检本次改动影响的维度（dim1/4/7/9 按评分标准逐条核对，dim2/3/5 通读确认未引入新问题），不通过则回退

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
    └────────────────────┘      │  CHECKPOINT       │
              │                 │  Phase 2  优化循环 │
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
```

### dry_run 降权规则

dry_run 模式下确定性维度不受影响；LLM 维度处理：

| 维度 | dry_run 处理 | 原因 |
|:---|:---|:---|
| dim2/3/5/6 | 标注 `[confidence: degraded]`，不降分 | 结构维度，不依赖实际执行 |
| dim8 全部子维度 | 原始分 ×0.5 | 无实测，Accuracy/Safety/Compliance 均为推演 |
| dim10 | 默认 100（同 Quick 模式） | full_test 才能触发门控 |

反例 #6 强制约束：total dry_run_ratio > 30% 时必须至少跑 1 个 full_test。

### 十维执行模式

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

- **Quick→Full**：Quick 模式下 3 轮内 Δ > 5 分，自动升级 Full（有金矿）
- **Full→Quick**：Full 模式下连续 3 个 skill 稳定 delta < 3，后续降级 Quick（成熟稳定）

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
| 同质多评委 | 主 agent 单次 LLM 评分，不取中位数 | `judge_count=1`，`eval_mode=fallback` |
| 异质评委 | 跳过，不执行 | — |
| 多角色并行审查 | 跳过阶段 0-4，dim10 默认 100 | `eval_mode=fallback` |
| dim8 效果维度 | 无法跑 full_test，降为 dry_run 推演 | `eval_mode=fallback_dry` |
| Phase 3 Step 5 重评 | 主 agent 单次评分，不 spawn 子 agent | `judge_count=1` |

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
7. 检查 diagnostics.tsv 是否存在，不存在则创建并写入表头（模块/维度/分数/文件/行号/详情）
```

### Phase 0.3: 模块诊断

触发五个诊断模块对目标 skill 做静态检测，输出到 diagnostics.tsv：

| 模块 | 检测内容 | 产出维度分 |
|:---|:---|:---|
| SkillOps | 健康巡检：路径可达性、YAML 合法性、引用链完整性 | dim6、dim7 |
| EvoSkill | 失败捕获记录扫描：从 results.tsv 提取历史失败维度 | dim3、dim8 |
| HASP | 规则硬化状态：软规则识别、违规计数 | dim5、dim10 |
| CASCADE | 知识新鲜度：外部引用过时检查 | dim6 |
| Distill | 冗余分析：F_approx 计算、引用密度 | dim6、dim7 |

```
for each skill:
  1. 按模块优先级顺序执行：SkillOps → EvoSkill → HASP → CASCADE → Distill
  2. 每模块产出：维度分 + 文件/行号/详情 → 追加到 diagnostics.tsv
  3. 模块完成后不回写 SKILL.md，仅写入诊断记录
```

🔴 CHECKPOINT：展示诊断摘要（哪些维度有检测数据、哪些空缺），确认后进入 Phase 0.5。

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

展示所有 prompt 给用户，🔴 CHECKPOINT · 🛑 STOP 确认后进入评估。

### Phase 2: 基线评估

```
for each skill:
  1. 读取 diagnostics.tsv，按维度聚合模块分（同维度多模块取中位数）
  2. 模块未覆盖的维度（dim1/dim2/dim4/dim7/dim9）由主 agent 按 Rubric 补充评分
  3. 效果评分：spawn 子 agent 跑 test-prompts
     - with_skill: 带 SKILL.md 执行
     - baseline: 不带 skill 直接执行（裸 prompt）
  4. 加权计算总分，记录到 results.tsv
```

Full 模式额外执行消费者能力基线测试：若 `references/baseline-skill.md` 不存在，则按当前所评估 skill 的核心领域自动生成一份通用基线 skill（含 name/description/workflow/约束规则 等基本结构），保存到该路径。用 baseline-skill 测目标模型裸能力，若 baseline-skill 评分 < 60 则输出能力不足报告并阻断后续优化。此测试独立于 dim8 的 with_skill vs baseline 对比，不要混淆。

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
```

---

## 资源文件

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
| `references/baseline-skill.md` | 消费者能力基线测试参考 skill（首次运行时自动生成） |
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
