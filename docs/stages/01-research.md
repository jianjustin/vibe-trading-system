# 阶段 1：研究（Research）— 宏观快照

## 功能说明

获取宏观市场指标，判定市场立场（进攻 / 谨慎 / 防守），生成 `MacroSnapshot` 产物。

- **数据来源：** yfinance（`^TNX` 10 年期国债、`^VIX`、`DX-Y.NYB` 美元指数、`SPY`、`QQQ`、`HYG`）
- **实现：** `src/vts/stages/research.py`（`ResearchStage`）+ `src/vts/loaders/yfinance_loader.py`
- **输入：** 无（实时拉取行情）
- **输出产物：** `artifacts/snapshots/{YYYY-MM-DD}.json`

## 立场判定规则

| 条件 | 立场 |
|------|------|
| VIX > 25，或 SPY 同时跌破 50 日和 200 日均线 | 防守 |
| VIX < 18 且 SPY、QQQ 均在 50 日均线之上 | 进攻 |
| 其他情况 | 谨慎 |

## 操作步骤

```bash
vts research
```

预期输出：

```
MacroSnapshot saved: 2026-06-10
  Stance: 谨慎
  VIX: 18.5
  10Y Treasury: 4.28
```

## 自动化测试

```bash
pytest tests/test_research.py tests/test_loader.py -v
```

预期：`test_research.py` 4 个测试通过（快照生成 + 三种立场判定），`test_loader.py` 5 个测试通过（OHLCV 列规范化、空数据报错、均线状态、宏观指标）。测试全部使用 mock，不发起真实网络请求。

## 手动验证

1. 运行 `vts research`，确认命令成功且输出立场、VIX、国债收益率。
2. 检查产物文件存在且字段完整：

   ```bash
   cat artifacts/snapshots/$(date +%F).json | python3 -m json.tool
   ```

   验证点：
   - `date` 为今天日期
   - `stance` 为 进攻/谨慎/防守 之一
   - `vix`、`treasury_10y`、`dxy` 为合理数值（VIX 通常 10–40，10Y 通常 3–6）
   - `spy_above_50d` 等均线字段为 true/false
3. 对照判定规则人工核对：如当前 VIX < 18 且 SPY/QQQ 在 50 日均线上方，立场应为「进攻」。
4. 重复运行 `vts research`，确认同日产物被幂等覆盖（不会产生重复文件）。

## 常见问题

- **网络失败 / yfinance 限流：** 个别指标返回 None 不会让阶段失败，对应字段为 null；立场判定会基于可用指标降级。
- **非交易时段：** 数据为最近一个交易日收盘值，属正常现象。
