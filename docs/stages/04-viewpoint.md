# 阶段 4：观点（Viewpoint）— 综合判断

## 功能说明

把上游三类产物（最新 `MacroSnapshot` + 该标的的 `ResearchBrief` + 匹配的 `BacktestReport`）按规则综合为 `Viewpoint`：方向（看多 / 中性 / 看空）、置信度（高 / 中 / 低）、反方论点。

- **实现：** `src/vts/stages/viewpoint.py`（`ViewpointStage`）
- **输入依赖：**
  - `artifacts/briefs/{TICKER}.json` —— **必须存在**，缺失时报 `FileNotFoundError`
  - `artifacts/snapshots/` 最新一份 —— 可选（缺失时按「无宏观数据」处理）
  - `artifacts/reports/` 中以 ticker 开头的最新报告 —— 可选
- **输出产物：** `artifacts/viewpoints/{TICKER}.json`

## 综合规则

**方向：**

| 条件 | 方向 |
|------|------|
| 回测结论为「放弃」 | 看空 |
| 宏观立场为「防守」 | 中性 |
| 回测结论为「小仓位验证」或「模拟观察」 | 看多 |
| 其他（含无回测报告） | 中性 |

**置信度：**

| 条件 | 置信度 |
|------|--------|
| 无回测报告或样本数 < 10 | 低 |
| 胜率 > 55% 且盈亏比 > 1.5 且宏观非防守 | 高 |
| 胜率 > 45% | 中 |
| 其他 | 低 |

**反方论点：** 自动汇总简报中的失效条件；宏观防守时额外附加风险提示；两者皆无时给出「历史数据有限」的兜底论点（保证至少 1 条）。

## 操作步骤

前置：已完成阶段 1（research）、阶段 2（discover），建议完成阶段 3（backtest）。

```bash
vts viewpoint TSLA.US
```

预期输出：

```
Viewpoint saved: TSLA.US
  Direction: 看多
  Confidence: 中
  Counter-arguments: 1
```

## 自动化测试

```bash
pytest tests/test_viewpoint.py -v
```

预期：4 个测试通过（综合生成、好回测 + 进攻宏观 → 看多、坏回测 → 看空、缺简报报错）。

## 手动验证

1. 检查产物：

   ```bash
   cat artifacts/viewpoints/TSLA.US.json | python3 -m json.tool
   ```

   验证点：
   - `direction` / `confidence` 与上方规则表自洽（对照当前快照立场和回测报告结论手工核对）
   - `core_logic` 包含简报论点和回测结论
   - `supporting_evidence` 为简报中证据的分号拼接
   - `counter_arguments` 至少 1 条，且包含简报中的失效条件
2. 依赖缺失验证：对一个没有简报的 ticker 运行 `vts viewpoint FAKE.US`，应报错（FileNotFoundError），不生成产物。
3. 规则验证（可选）：手工把最新快照 JSON 的 `stance` 改为「防守」，重新运行，确认方向变为「中性」且反方论点中出现宏观防守提示；验证后恢复快照。
