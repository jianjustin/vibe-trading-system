# 阶段 2：发现（Discover）— 研究简报

## 功能说明

将结构化的研究输入沉淀为 `ResearchBrief` 产物，强制约束研究质量（必填论点与失效条件、证据最多 3 条）。

- **实现：** `src/vts/stages/discover.py`（`DiscoverStage`）
- **输入：** 人工提供的 ticker、论点、证据、失效条件、下一步行动
- **输出产物：** `artifacts/briefs/{TICKER}.json`

## 校验规则

| 规则 | 行为 |
|------|------|
| `ticker` 为空 | 报错 `ValueError: ticker is required` |
| `thesis` 为空 | 报错 `ValueError: thesis is required` |
| 证据超过 3 条 | 自动截断为前 3 条 |
| `next_action` 非法值 | 回退为「继续研究」 |

`next_action` 合法值：`继续研究` / `决策挑战` / `回测 setup` / `放弃`

## 操作步骤

```bash
vts discover TSLA.US \
  --thesis "电动车龙头，交付动能强劲" \
  --evidence "Q1 交付超预期,毛利率扩张,FSD 收入浮现" \
  --invalidation "交付连续两个季度不及预期" \
  --next-action "回测 setup"
```

预期输出：

```
ResearchBrief saved: TSLA.US
```

不带选项直接运行 `vts discover TSLA.US` 时，CLI 会交互式提示输入 thesis、evidence、invalidation。

## 自动化测试

```bash
pytest tests/test_discover.py -v
```

预期：4 个测试通过（保存简报、证据截断、ticker 必填、thesis 必填）。

## 手动验证

1. 运行上述命令，检查产物：

   ```bash
   cat artifacts/briefs/TSLA.US.json | python3 -m json.tool
   ```

   验证点：
   - `ticker`、`thesis`、`invalidation` 与输入一致
   - `key_evidence` 数组长度 ≤ 3
   - `next_action` 为「回测 setup」
2. 验证证据截断：传入 5 条逗号分隔的证据，确认产物中只保留前 3 条。
3. 验证必填校验：`--thesis ""` 应报错且不生成产物。
4. 重复运行同一 ticker，确认产物被覆盖更新（以最新一次输入为准）。
