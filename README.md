# 鲁班.Skill（luban-skill）

工业级 AI Agent Skill 优化器。对 skill 进行 9 维度结构评分 + 效果验证，通过棘轮机制保留改进、回滚退步，输出可量化的优化日志。

## 核心特性

- **9 维 Rubric**：覆盖 frontmatter / 工作流 / 失败模式 / 检查点 / 具体性 / 资源 / 架构 / 实测 / 反例
- **棘轮机制**：只保留改进，自动回滚退步，`results.tsv` 全量记录
- **独立评分**：效果维度用子 agent 独立打分，消除「自己改自己评」的偏差
- **人在回路**：每个 skill 优化完暂停，用户确认再继续

## 六模块架构

| 模块 | 功能 | 论文 |
|------|------|------|
| Darwin | 9 维评分 + Phase 0-3 优化循环 | SkillLens |
| EvoSkill | 失败驱动的缺口发现与自动修补 | arXiv 2603.02766 |
| SkillOps | 五维健康诊断 + 定期巡检 | arXiv 2605.13716 |
| CASCADE | 持续学习 + 自我反思驱动知识更新 | arXiv 2512.23880 |
| Skill Distill | 指标自由度 F 驱动的精简决策 | arXiv 2604.01608 |
| HASP | 建议规则升格为可执行程序函数 | arXiv 2605.17734 |
| MUSE-Autoskill | 编辑后自动回归测试 | arXiv 2605.27366 |

## 安装

将本目录放入 Agent 的 skills 加载路径即可。

## 使用方式

```
优化所有skills        → Darwin 核心引擎（全量）
优化 <skill名>        → 对指定 skill 执行 Phase 1-4
评估所有skills        → 只执行 Phase 0.5-1，不进入优化循环
检查技能健康          → SkillOps 巡检
这个技能有问题        → EvoSkill 失败修补
更新技能知识          → CASCADE 知识更新
精简技能              → Skill Distill
规则硬化              → HASP 规则硬化
看看优化历史          → 读取 results.tsv
```

## 已知限制

1. **Quick/Full 模式选定后不会自动切换**：双轨反馈依赖跨会话状态追踪，当前无法实现。运行时 agent 按前置网关选一次模式，执行到底。
2. **Full 模式依赖 git**：git 不可用时降级为 `.bak` 文件备份。多评委评分依赖 `dispatch_task` 可用。
3. **确定性维度（dim1/4/6/7/9）由 agent 按 Rubric 逐条自检**，非系统内置工具。评分一致性依赖 agent 对 rubric 的理解准确度。

## 调度策略

| 类型 | 触发 |
|------|------|
| 事件驱动（立即） | 用户反馈技能错误 → EvoSkill / 技能编辑完成 → MUSE / 规则重复忽略 → HASP |
| 按需触发 | 用户指令（优化/体检/更新/精简/硬化）→ 对应模块 |
| 定时扫描 | 每周 SkillOps / 每月 Distill / 每季度 CASCADE |

## 目录结构

```
luban-skill/
├── SKILL.md                     # 主文件（本 skill 的定义和指令）
├── README.md                    # 项目概览
├── QUICKSTART.md                # 快速上手指南
├── scripts/
│   ├── skillops_scanner.py      # SkillOps 工具化扫描
│   ├── distill_analyzer.py      # Distill 引用矩阵构建与 F_approx 计算
│   ├── muse_generator.py        # MUSE 测试用例自动生成
│   ├── evo_skill_patcher.py     # EvoSkill 失败驱动缺口分析与补丁生成
│   ├── cascade_updater.py       # CASCADE 外部引用过时检测与更新建议
│   └── hasp_hardener.py         # HASP 软规则违规检测与硬化建议
└── references/
    └── SA-DM.md                 # SkillOps 设计方法论论文
```

## 学术依据

- EvoSkill (arXiv 2603.02766) — 失败驱动的技能缺口发现与自动修补
- SkillOps (arXiv 2605.13716) — 技能库运维框架，五维健康诊断
- CASCADE (arXiv 2512.23880) — 持续学习 + 自我反思驱动的技能进化
- Skill Distill (arXiv 2604.01608) — 指标自由度 F 驱动的精简决策
- HASP (arXiv 2605.17734) — 技能升格为可执行程序函数
- MUSE-Autoskill (arXiv 2605.27366) — 全生命周期管理 + 回归测试
- SkillLens (arXiv 2605.23899) — 9 维 rubric 实证来源
- SkillOpt (arXiv 2605.23904) — validation-gated edits 形式化框架
