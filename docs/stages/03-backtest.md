# 阶段 3：回测（Backtest）— 历史验证

## 功能说明

对给定的交易信号函数在历史数据上做逐 K 线回测，计算胜率、盈亏比、最大回撤，并自动给出结论，生成 `BacktestReport` 产物。

- **实现：**
  - `src/vts/backtest/engine.py`（`SimpleEquityEngine`，仅做多、含滑点的逐 K 线引擎）
  - `src/vts/backtest/metrics.py`（`calc_metrics`：胜率 / 盈亏比 / 最大回撤）
  - `src/vts/stages/backtest.py`（`BacktestStage`）
- **输入：** ticker、规则名、信号函数（`DataFrame → Series`，1=买入 / -1=卖出 / 0=持有）、时间范围
- **输出产物：** `artifacts/reports/{TICKER}-{rule_name}.json`

> **注意：** 回测阶段需要传入 Python 信号函数，无法通过 CLI 直接表达，因此**没有对应的 CLI 子命令**，通过 Python API 运行。

## 自动结论规则

| 条件 | 结论 |
|------|------|
| 样本数 < 10 | 样本不足，不下结论 |
| 胜率 < 40% 且盈亏比 < 1.0 | 放弃 |
| 胜率 > 55% 且盈亏比 > 1.5 | 小仓位验证 |
| 胜率 > 45% | 模拟观察 |
| 其他 | 修改 |

## 操作步骤（Python API）

在仓库根目录创建脚本或直接在 REPL 中运行（真实拉取 yfinance 数据）：

```python
# run_backtest_example.py
import pandas as pd

from vts.artifacts.store import ArtifactStore
from vts.stages.backtest import BacktestStage


def ma_cross_signal(data: pd.DataFrame) -> pd.Series:
    """示例信号：收盘价上穿 20 日均线买入，下穿卖出。"""
    ma20 = data["close"].rolling(20).mean()
    above = data["close"] > ma20
    signals = pd.Series(0, index=data.index)
    signals[above & ~above.shift(1, fill_value=False)] = 1
    signals[~above & above.shift(1, fill_value=False)] = -1
    return signals


store = ArtifactStore("artifacts")
stage = BacktestStage(store)
artifact_id = stage.run(
    ticker="TSLA",
    rule_name="ma20_cross",
    signal_fn=ma_cross_signal,
    start_date="2022-01-01",
    end_date="2026-01-01",
    entry_rule="收盘价上穿 20 日均线",
    exit_rule="收盘价下穿 20 日均线",
)
print(f"BacktestReport saved: {artifact_id}")
```

```bash
.venv/bin/python run_backtest_example.py
```

## 自动化测试

```bash
pytest tests/test_engine.py tests/test_backtest.py -v
```

预期：6 个测试通过——

- `test_engine.py`（4 个）：单笔买卖配对、无信号无交易、多笔交易、指标计算（5 笔交易胜率 0.6）
- `test_backtest.py`（2 个）：报告生成（含样本数 / 胜率）、无交易时样本数为 0

测试使用 mock 数据，不发起真实网络请求。

## 手动验证

1. 运行上面的示例脚本，检查产物：

   ```bash
   cat artifacts/reports/TSLA-ma20_cross.json | python3 -m json.tool
   ```

   验证点：
   - `sample_count` > 0（4 年日线 + 均线交叉策略通常有数十笔交易）
   - `win_rate` 在 0–1 之间，`max_drawdown` ≥ 0
   - `conclusion` 与上方结论规则表自洽（用 `win_rate`、`profit_loss_ratio` 手工对照）
   - `time_range` 为 "2022-01-01 to 2026-01-01"
2. 边界验证：把 `signal_fn` 改为恒为 0 的函数，确认 `sample_count == 0` 且结论为「样本不足，不下结论」。
3. 引擎正确性抽查：信号在第 5 天买入、第 50 天卖出时，产物中交易的进出场日期应与之对应（参考 `tests/test_engine.py::test_engine_buy_and_hold`）。
