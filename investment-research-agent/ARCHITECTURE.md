# Investment Research Agent — 架构设计文档

## 项目概览

一个学习用户个人投研 pattern 的 AI agent，核心价值是：在保持人完全控制投资决策的前提下，自动化数据采集和质量检查，逐步学习并复现用户的研究框架。

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户界面层                          │
│  Topic 输入 → 数据范围勾选 → 逐步审批 → 投资决策       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  工作流引擎                            │
│                                                      │
│  Step 0: 加载 Pattern Memory                         │
│  Step 1: Topic 解析 + 维度推荐                        │
│  Step 2: 数据采集 (带引用)          ←── 人审批        │
│  Step 3: Pattern 引申建议           ←── 人审批        │
│  Step 4: 判断规则应用               ←── 人审批        │
│  Step 5: 汇总输出                                    │
│  Step 6: Pattern 更新               ←── 人审批        │
└──────┬──────────┬──────────┬────────────────────────┘
       │          │          │
┌──────▼───┐ ┌───▼────┐ ┌───▼──────────────┐
│ 数据采集  │ │Pattern │ │    输出引擎       │
│ 模块     │ │Memory  │ │                  │
│          │ │System  │ │ - Markdown 报告   │
│- WebSearch│ │        │ │ - 数据附录       │
│- yfinance│ │- JSON  │ │ - 规则结果       │
│- FRED    │ │  存储   │ │                  │
│- SEC     │ │- 版本   │ └──────────────────┘
│  EDGAR   │ │  追踪   │
│          │ │- 变更   │
│ 每条数据  │ │  日志   │
│ 带引用   │ │        │
└──────────┘ └────────┘
```

---

## 核心模块详解

### 1. Pattern Memory System（最核心）

**文件**: `pattern_memory.json`
**位置**: 用户持久化目录（跨 session 保留）

存储五类 pattern：

| 类型 | 说明 | 例子 |
|------|------|------|
| 研究框架模板 | 不同研究类型的标准维度和顺序 | 看半导体公司：TAM → 竞争 → 单位经济 → 催化剂 |
| 数据筛选偏好 | 时间窗口、来源优先级、指标定义 | 只看 TTM 数据、偏好 SEC filing 而非二手报道 |
| 判断逻辑规则 | if A and B → C 的机械规则 | FCF yield > 8% 且 Debt/EBITDA < 3x → 深入研究 |
| 排除清单 | 明确不要的内容 | 不看技术图表、不做买卖推荐 |
| 工作流偏好 | 审批粒度、输出格式、语言 | 逐维度审批、中文分析+英文引用 |

**关键设计原则**：
- Pattern memory 的任何修改都需要用户显式审批
- 低置信度的 pattern（仅观察到一次）标记为 "tentative"
- 保留完整变更日志，可回溯

### 2. 数据采集模块

**零幻觉机制**：
- 每条数据强制附带 `[Source: 名称, URL, 访问日期]`
- 无法找到可靠来源的数据标记为 `[UNVERIFIED]`
- 数据冲突时呈现双方来源，由人判断
- 计算型指标注明公式和数据来源

**数据来源优先级**:
1. SEC EDGAR（一手财务数据）
2. 公司 IR 页面（官方披露）
3. Yahoo Finance / FRED（结构化数据 API）
4. 主流财经媒体（新闻、分析师评论）
5. 行业报告（第三方研究）

**脚本**:
- `scripts/fetch_financial_data.py` — 通过 yfinance 获取股票财务数据
- WebSearch 工具 — 新闻、报告、公告搜索
- FRED API — 宏观经济数据

### 3. 工作流引擎

每一步都是 **提案 → 审批** 模式：

```
Agent 提案                    用户决策
──────────                    ────────
"建议查这5个维度"      →      "去掉第3个，加上X"
"市场规模数据如下"      →      "数据可用 / 需要补充Y"
"建议还可以看Z方向"    →      "好的查一下 / 不需要"
"规则判断结果如下"      →      "同意 / 调整规则"
"学到了这些新pattern"  →      "保存 / 修改 / 不保存"
```

### 4. Phase 2 — 他人使用你的 Pattern

当别人加载你的 pattern memory 时：
- 展示你的研究框架作为引导式清单
- 每个维度/规则会解释 **为什么** 这样做（来自 pattern memory 的 notes）
- 允许偏离但会标记偏离点
- **不会**根据其他人的操作修改你的 pattern memory

---

## 文件结构

```
investment-research-agent/
├── SKILL.md                          # 主 skill 指令（agent 行为定义）
├── ARCHITECTURE.md                   # 本文档
├── references/
│   └── pattern_schema.md             # Pattern Memory 的 JSON Schema
├── scripts/
│   ├── init_pattern_memory.py        # 初始化空的 pattern memory
│   ├── update_pattern_memory.py      # 应用 pattern 变更（带预览和备份）
│   ├── fetch_financial_data.py       # 金融数据获取（yfinance + FRED）
│   └── export_research.py           # 导出研究报告为 Markdown
└── assets/                           # 模板等资源（预留）
```

---

## 使用流程

### 首次使用

1. 运行 `init_pattern_memory.py` 创建空的 pattern memory
2. 告诉 agent 一个投资 topic
3. 正常做研究 — agent 帮你查数据，你审批每一步
4. 结束时 agent 总结学到的 pattern，你确认保存

### 日常使用

1. 输入新 topic
2. Agent 根据已有 pattern 自动推荐研究维度
3. 数据采集和审批流程同上
4. Pattern 持续迭代优化

### 让他人使用

1. 分享你的 `pattern_memory.json`
2. 他人输入 topic 后看到你的研究框架
3. 按照你的标准查资料、应用规则
4. 他们的使用不会改变你的 pattern

---

## 技术依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| yfinance | 股票财务数据 | `pip install yfinance` |
| WebSearch | 新闻和网页搜索 | Cowork 内置工具 |
| WebFetch | 网页内容获取 | Cowork 内置工具 |
| Python 3.8+ | 脚本运行环境 | 系统自带 |

可选：
| fredapi | FRED 宏观数据 | `pip install fredapi`（需要 API key）|

---

## 安全和合规

- Agent **永远不会**做出投资建议（买/卖/持有）
- 所有数据来自公开来源
- Pattern memory 存储在用户本地，不上传
- 用户对所有结论和数据使用有最终决定权
