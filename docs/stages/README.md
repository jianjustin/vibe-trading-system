# 五阶段管道操作手册

本目录为每个管道阶段提供独立的操作步骤文档，覆盖：功能说明、CLI 操作、自动化测试、手动验证。

实施方案见 [../plans/2026-06-09-five-stage-pipeline.md](../plans/2026-06-09-five-stage-pipeline.md)。

## 管道总览

```
研究 (research) → 发现 (discover) → 回测 (backtest) → 观点 (viewpoint) → 计划 (plan + review)
     │                 │                  │                  │                   │
MacroSnapshot     ResearchBrief     BacktestReport       Viewpoint        ExecutionPlan
artifacts/        artifacts/        artifacts/           artifacts/       artifacts/
snapshots/        briefs/           reports/             viewpoints/      plans/
```

阶段之间仅通过产物（`artifacts/` 目录下的 JSON 文件）通信，每个阶段可独立运行和测试。

## 文档索引

| 文档 | 阶段 | CLI 命令 | API 端点 |
|------|------|----------|----------|
| [01-research.md](01-research.md) | 研究：宏观快照 | `vts research` | `POST /api/stages/research/run` |
| [02-discover.md](02-discover.md) | 发现：研究简报 | `vts discover TICKER` | `POST /api/stages/discover/run` |
| [03-backtest.md](03-backtest.md) | 回测：历史验证 | （Python API / 仪表盘） | `POST /api/stages/backtest/run` |
| [04-viewpoint.md](04-viewpoint.md) | 观点：综合判断 | `vts viewpoint TICKER` | `POST /api/stages/viewpoint/run` |
| [05-plan.md](05-plan.md) | 计划：执行计划 + 人工审批 | `vts plan` / `vts review` | `POST /api/stages/plan/run` / `POST /api/plans/{id}/review` |
| [06-earnings-data.md](06-earnings-data.md) | 财报数据工具（迁移自 earnings-agent） | `vts earnings fetch` / `vts earnings scan` | — |

## 环境准备（所有阶段通用）

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system

# 创建虚拟环境（已有 .venv 可跳过）
python3 -m venv .venv
source .venv/bin/activate

# 安装项目及开发依赖
pip install -e ".[dev]"

# 验证 CLI 可用
vts --help
```

## 全量自动化测试

```bash
pytest -v
```

预期：全部测试通过（73 个），覆盖产物存储、数据加载器、五个阶段、回测引擎、信号规则、管道编排器、REST API 和财报数据工具。

## 全链路手动验证（端到端）

### 方式一：通过仪表盘（推荐）

```bash
# 构建前端（首次）
cd frontend && npm install && npm run build && cd ..

# 启动服务
vts serve
# 打开 http://127.0.0.1:8000
```

在仪表盘中按顺序操作：

1. **Research** — 点击「抓取宏观快照」，右侧产物面板出现 MacroSnapshot
2. **Discover** — 填写 Ticker、投资论点、证据、失效条件，点击「生成研究简报」
3. **Backtest** — 填写 Ticker，选择信号规则（如 20/60 均线交叉），点击「运行回测」
4. **Viewpoint** — 填写 Ticker，点击「生成观点」
5. **Plan** — 填写 Ticker，点击「生成执行计划」
6. 右侧产物面板切换至「执行计划」tab，点击「批准」/「拒绝」/「需修改」完成审批

每一步执行后，顶部状态栏和产物面板自动刷新。

### 方式二：通过 CLI

```bash
# 1. 研究：生成今日宏观快照（真实调用 yfinance）
vts research

# 2. 发现：创建研究简报
vts discover TSLA \
  --thesis "电动车龙头，交付动能强劲" \
  --evidence "Q1 交付超预期,毛利率扩张,FSD 收入浮现" \
  --invalidation "交付连续两个季度不及预期" \
  --next-action "回测 setup"

# 3. 回测：通过 API 调用（信号规则已预定义）
curl -X POST http://127.0.0.1:8000/api/stages/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"TSLA","rule":"ma_cross_20_60"}'

# 4. 观点：综合宏观 + 简报 + 回测
vts viewpoint TSLA

# 5. 计划：生成执行计划并审批
vts plan TSLA
vts review TSLA approve --notes "确认入场条件"

# 6. 查看整体状态
vts status
```

### 方式三：纯 API

```bash
# 查看可用信号规则
curl http://127.0.0.1:8000/api/backtest/rules

# 查看系统状态
curl http://127.0.0.1:8000/api/status

# 浏览某类产物
curl http://127.0.0.1:8000/api/artifacts/viewpoints
```

每一步成功后可在 `artifacts/` 对应子目录中找到 JSON 产物。`vts status` 应显示各类产物计数 ≥ 1。
