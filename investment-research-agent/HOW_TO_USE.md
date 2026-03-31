# Investment Research Agent — 使用指南

---

## 整体概念：你在用什么

这个 agent 本质上是一套 **Cowork Skill**（Claude 的行为指令集）+ **配套脚本**。

它不是一个独立应用，而是让 Claude 在 Cowork 对话中"变成"你的投研助手。你给它一个投资 topic，它按照学到的你的研究习惯帮你查数据、组织信息、应用你的判断规则——每一步都等你点头。

---

## 文件清单和各自作用

```
investment-research-agent/
│
├── SKILL.md                          ← 核心：Claude 的行为指令
│   定义了 agent 的完整工作流程：
│   - 怎么理解你的 topic
│   - 怎么推荐研究维度
│   - 怎么查数据、标引用
│   - 怎么应用你的规则
│   - 怎么更新 pattern memory
│
├── ARCHITECTURE.md                   ← 参考：系统架构设计文档
│   整体架构说明，帮你理解系统怎么运作。
│   不直接被 Claude 使用，是给你看的。
│
├── references/
│   └── pattern_schema.md             ← 参考：Pattern Memory 的数据结构定义
│       详细描述了 pattern_memory.json 的 JSON 格式。
│       Claude 在创建和更新 pattern memory 时会参考这个文件。
│
├── scripts/
│   ├── init_pattern_memory.py        ← 脚本：初始化 pattern memory
│   ├── update_pattern_memory.py      ← 脚本：更新 pattern memory（带备份）
│   ├── fetch_financial_data.py       ← 脚本：从 Yahoo Finance 抓取财务数据
│   └── export_research.py            ← 脚本：把研究结果导出为 Markdown 报告
│
└── assets/                           ← 预留：模板等资源
```

---

## 两种使用方式

### 方式一：在当前 Cowork 对话中直接用（最简单）

**你不需要安装任何东西。** 因为 SKILL.md 已经在你的工作目录里了，你可以直接在当前对话（或新对话）里说：

> "按照 investment-research-agent/SKILL.md 的流程，帮我研究 [你的 topic]"

Claude 会：
1. 读取 SKILL.md 了解自己该怎么做
2. 检查有没有 pattern_memory.json，没有就帮你创建
3. 开始走六步工作流

**优点**：零配置，立刻能用
**缺点**：每次新对话都要手动提一下 SKILL.md

### 方式二：打包成 Cowork Plugin（推荐长期使用）

可以把这套 skill 打包成一个 `.plugin` 文件安装到 Cowork。安装后，以后你只要说"帮我研究 NVIDIA"之类的话，Claude 会自动触发这个 skill，不需要你手动指向文件。

我可以帮你打包，你只需要说"帮我打包成插件"。

---

## 实际使用流程（Step by Step）

### 第一次使用

**Step 1：初始化 Pattern Memory**

你告诉我一个投资 topic，我会先创建一个空的 `pattern_memory.json`。这是你的"研究大脑"，随着使用会越来越了解你。

**Step 2：输入 Topic + 选维度**

你说比如"我想研究东南亚电动车供应链"，我会列出建议的研究维度：

```
建议研究维度：
☑ 市场规模 & TAM
☑ 主要玩家/竞争格局
☑ 供应链上下游结构
☑ 政策支持/补贴
☑ 关键财务指标
☐ 技术路线对比
☐ ESG 相关风险

要增减哪些？
```

你勾选、增删、确认后我才开始查。

**Step 3：数据采集**

我逐个维度搜集数据，每条数据都标注来源。比如：

```
## 市场规模 & TAM

- 东南亚 EV 市场 2025 年销量约 50 万辆，同比增长 42%
  [Source: Counterpoint Research, https://..., accessed 2026-03-29]

- 泰国占东南亚 EV 销量 60%+，主要由政策补贴驱动
  [Source: Bangkok Post, https://..., accessed 2026-03-29]

数据质量：✅ 完整 | 2025 年全年数据 | 来源可靠
```

搜完一个维度我会暂停，等你确认"数据可用"或"需要补充 X"。

**Step 4：Pattern 引申**

基于已有数据，我会建议额外方向：

```
建议额外探索：
1. 🔍 电池原材料（镍、锂）在东南亚的供应
   原因：你选了供应链维度，上游材料是关键变量
2. 🔍 中国车企在东南亚的工厂布局
   原因：竞争格局的具体落地数据

要查哪个？(1/2/全部/不需要)
```

