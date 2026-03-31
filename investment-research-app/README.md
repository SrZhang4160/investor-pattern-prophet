# 📊 投研助手 — Investment Research Agent

一个学习你个人投研 pattern 的 AI 助手网页应用。

## 核心功能

- **一人训练，多人使用**：训练者做研究时 agent 学习你的 pattern；别人导入后按你的框架做研究
- **每条数据带引用**：零幻觉，所有数据来自公开来源并标注出处
- **逐步审批**：每一步等你确认，你完全掌控数据质量和研究方向
- **Pattern 可导出**：JSON 文件，跨设备跨人员共享

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置 API Key（可选但推荐）

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

没有 Claude API Key 也能用——只是 AI 分析、维度建议、规则判断等功能不可用，
你仍然可以使用 Yahoo Finance 数据拉取和手动研究流程。

### 3. 启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 使用流程

### 训练者（Pattern 所有者）

1. 选择「🎓 训练者」身份，输入密码（默认 `admin`，可通过环境变量 `TRAINER_PASSWORD` 修改）
2. 输入投资 topic → 选择研究类型 → 勾选维度
3. 逐维度审核数据 → 确认数据质量
4. 查看 AI 引申建议 → 决定是否追加维度
5. 应用/添加判断规则
6. 生成研究总结
7. 确认保存 Pattern 更新

每做一次研究，pattern 变得更精准。

### 使用者（跟随 Pattern）

1. 选择「👤 使用者」身份
2. 导入训练者的 `pattern_memory.json`（左侧面板）
3. 输入 topic → 看到训练者的研究框架作为维度推荐
4. 跟随相同的研究流程
5. 使用者的操作**不会修改**原始 pattern

### 跨设备 / 分享

- **导出**：左侧面板 → 📤 导出 Pattern → 得到 JSON 文件
- **导入**：左侧面板 → 📥 导入 Pattern → 选择 JSON 文件
- 支持「合并模式」：保留自己的 pattern，添加新的维度和规则

## 配置

| 环境变量 | 用途 | 默认值 |
|----------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | 无（AI 功能不可用） |
| `TRAINER_PASSWORD` | 训练者登录密码 | `admin` |
| `PATTERN_MEMORY_PATH` | pattern 文件路径 | `pattern_memory.json` |

## 部署给多人使用

### 方式 A：本地运行，分享 Pattern 文件

每人自己 `pip install + streamlit run`，通过文件共享 pattern。

### 方式 B：部署到 Streamlit Cloud（免费）

1. 把代码推到 GitHub
2. 去 [share.streamlit.io](https://share.streamlit.io) 部署
3. 在 Streamlit Cloud 的 Secrets 里设置 `ANTHROPIC_API_KEY` 和 `TRAINER_PASSWORD`
4. 所有人通过浏览器访问

### 方式 C：部署到任何服务器

```bash
# Docker
docker build -t investment-research .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=xxx investment-research
```

## 技术栈

- **前端**：Streamlit（Python 原生 Web 框架）
- **数据源**：Yahoo Finance (yfinance)、WebSearch
- **AI 分析**：Anthropic Claude API
- **存储**：本地 JSON 文件（pattern_memory.json）

## 注意事项

- 本应用**不会**给出投资建议（买/卖/持有）
- 所有数据来自公开渠道
- Pattern 数据存储在本地
- 投资决策完全由你自己做出
