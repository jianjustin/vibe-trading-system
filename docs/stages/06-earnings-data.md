# 财报数据工具（Earnings Data）

> 迁移自 `earnings-agent` 仓库（`data/sec.py`、`data/earnings.py`），作为管道的数据支撑能力，服务于发现 / 回测阶段的财报事件研究。

## 功能说明

两个独立模块：

1. **SEC EDGAR 下载器**（`src/vts/loaders/sec_loader.py`，`SECDownloader`）
   - Ticker → CIK 映射（SEC 官方全量表，约 12,000 家公司）
   - 查找 8-K / 10-Q 等 filings（支持按日期范围翻历史分页）
   - 下载财报原文，优先级：Exhibit 99.1（财报新闻稿）> 8-K 主文件 > 第一个 HTML
2. **财报日历检测**（`src/vts/loaders/earnings_calendar.py`）
   - 基于 yfinance 检测标的在目标日期 ± 窗口内是否发布了财报（只认已发布、Reported EPS 非空的记录）
   - 批量扫描 watchlist

## 前置条件

SEC EDGAR 要求请求携带 `User-Agent`（格式 `'名字 邮箱'`），否则会被限速。通过环境变量设置：

```bash
export SEC_USER_AGENT="你的名字 your-email@example.com"
```

也可以每次用 `--user-agent` 选项传入。

## 操作步骤

### 下载财报文件：`vts earnings fetch`

```bash
# 单次模式：下载指定日期附近最近的一份 8-K（默认今天）
vts earnings fetch AAPL --date 2026-05-01

# 批量模式：过去 3 年的 8-K 和 10-Q
vts earnings fetch AAPL --years 3 --form 8-K,10-Q

# 批量模式：指定起始日期，只拉 10-Q
vts earnings fetch NVDA --since 2023-01-01 --form 10-Q

# 自定义输出目录
vts earnings fetch AAPL --date 2026-05-01 --out /tmp/filings
```

预期输出（单次模式）：

```
Downloaded: data/earnings_reports/AAPL/0000320193-26-000011.htm
```

落盘路径：单次模式 `{out}/{TICKER}/{accession}.htm`；批量模式 `{out}/{TICKER}/{FORM_TYPE}/{accession}.htm`。

注意：`--years` / `--since` 不能同时使用，也不能与 `--date` 混用；未找到任何文件时退出码为 1。

### 扫描财报日历：`vts earnings scan`

```bash
# 扫描多个标的在指定日期 ±2 天内是否发布了财报
vts earnings scan TSLA AAPL NVDA --date 2026-04-23

# 调整日期容差窗口
vts earnings scan TSLA --date 2026-04-23 --window 3
```

预期输出：

```
Earnings near 2026-04-23: TSLA
```

无命中时输出 `No earnings found near {date}`。

## 自动化测试

```bash
pytest tests/test_sec_loader.py tests/test_earnings_calendar.py -v
```

预期：14 个测试通过——

- `test_sec_loader.py`（8 个）：CIK 补零映射、未知 ticker、表单类型过滤与数量限制、日期范围过滤、Exhibit 99.1 优先级、文档兜底逻辑、文件落盘、primaryDocument 兜底下载
- `test_earnings_calendar.py`（6 个）：窗口内命中、窗口外未命中、未发布 EPS 不算命中、空数据、yfinance 异常容错、watchlist 批量扫描

测试全部 mock 网络请求，离线可运行。

## 手动验证

1. **真实下载验证**（需联网）：

   ```bash
   vts earnings fetch AAPL --date 2026-05-01 --user-agent "你的名字 邮箱"
   ```

   验证点：
   - 命令输出 `Downloaded: ...` 且退出码为 0
   - 下载的 `.htm` 文件可在浏览器中打开，内容为 Apple 财报新闻稿（Exhibit 99.1）或 8-K 正文
2. **批量下载验证：** `vts earnings fetch AAPL --since 2025-06-01`，确认 `data/earnings_reports/AAPL/` 下按表单类型（`8-K/`、`10-Q/`）分目录落盘，数量与该期间实际 filings 数一致（可在 [EDGAR 官网](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker=AAPL&type=8-K) 核对）。
3. **日历扫描验证：** 选一个已知的历史财报日（如 TSLA 2026 年 Q1 财报日），运行 `vts earnings scan TSLA --date <财报日>`，应命中；换一个非财报日，应不命中。
4. **错误处理验证：**
   - 不设置 `SEC_USER_AGENT` 且不传 `--user-agent`：CLI 报缺少必填选项
   - `vts earnings fetch FAKETICKER --date 2026-05-01`：输出未找到并以退出码 1 结束
