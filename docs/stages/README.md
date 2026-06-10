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

| 文档 | 阶段 | CLI 命令 |
|------|------|----------|
| [01-research.md](01-research.md) | 研究：宏观快照 | `vts research` |
| [02-discover.md](02-discover.md) | 发现：研究简报 | `vts discover TICKER` |
| [03-backtest.md](03-backtest.md) | 回测：历史验证 | （Python API） |
| [04-viewpoint.md](04-viewpoint.md) | 观点：综合判断 | `vts viewpoint TICKER` |
| [05-plan.md](05-plan.md) | 计划：执行计划 + 人工审批 | `vts plan` / `vts review` |
| [06-earnings-data.md](06-earnings-data.md) | 财报数据工具（迁移自 earnings-agent） | `vts earnings fetch` / `vts earnings scan` |

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

预期：全部测试通过（53 个），覆盖产物存储、数据加载器、五个阶段、回测引擎、管道编排器和财报数据工具。

## 全链路手动验证（端到端）

按顺序执行以下命令，走通一条完整的管道：

```bash
# 1. 研究：生成今日宏观快照（真实调用 yfinance）
vts research

# 2. 发现：创建研究简报
vts discover TSLA.US \
  --thesis "电动车龙头，交付动能强劲" \
  --evidence "Q1 交付超预期,毛利率扩张,FSD 收入浮现" \
  --invalidation "交付连续两个季度不及预期" \
  --next-action "回测 setup"

# 3. 回测：见 03-backtest.md（通过 Python API 运行）

# 4. 观点：综合宏观 + 简报 + 回测
vts viewpoint TSLA.US

# 5. 计划：生成执行计划并审批
vts plan TSLA.US
vts review TSLA.US approve --notes "确认入场条件"

# 6. 查看整体状态
vts status
```

每一步成功后可在 `artifacts/` 对应子目录中找到 JSON 产物。`vts status` 应显示各类产物计数 ≥ 1。