**Step 5：规则判断**

如果你之前教过我判断规则（比如"市场年增速 > 30% → 值得深入"），我会自动应用：

```
✅ 规则: "市场年增速 > 30% → 值得深入"
   结果: 增速 42% — 满足条件
   [来源: 上述 Counterpoint 数据]
```

第一次用的时候你还没有规则，我会问你"看到这些数据，你通常怎么判断？"来学习你的规则。

**Step 6：Pattern 保存**

结束时我会告诉你这次学到了什么：

```
📝 这次学到的 pattern：
- 新增研究框架："东南亚/新兴市场"模板，维度包含政策分析
- 新增规则："市场年增速 > 30% → 深入研究"
- 偏好记录：你更信任 Counterpoint 而非一般新闻来源

保存？(是/否/修改)
```

### 第二次及以后

下次你说"帮我研究印度光伏产业"，我会：
- 自动加载你的 pattern memory
- 基于你之前的"新兴市场研究"框架推荐维度（而不是从零开始）
- 按你偏好的来源优先级查数据
- 应用你建立的规则

**你需要做的 prompt 调节会越来越少。**

### 让别人用你的 Pattern

把 `pattern_memory.json` 文件分享给别人。他们在自己的 Cowork 里加载后，会看到你的研究框架作为引导清单。他们的操作不会修改你的 pattern。

---

## 四个脚本的具体用法

### 1. init_pattern_memory.py — 初始化

```bash
python scripts/init_pattern_memory.py ./pattern_memory.json --owner Sharon
```

创建一个空白的 pattern memory 文件。只需要运行一次。

### 2. update_pattern_memory.py — 更新 Pattern

```bash
# 预览变更（不实际保存）
python scripts/update_pattern_memory.py ./pattern_memory.json ./changes.json --dry-run

# 实际保存（会自动备份旧文件为 .bak）
python scripts/update_pattern_memory.py ./pattern_memory.json ./changes.json
```

输入是一个描述变更的 JSON 文件（Claude 在每次研究结束时会自动生成）。支持的变更类型：增加维度、增加规则、修改规则、停用规则、更新研究顺序、增加排除项、更新偏好、增删数据源。

### 3. fetch_financial_data.py — 抓取金融数据

```bash
# 公司概况
python scripts/fetch_financial_data.py --ticker NVDA --type profile

# 财务报表（利润表、资产负债表、现金流）
python scripts/fetch_financial_data.py --ticker NVDA --type financials

# 关键指标（估值、盈利能力、增长、杠杆）
python scripts/fetch_financial_data.py --ticker NVDA --type metrics

# 分析师预期
python scripts/fetch_financial_data.py --ticker NVDA --type estimates

# 全部数据
python scripts/fetch_financial_data.py --ticker NVDA --type all

# FRED 宏观数据（需要 FRED_API_KEY 环境变量）
python scripts/fetch_financial_data.py --fred-series GDP --start 2020-01-01

# 输出到文件
python scripts/fetch_financial_data.py --ticker NVDA --type all --output nvda_data.json
```

需要先安装 yfinance：`pip install yfinance`

所有输出自带 citation 信息（source name、URL、访问日期）。

### 4. export_research.py — 导出研究报告

```bash
python scripts/export_research.py ./session_data.json ./output_report.md
```

把一次完整的研究 session 导出为格式化的 Markdown 文档，包含所有数据引用、质量评估、规则应用结果和未解决问题。

---

## 关键设计原则（为什么这么做）

**为什么每一步都要人审批？**
投资决策的数据质量至关重要。Agent 可能搜到过时的、不准确的、或者对你的分析场景不适用的数据。你比 agent 更清楚哪些数据"能用"。

**为什么要记 pattern？**
你的投研经验本质上是一套隐性知识：看什么、不看什么、怎么判断。Pattern memory 把这些显性化、可复用。用得越多，agent 越了解你，你需要手动调的越少。

**为什么不直接给投资建议？**
Agent 的价值是帮你更快地拿到高质量数据和机械化地应用你的规则。投资判断涉及太多 agent 无法掌握的上下文（你的组合、风险偏好、市场情绪感知等）。这是你的工作，agent 只是加速器。

**为什么每条数据都要引用？**
零幻觉是底线。在投资场景中，一个错误的数字可能导致完全相反的结论。强制引用确保你可以验证任何一条数据。
