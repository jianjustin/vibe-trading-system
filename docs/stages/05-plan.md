# 阶段 5：计划（Plan）— 执行计划与人工审批

## 功能说明

从 `Viewpoint` 生成 `ExecutionPlan`（方向、仓位、入场条件、前置条件），并提供人工审批门：批准 / 拒绝 / 修改。**这是管道中唯一带人工决策门的阶段**——计划生成后处于 `pending_review` 状态，必须人工审批。

- **实现：** `src/vts/stages/plan.py`（`PlanStage.generate()` + `PlanStage.review()`）
- **输入依赖：** `artifacts/viewpoints/{TICKER}.json`（必须存在）
- **输出产物：** `artifacts/plans/{TICKER}.json`

## 生成门槛（风控规则）

| 观点状态 | 行为 |
|----------|------|
| 方向为「中性」 | 拒绝生成（`Cannot generate plan for neutral viewpoint`） |
| 置信度为「低」 | 拒绝生成（`confidence too low`） |
| 看多 / 看空 且置信度 中 / 高 | 生成计划，状态 `pending_review` |

## 操作步骤

### 1. 生成计划

```bash
vts plan TSLA.US
```

预期输出：

```
ExecutionPlan saved: TSLA.US
  Direction: 做多
  Status: pending_review
```

### 2. 人工审批

```bash
# 批准（记录审批时间）
vts review TSLA.US approve --notes "确认入场条件，开盘执行"

# 或拒绝
vts review TSLA.US reject --notes "宏观不确定性太大"

# 或要求修改
vts review TSLA.US revise --notes "仓位降至 3%"
```

预期输出：`Plan TSLA.US → approve`

## 自动化测试

```bash
pytest tests/test_plan.py -v
```

预期：6 个测试通过（从观点生成、中性观点拒绝、低置信度拒绝、approve / reject / revise 三种审批）。

## 手动验证

1. 生成后检查产物：

   ```bash
   cat artifacts/plans/TSLA.US.json | python3 -m json.tool
   ```

   验证点：
   - `direction` 与观点方向对应（看多 → 做多，看空 → 做空）
   - `approval_status` 为 `pending_review`，`approved_at` 为 null
   - `entry_condition` 引用了观点的核心逻辑
2. 执行 `vts review TSLA.US approve --notes "测试"`，再次查看产物：
   - `approval_status` 变为 `approved`
   - `approval_notes` 为 "测试"
   - `approved_at` 为审批时刻的时间戳
3. 风控门验证：构造一个中性或低置信度观点（如对只有简报、没有回测的 ticker 运行 `vts viewpoint`，置信度为低），然后 `vts plan` 应输出 `Cannot generate plan: ...` 且不生成产物。
4. 非法审批动作验证：`vts review TSLA.US foo` 应被 CLI 拒绝（choice 校验）。

## 管道整体回归

五个阶段全部走通后，运行编排器与存储层的回归测试：

```bash
pytest tests/test_pipeline.py tests/test_store.py -v
vts status
```

预期：10 个测试通过；`vts status` 显示 snapshots / briefs / reports / viewpoints / plans 各类产物计数及最新宏观立场。
