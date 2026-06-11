# 五阶段管道实施方案

> **面向自动化执行者：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行本方案。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 实现五个管道阶段（研究 → 发现 → 回测 → 观点 → 计划），每个阶段为独立可测试的模块，共享统一的产物存储，通过 CLI 暴露使用。

**架构：** 每个阶段是一个 Python 类，接收 `ArtifactStore`，执行自身逻辑，保存类型化产物。阶段之间仅通过产物通信。数据加载器封装 yfinance 获取 OHLCV 和宏观数据。CLI 将每个阶段作为子命令暴露。

**技术栈：** Python 3.11+, Pydantic 2, Click, yfinance, pandas, pytest

**工作目录：** `/Users/jianjustin/workspaces/vibe-trading-system`

---

## 文件结构

```
src/vts/
├── artifacts/
│   ├── schemas.py      # 修改 — 修复校验问题
│   └── store.py        # 新建 — 保存/加载/列表/渲染产物
├── loaders/
│   ├── __init__.py
│   └── yfinance_loader.py  # 新建 — OHLCV + 宏观指标获取
├── stages/
│   ├── base.py         # 新建 — Stage 协议
│   ├── research.py     # 实现 — MacroSnapshot 生成
│   ├── discover.py     # 实现 — ResearchBrief 创建
│   ├── backtest.py     # 实现 — BacktestReport 生成
│   ├── viewpoint.py    # 实现 — Viewpoint 综合
│   └── plan.py         # 实现 — ExecutionPlan + 人工审批
├── backtest/
│   ├── engine.py       # 新建 — 简化版美股回测引擎
│   └── metrics.py      # 新建 — 胜率、回撤、盈亏比
├── cli/
│   └── main.py         # 修改 — 接入真实阶段实现
└── orchestrator/
    └── pipeline.py     # 新建 — 顺序管道执行器

tests/
├── conftest.py         # 新建 — 共享测试夹具
├── test_store.py       # 新建
├── test_loader.py      # 新建
├── test_research.py    # 新建
├── test_discover.py    # 新建
├── test_backtest.py    # 新建
├── test_viewpoint.py   # 新建
├── test_plan.py        # 新建
├── test_engine.py      # 新建
└── test_pipeline.py    # 新建
```

---

## 任务 1：产物存储

**文件：**
- 修改：`src/vts/artifacts/schemas.py`
- 新建：`src/vts/artifacts/store.py`
- 新建：`tests/conftest.py`
- 新建：`tests/test_store.py`

- [ ] **步骤 1：修复 schema 校验问题**

当前 `counter_arguments` 字段设置了 `min_length=2` 且 `default_factory=list`，导致默认值校验失败。修复此问题并确保所有 schema 校验通过。

```python
# src/vts/artifacts/schemas.py
"""五阶段管道的类型化产物 schema。"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class MarketStance(str, Enum):
    OFFENSIVE = "进攻"
    CAUTIOUS = "谨慎"
    DEFENSIVE = "防守"


class MacroSnapshot(BaseModel):
    date: date
    stance: MarketStance
    treasury_10y: float | None = None
    treasury_2y: float | None = None
    spread_10y_2y: float | None = None
    dxy: float | None = None
    vix: float | None = None
    spy_above_50d: bool | None = None
    spy_above_200d: bool | None = None
    qqq_above_50d: bool | None = None
    qqq_above_200d: bool | None = None
    hy_spread: float | None = None
    most_important_change: str = ""
    impact_on_growth: str = ""
    impact_on_watchlist: str = ""
    next_step: str = ""


class NextAction(str, Enum):
    CONTINUE_RESEARCH = "继续研究"
    DECISION_CHALLENGE = "决策挑战"
    BACKTEST_SETUP = "回测 setup"
    ABANDON = "放弃"


class ResearchBrief(BaseModel):
    ticker: str
    thesis: str
    key_evidence: list[str] = Field(default_factory=list)
    core_driver: str = ""
    macro_sensitivity: str = ""
    valuation_sensitivity: str = ""
    catalysts: str = ""
    invalidation: str = ""
    next_action: NextAction = NextAction.CONTINUE_RESEARCH


class BacktestReport(BaseModel):
    rule_name: str
    ticker_scope: str
    market_filter: str = ""
    entry_rule: str
    exit_rule: str
    data_source: str = "yfinance"
    time_range: str = ""
    sample_count: int = 0
    win_rate: float | None = None
    profit_loss_ratio: float | None = None
    max_drawdown: float | None = None
    vs_spy: str = ""
    vs_qqq: str = ""
    conclusion: str = ""


class ViewpointDirection(str, Enum):
    BULLISH = "看多"
    NEUTRAL = "中性"
    BEARISH = "看空"


class Confidence(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class Viewpoint(BaseModel):
    ticker: str
    direction: ViewpointDirection
    confidence: Confidence
    macro_support: str = ""
    core_logic: str = ""
    supporting_evidence: str = ""
    counter_arguments: list[str] = Field(default_factory=list)
    invalidation: str = ""
    valid_until: str = ""


class ApprovalStatus(str, Enum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class ExecutionPlan(BaseModel):
    ticker: str
    direction: str
    position_pct: str = ""
    entry_condition: str = ""
    entry_price_range: str = ""
    stop_loss: str = ""
    target: str = ""
    holding_period: str = ""
    prerequisites: str = ""
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approval_notes: str = ""
    approved_at: datetime | None = None
```

- [ ] **步骤 2：编写产物存储测试**

```python
# tests/conftest.py
import pytest
from pathlib import Path
from datetime import date

from vts.artifacts.store import ArtifactStore
from vts.artifacts.schemas import (
    MacroSnapshot, MarketStance, ResearchBrief, NextAction,
    BacktestReport, Viewpoint, ViewpointDirection, Confidence,
    ExecutionPlan, ApprovalStatus,
)


@pytest.fixture
def store(tmp_path):
    return ArtifactStore(base_dir=tmp_path)


@pytest.fixture
def sample_snapshot():
    return MacroSnapshot(
        date=date(2026, 6, 9),
        stance=MarketStance.CAUTIOUS,
        treasury_10y=4.28,
        vix=18.5,
        dxy=104.2,
        spy_above_50d=True,
        spy_above_200d=True,
        qqq_above_50d=True,
        qqq_above_200d=False,
        most_important_change="VIX 降至 20 以下",
        impact_on_growth="利好成长股",
        next_step="关注国债收益率曲线",
    )


@pytest.fixture
def sample_brief():
    return ResearchBrief(
        ticker="TSLA.US",
        thesis="电动车龙头，交付动能强劲",
        key_evidence=[
            "Q1 交付超预期 8%",
            "毛利率连续 3 个季度扩张",
            "FSD 授权收入浮现",
        ],
        core_driver="季度交付数据",
        macro_sensitivity="利率影响汽车融资",
        valuation_sensitivity="营收增速与利润率趋势",
        catalysts="Q2 财报 7 月 23 日",
        invalidation="交付连续两个季度不及预期",
        next_action=NextAction.BACKTEST_SETUP,
    )


@pytest.fixture
def sample_backtest():
    return BacktestReport(
        rule_name="财报后跳空延续",
        ticker_scope="TSLA.US",
        market_filter="QQQ 在 50 日均线之上",
        entry_rule="财报日收盘买入（跳空 > 3%）",
        exit_rule="5 个交易日后卖出或 -5% 止损",
        time_range="2022-01-01 至 2026-01-01",
        sample_count=16,
        win_rate=0.625,
        profit_loss_ratio=1.8,
        max_drawdown=0.12,
        vs_spy="年化超额 Alpha +3.2%",
        conclusion="模拟观察",
    )


@pytest.fixture
def sample_viewpoint():
    return Viewpoint(
        ticker="TSLA.US",
        direction=ViewpointDirection.BULLISH,
        confidence=Confidence.MEDIUM,
        macro_support="低 VIX，利于成长的环境",
        core_logic="强劲交付 + 利润率扩张 + 有利宏观",
        supporting_evidence="回测显示跳空延续有正向 edge",
        counter_arguments=[
            "60 倍远期 PE，估值偏高",
            "中国电动车市场竞争加剧",
        ],
        invalidation="美联储转鹰或交付不及预期",
        valid_until="Q2 财报（2026-07-23）",
    )


@pytest.fixture
def sample_plan():
    return ExecutionPlan(
        ticker="TSLA.US",
        direction="做多",
        position_pct="5%",
        entry_condition="价格回踩 50 日均线或财报后跳空 > 3%",
        entry_price_range="$280-$310",
        stop_loss="$265（-8%）",
        target="第一目标 $340，第二目标 $380",
        holding_period="中线（4-8 周）",
        prerequisites="VIX 维持 25 以下，QQQ 在 50 日均线之上",
    )
```

```python
# tests/test_store.py
from vts.artifacts.store import ArtifactStore
from vts.artifacts.schemas import MacroSnapshot, MarketStance
from datetime import date


def test_save_and_load(store, sample_snapshot):
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    loaded = store.load("snapshots", "2026-06-09", MacroSnapshot)
    assert loaded.stance == MarketStance.CAUTIOUS
    assert loaded.date == date(2026, 6, 9)
    assert loaded.treasury_10y == 4.28


def test_list_ids_sorted(store, sample_snapshot):
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    store.save(sample_snapshot, "snapshots", "2026-06-08")
    ids = store.list_ids("snapshots")
    assert ids == ["2026-06-08", "2026-06-09"]


def test_list_ids_empty(store):
    assert store.list_ids("nonexistent") == []


def test_latest(store, sample_snapshot):
    s1 = sample_snapshot.model_copy(update={"date": date(2026, 6, 8)})
    store.save(s1, "snapshots", "2026-06-08")
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    latest = store.latest("snapshots", MacroSnapshot)
    assert latest.date == date(2026, 6, 9)


def test_latest_empty(store):
    assert store.latest("snapshots", MacroSnapshot) is None


def test_to_markdown(store, sample_snapshot):
    md = store.to_markdown(sample_snapshot)
    assert "4.28" in md
    assert "18.5" in md


def test_load_nonexistent_raises(store):
    import pytest
    with pytest.raises(FileNotFoundError):
        store.load("snapshots", "nonexistent", MacroSnapshot)
```

- [ ] **步骤 3：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pip install -e ".[dev]" && pytest tests/test_store.py -v`
预期：FAIL — `ModuleNotFoundError: No module named 'vts.artifacts.store'`

- [ ] **步骤 4：实现产物存储**

```python
# src/vts/artifacts/store.py
"""基于文件的产物存储，支持 JSON 持久化和 Markdown 渲染。"""

from pathlib import Path

from pydantic import BaseModel


class ArtifactStore:
    """保存、加载、列出并渲染类型化 Pydantic 产物为 JSON 文件。"""

    def __init__(self, base_dir: str | Path = "artifacts"):
        self.base_dir = Path(base_dir)

    def save(self, artifact: BaseModel, artifact_type: str, artifact_id: str) -> Path:
        directory = self.base_dir / artifact_type
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{artifact_id}.json"
        path.write_text(artifact.model_dump_json(indent=2))
        return path

    def load(self, artifact_type: str, artifact_id: str, model_class: type[BaseModel]) -> BaseModel:
        path = self.base_dir / artifact_type / f"{artifact_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return model_class.model_validate_json(path.read_text())

    def list_ids(self, artifact_type: str) -> list[str]:
        directory = self.base_dir / artifact_type
        if not directory.exists():
            return []
        return sorted(p.stem for p in directory.glob("*.json"))

    def latest(self, artifact_type: str, model_class: type[BaseModel]) -> BaseModel | None:
        ids = self.list_ids(artifact_type)
        if not ids:
            return None
        return self.load(artifact_type, ids[-1], model_class)

    def to_markdown(self, artifact: BaseModel) -> str:
        lines = []
        for field_name, value in artifact.model_dump().items():
            label = field_name.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"**{label}:**")
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{label}:** {value}")
        return "\n".join(lines)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_store.py -v`
预期：全部 7 个测试通过

- [ ] **步骤 6：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/artifacts/schemas.py src/vts/artifacts/store.py tests/conftest.py tests/test_store.py
git commit -m "feat: artifact store with save/load/list/render + fix schemas"
```

---

## 任务 2：数据加载器

**文件：**
- 新建：`src/vts/loaders/yfinance_loader.py`
- 新建：`tests/test_loader.py`

- [ ] **步骤 1：编写数据加载器测试**

测试使用 monkeypatch 避免真实 API 调用。

```python
# tests/test_loader.py
import pandas as pd
import numpy as np
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from vts.loaders.yfinance_loader import YFinanceLoader, MACRO_TICKERS


@pytest.fixture
def loader():
    return YFinanceLoader()


@pytest.fixture
def mock_ohlcv():
    dates = pd.date_range("2026-01-01", periods=250, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    return pd.DataFrame(
        {
            "Open": prices + np.random.rand(250),
            "High": prices + abs(np.random.randn(250)),
            "Low": prices - abs(np.random.randn(250)),
            "Close": prices,
            "Volume": np.random.randint(1_000_000, 10_000_000, 250),
        },
        index=dates,
    )


def test_fetch_ohlcv_normalizes_columns(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        df = loader.fetch_ohlcv("SPY", "2026-01-01", "2026-12-01")
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert len(df) == 250


def test_fetch_ohlcv_empty_raises(loader):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="No data"):
            loader.fetch_ohlcv("INVALID", "2026-01-01", "2026-12-01")


def test_compute_ma_status(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        result = loader.compute_ma_status("SPY", [50, 200])
        assert 50 in result
        assert 200 in result
        assert isinstance(result[50], bool)
        assert isinstance(result[200], bool)


def test_compute_ma_status_insufficient_data(loader):
    short_data = pd.DataFrame(
        {"Open": [1], "High": [2], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.date_range("2026-06-01", periods=1),
    )
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=short_data):
        result = loader.compute_ma_status("SPY", [50])
        assert result[50] is None


def test_fetch_macro_indicators(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        indicators = loader.fetch_macro_indicators()
        for key in ["treasury_10y", "vix", "dxy", "spy", "qqq"]:
            assert key in indicators
            assert indicators[key] is not None
            assert "latest" in indicators[key]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_loader.py -v`
预期：FAIL — `ModuleNotFoundError`

- [ ] **步骤 3：实现数据加载器**

```python
# src/vts/loaders/yfinance_loader.py
"""基于 yfinance 的数据加载器，获取 OHLCV 和宏观指标。"""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

MACRO_TICKERS = {
    "treasury_10y": "^TNX",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "spy": "SPY",
    "qqq": "QQQ",
    "hyg": "HYG",
}


class YFinanceLoader:
    """通过 yfinance 获取 OHLCV 数据和宏观指标。"""

    def fetch_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            raise ValueError(f"No data for {ticker} between {start_date} and {end_date}")
        col_map = {}
        for c in data.columns:
            name = c[0].lower() if isinstance(c, tuple) else c.lower()
            col_map[c] = name
        data = data.rename(columns=col_map)
        return data[["open", "high", "low", "close", "volume"]]

    def fetch_macro_indicators(self) -> dict:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
        results = {}
        for key, ticker in MACRO_TICKERS.items():
            try:
                data = self.fetch_ohlcv(ticker, start, end)
                results[key] = {"latest": float(data["close"].iloc[-1]), "data": data}
            except Exception:
                results[key] = None
        return results

    def compute_ma_status(self, ticker: str, periods: list[int] | None = None) -> dict[int, bool | None]:
        if periods is None:
            periods = [50, 200]
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=max(periods) + 50)).strftime("%Y-%m-%d")
        data = self.fetch_ohlcv(ticker, start, end)
        latest_close = float(data["close"].iloc[-1])
        result = {}
        for period in periods:
            if len(data) >= period:
                ma = float(data["close"].rolling(period).mean().iloc[-1])
                result[period] = latest_close > ma
            else:
                result[period] = None
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_loader.py -v`
预期：全部 5 个测试通过

- [ ] **步骤 5：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/loaders/yfinance_loader.py tests/test_loader.py
git commit -m "feat: yfinance data loader with OHLCV + macro indicators"
```

---

## 任务 3：研究阶段（MacroSnapshot）

**文件：**
- 新建：`src/vts/stages/base.py`
- 修改：`src/vts/stages/research.py`
- 新建：`tests/test_research.py`

- [ ] **步骤 1：编写 Stage 基类**

```python
# src/vts/stages/base.py
"""管道阶段基类。"""

from abc import ABC, abstractmethod

from vts.artifacts.store import ArtifactStore


class Stage(ABC):
    """所有阶段接收 ArtifactStore，执行逻辑，保存产物，返回产物 ID。"""

    def __init__(self, store: ArtifactStore):
        self.store = store

    @abstractmethod
    def run(self, **kwargs) -> str:
        """执行阶段并返回已保存的产物 ID。"""
        ...
```

- [ ] **步骤 2：编写研究阶段测试**

```python
# tests/test_research.py
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from datetime import date

from vts.stages.research import ResearchStage
from vts.artifacts.schemas import MacroSnapshot, MarketStance


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    dates = pd.date_range("2025-06-01", periods=250, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 250,
        },
        index=dates,
    )
    loader.fetch_macro_indicators.return_value = {
        "treasury_10y": {"latest": 4.28, "data": ohlcv},
        "vix": {"latest": 17.5, "data": ohlcv},
        "dxy": {"latest": 104.0, "data": ohlcv},
        "spy": {"latest": 540.0, "data": ohlcv},
        "qqq": {"latest": 470.0, "data": ohlcv},
        "hyg": {"latest": 78.0, "data": ohlcv},
    }
    loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: True}
    return loader


def test_research_produces_snapshot(store, mock_loader):
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    assert artifact_id == date.today().isoformat()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.treasury_10y == 4.28
    assert snapshot.vix == 17.5


def test_research_offensive_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 14.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: True}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.OFFENSIVE


def test_research_defensive_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 30.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: False, 200: False}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.DEFENSIVE


def test_research_cautious_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 22.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: False}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.CAUTIOUS
```

- [ ] **步骤 3：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_research.py -v`
预期：FAIL — `cannot import name 'ResearchStage'`

- [ ] **步骤 4：实现研究阶段**

```python
# src/vts/stages/research.py
"""研究阶段：获取宏观指标并生成 MacroSnapshot 产物。"""

from datetime import date

from vts.artifacts.schemas import MacroSnapshot, MarketStance
from vts.artifacts.store import ArtifactStore
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.base import Stage


class ResearchStage(Stage):
    """获取宏观指标，判定市场立场，保存 MacroSnapshot。"""

    def __init__(self, store: ArtifactStore, loader: YFinanceLoader | None = None):
        super().__init__(store)
        self.loader = loader or YFinanceLoader()

    def run(self, **kwargs) -> str:
        indicators = self.loader.fetch_macro_indicators()
        spy_ma = self.loader.compute_ma_status("SPY", [50, 200])
        qqq_ma = self.loader.compute_ma_status("QQQ", [50, 200])

        vix = self._get_latest(indicators, "vix")
        treasury_10y = self._get_latest(indicators, "treasury_10y")
        dxy = self._get_latest(indicators, "dxy")

        stance = self._determine_stance(vix, spy_ma, qqq_ma)

        snapshot = MacroSnapshot(
            date=date.today(),
            stance=stance,
            treasury_10y=treasury_10y,
            vix=vix,
            dxy=dxy,
            spy_above_50d=spy_ma.get(50),
            spy_above_200d=spy_ma.get(200),
            qqq_above_50d=qqq_ma.get(50),
            qqq_above_200d=qqq_ma.get(200),
        )

        artifact_id = date.today().isoformat()
        self.store.save(snapshot, "snapshots", artifact_id)
        return artifact_id

    def _determine_stance(
        self, vix: float | None, spy_ma: dict, qqq_ma: dict
    ) -> MarketStance:
        if vix is not None and vix > 25:
            return MarketStance.DEFENSIVE
        if spy_ma.get(200) is False and spy_ma.get(50) is False:
            return MarketStance.DEFENSIVE
        if (
            vix is not None
            and vix < 18
            and spy_ma.get(50) is True
            and qqq_ma.get(50) is True
        ):
            return MarketStance.OFFENSIVE
        return MarketStance.CAUTIOUS

    def _get_latest(self, indicators: dict, key: str) -> float | None:
        entry = indicators.get(key)
        if entry is None:
            return None
        return entry.get("latest")
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_research.py -v`
预期：全部 4 个测试通过

- [ ] **步骤 6：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/stages/base.py src/vts/stages/research.py tests/test_research.py
git commit -m "feat: research stage — macro indicators to MacroSnapshot with stance detection"
```

---

## 任务 4：发现阶段（ResearchBrief）

**文件：**
- 修改：`src/vts/stages/discover.py`
- 新建：`tests/test_discover.py`

- [ ] **步骤 1：编写发现阶段测试**

```python
# tests/test_discover.py
import pytest
from vts.stages.discover import DiscoverStage
from vts.artifacts.schemas import ResearchBrief, NextAction


def test_discover_saves_brief(store):
    stage = DiscoverStage(store)
    artifact_id = stage.run(
        ticker="TSLA.US",
        thesis="电动车龙头，交付动能强劲",
        key_evidence=["Q1 超预期", "毛利率扩张", "FSD 收入"],
        core_driver="季度交付数据",
        invalidation="交付连续两季度不及预期",
        next_action="回测 setup",
    )
    assert artifact_id == "TSLA.US"
    brief = store.load("briefs", "TSLA.US", ResearchBrief)
    assert brief.ticker == "TSLA.US"
    assert brief.next_action == NextAction.BACKTEST_SETUP
    assert len(brief.key_evidence) == 3


def test_discover_truncates_evidence(store):
    stage = DiscoverStage(store)
    stage.run(
        ticker="NVDA.US",
        thesis="AI 算力需求",
        key_evidence=["A", "B", "C", "D", "E"],
        invalidation="云资本开支放缓",
    )
    brief = store.load("briefs", "NVDA.US", ResearchBrief)
    assert len(brief.key_evidence) == 3


def test_discover_requires_ticker(store):
    stage = DiscoverStage(store)
    with pytest.raises(ValueError, match="ticker"):
        stage.run(ticker="", thesis="test", invalidation="test")


def test_discover_requires_thesis(store):
    stage = DiscoverStage(store)
    with pytest.raises(ValueError, match="thesis"):
        stage.run(ticker="TSLA.US", thesis="", invalidation="test")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_discover.py -v`
预期：FAIL — `cannot import name 'DiscoverStage'`

- [ ] **步骤 3：实现发现阶段**

```python
# src/vts/stages/discover.py
"""发现阶段：创建并保存 ResearchBrief 产物。"""

from vts.artifacts.schemas import NextAction, ResearchBrief
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_ACTION_MAP = {
    "继续研究": NextAction.CONTINUE_RESEARCH,
    "决策挑战": NextAction.DECISION_CHALLENGE,
    "回测 setup": NextAction.BACKTEST_SETUP,
    "放弃": NextAction.ABANDON,
}


class DiscoverStage(Stage):
    """从结构化输入创建 ResearchBrief 并保存。"""

    def __init__(self, store: ArtifactStore):
        super().__init__(store)

    def run(self, **kwargs) -> str:
        ticker = kwargs.get("ticker", "")
        thesis = kwargs.get("thesis", "")
        if not ticker:
            raise ValueError("ticker is required")
        if not thesis:
            raise ValueError("thesis is required")

        evidence = kwargs.get("key_evidence", [])
        if len(evidence) > 3:
            evidence = evidence[:3]

        action_str = kwargs.get("next_action", "继续研究")
        next_action = _ACTION_MAP.get(action_str, NextAction.CONTINUE_RESEARCH)

        brief = ResearchBrief(
            ticker=ticker,
            thesis=thesis,
            key_evidence=evidence,
            core_driver=kwargs.get("core_driver", ""),
            macro_sensitivity=kwargs.get("macro_sensitivity", ""),
            valuation_sensitivity=kwargs.get("valuation_sensitivity", ""),
            catalysts=kwargs.get("catalysts", ""),
            invalidation=kwargs.get("invalidation", ""),
            next_action=next_action,
        )

        self.store.save(brief, "briefs", ticker)
        return ticker
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_discover.py -v`
预期：全部 4 个测试通过

- [ ] **步骤 5：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/stages/discover.py tests/test_discover.py
git commit -m "feat: discover stage — structured ResearchBrief creation with validation"
```

---

## 任务 5：回测引擎与阶段

**文件：**
- 新建：`src/vts/backtest/engine.py`
- 新建：`src/vts/backtest/metrics.py`
- 修改：`src/vts/stages/backtest.py`
- 新建：`tests/test_engine.py`
- 新建：`tests/test_backtest.py`

- [ ] **步骤 1：编写回测引擎测试**

```python
# tests/test_engine.py
import pandas as pd
import numpy as np
import pytest
from vts.backtest.engine import SimpleEquityEngine
from vts.backtest.metrics import calc_metrics


@pytest.fixture
def price_data():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    prices = 100 + np.cumsum(np.random.randn(100) * 1.5)
    return pd.DataFrame(
        {
            "open": prices + np.random.rand(100) * 0.5,
            "high": prices + abs(np.random.randn(100)),
            "low": prices - abs(np.random.randn(100)),
            "close": prices,
            "volume": np.random.randint(1_000_000, 5_000_000, 100),
        },
        index=dates,
    )


def test_engine_buy_and_hold(price_data):
    signals = pd.Series(0, index=price_data.index)
    signals.iloc[5] = 1   # 第 5 天买入
    signals.iloc[50] = -1  # 第 50 天卖出
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 1
    assert trades[0]["entry_date"] == price_data.index[5]
    assert trades[0]["exit_date"] == price_data.index[50]


def test_engine_no_signals(price_data):
    signals = pd.Series(0, index=price_data.index)
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 0


def test_engine_multiple_trades(price_data):
    signals = pd.Series(0, index=price_data.index)
    signals.iloc[5] = 1
    signals.iloc[15] = -1
    signals.iloc[30] = 1
    signals.iloc[45] = -1
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 2


def test_calc_metrics_basic():
    trades = [
        {"pnl_pct": 0.05},
        {"pnl_pct": -0.03},
        {"pnl_pct": 0.08},
        {"pnl_pct": -0.02},
        {"pnl_pct": 0.04},
    ]
    m = calc_metrics(trades)
    assert m["sample_count"] == 5
    assert m["win_rate"] == 0.6
    assert m["profit_loss_ratio"] > 0
    assert "max_drawdown" in m
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_engine.py -v`
预期：FAIL — `ModuleNotFoundError`

- [ ] **步骤 3：实现指标模块**

```python
# src/vts/backtest/metrics.py
"""基础回测指标：胜率、盈亏比、最大回撤。"""


def calc_metrics(trades: list[dict]) -> dict:
    """从包含 'pnl_pct' 键的交易字典列表计算汇总统计。"""
    if not trades:
        return {
            "sample_count": 0,
            "win_rate": None,
            "profit_loss_ratio": None,
            "max_drawdown": None,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) if pnls else 0
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 1

    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")

    cumulative = 0
    peak = 0
    max_dd = 0
    for pnl in pnls:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    return {
        "sample_count": len(pnls),
        "win_rate": round(win_rate, 4),
        "profit_loss_ratio": round(profit_loss_ratio, 4),
        "max_drawdown": round(max_dd, 4),
    }
```

- [ ] **步骤 4：实现回测引擎**

```python
# src/vts/backtest/engine.py
"""简化版美股回测引擎。仅做多，逐 K 线执行。"""

import pandas as pd


class SimpleEquityEngine:
    """基于 OHLCV 数据和买卖信号的逐 K 线回测。

    信号：1 = 买入，-1 = 卖出，0 = 持有。
    """

    def __init__(self, initial_capital: float = 100_000, slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.slippage = slippage

    def run(self, data: pd.DataFrame, signals: pd.Series) -> list[dict]:
        trades = []
        position = None
        capital = self.initial_capital

        for i, (dt, row) in enumerate(data.iterrows()):
            sig = signals.iloc[i] if i < len(signals) else 0

            if sig == 1 and position is None:
                entry_price = row["close"] * (1 + self.slippage)
                shares = int(capital / entry_price)
                if shares > 0:
                    position = {
                        "entry_date": dt,
                        "entry_price": entry_price,
                        "shares": shares,
                    }

            elif sig == -1 and position is not None:
                exit_price = row["close"] * (1 - self.slippage)
                pnl = (exit_price - position["entry_price"]) * position["shares"]
                pnl_pct = (exit_price / position["entry_price"]) - 1
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": dt,
                        "entry_price": round(position["entry_price"], 4),
                        "exit_price": round(exit_price, 4),
                        "shares": position["shares"],
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 6),
                    }
                )
                capital += pnl
                position = None

        return trades
```

- [ ] **步骤 5：运行引擎测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_engine.py -v`
预期：全部 4 个测试通过

- [ ] **步骤 6：编写回测阶段测试**

```python
# tests/test_backtest.py
import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock

from vts.stages.backtest import BacktestStage
from vts.artifacts.schemas import BacktestReport


@pytest.fixture
def mock_loader_for_bt():
    loader = MagicMock()
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 1.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices + np.random.rand(250) * 0.5,
            "high": prices + abs(np.random.randn(250)),
            "low": prices - abs(np.random.randn(250)),
            "close": prices,
            "volume": np.random.randint(1_000_000, 5_000_000, 250),
        },
        index=dates,
    )
    loader.fetch_ohlcv.return_value = ohlcv
    return loader


def test_backtest_stage_produces_report(store, mock_loader_for_bt):
    def signal_fn(data):
        signals = pd.Series(0, index=data.index)
        signals.iloc[10] = 1
        signals.iloc[20] = -1
        signals.iloc[50] = 1
        signals.iloc[65] = -1
        return signals

    stage = BacktestStage(store, loader=mock_loader_for_bt)
    artifact_id = stage.run(
        ticker="TSLA.US",
        rule_name="test_setup",
        signal_fn=signal_fn,
        start_date="2024-01-01",
        end_date="2025-01-01",
    )
    report = store.load("reports", artifact_id, BacktestReport)
    assert report.rule_name == "test_setup"
    assert report.sample_count == 2
    assert report.win_rate is not None


def test_backtest_stage_no_trades(store, mock_loader_for_bt):
    def signal_fn(data):
        return pd.Series(0, index=data.index)

    stage = BacktestStage(store, loader=mock_loader_for_bt)
    artifact_id = stage.run(
        ticker="TSLA.US",
        rule_name="no_trades",
        signal_fn=signal_fn,
        start_date="2024-01-01",
        end_date="2025-01-01",
    )
    report = store.load("reports", artifact_id, BacktestReport)
    assert report.sample_count == 0
```

- [ ] **步骤 7：实现回测阶段**

```python
# src/vts/stages/backtest.py
"""回测阶段：执行历史验证并生成 BacktestReport 产物。"""

from typing import Callable

import pandas as pd

from vts.artifacts.schemas import BacktestReport
from vts.artifacts.store import ArtifactStore
from vts.backtest.engine import SimpleEquityEngine
from vts.backtest.metrics import calc_metrics
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.base import Stage


class BacktestStage(Stage):
    """对给定信号函数运行回测并保存 BacktestReport。"""

    def __init__(self, store: ArtifactStore, loader: YFinanceLoader | None = None):
        super().__init__(store)
        self.loader = loader or YFinanceLoader()

    def run(self, **kwargs) -> str:
        ticker: str = kwargs["ticker"]
        rule_name: str = kwargs["rule_name"]
        signal_fn: Callable[[pd.DataFrame], pd.Series] = kwargs["signal_fn"]
        start_date: str = kwargs.get("start_date", "2022-01-01")
        end_date: str = kwargs.get("end_date", "2026-01-01")
        market_filter: str = kwargs.get("market_filter", "")

        data = self.loader.fetch_ohlcv(ticker, start_date, end_date)
        signals = signal_fn(data)

        engine = SimpleEquityEngine()
        trades = engine.run(data, signals)
        metrics = calc_metrics(trades)

        conclusion = self._derive_conclusion(metrics)

        report = BacktestReport(
            rule_name=rule_name,
            ticker_scope=ticker,
            market_filter=market_filter,
            entry_rule=kwargs.get("entry_rule", ""),
            exit_rule=kwargs.get("exit_rule", ""),
            time_range=f"{start_date} to {end_date}",
            sample_count=metrics["sample_count"],
            win_rate=metrics["win_rate"],
            profit_loss_ratio=metrics["profit_loss_ratio"],
            max_drawdown=metrics["max_drawdown"],
            conclusion=conclusion,
        )

        artifact_id = f"{ticker}-{rule_name}"
        self.store.save(report, "reports", artifact_id)
        return artifact_id

    def _derive_conclusion(self, metrics: dict) -> str:
        if metrics["sample_count"] < 10:
            return "样本不足，不下结论"
        win_rate = metrics.get("win_rate") or 0
        plr = metrics.get("profit_loss_ratio") or 0
        if win_rate < 0.4 and plr < 1.0:
            return "放弃"
        if win_rate > 0.55 and plr > 1.5:
            return "小仓位验证"
        if win_rate > 0.45:
            return "模拟观察"
        return "修改"
```

- [ ] **步骤 8：运行回测测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_backtest.py tests/test_engine.py -v`
预期：全部 6 个测试通过

- [ ] **步骤 9：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/backtest/engine.py src/vts/backtest/metrics.py src/vts/stages/backtest.py tests/test_engine.py tests/test_backtest.py
git commit -m "feat: backtest engine + stage — bar-by-bar simulation with metrics and auto-conclusion"
```

---

## 任务 6：观点阶段

**文件：**
- 修改：`src/vts/stages/viewpoint.py`
- 新建：`tests/test_viewpoint.py`

- [ ] **步骤 1：编写观点阶段测试**

```python
# tests/test_viewpoint.py
import pytest
from datetime import date

from vts.stages.viewpoint import ViewpointStage
from vts.artifacts.schemas import (
    MacroSnapshot, MarketStance, ResearchBrief, NextAction,
    BacktestReport, Viewpoint, ViewpointDirection, Confidence,
)


def _seed_artifacts(store, stance=MarketStance.CAUTIOUS, conclusion="模拟观察"):
    store.save(
        MacroSnapshot(date=date(2026, 6, 9), stance=stance, vix=18.0),
        "snapshots", "2026-06-09",
    )
    store.save(
        ResearchBrief(
            ticker="TSLA.US", thesis="电动车动能", invalidation="交付不及预期",
            key_evidence=["证据 A", "证据 B"],
        ),
        "briefs", "TSLA.US",
    )
    store.save(
        BacktestReport(
            rule_name="gap_cont", ticker_scope="TSLA.US",
            entry_rule="跳空 > 3%", exit_rule="持有 5 天",
            sample_count=20, win_rate=0.6, profit_loss_ratio=1.8,
            max_drawdown=0.1, conclusion=conclusion,
        ),
        "reports", "TSLA.US-gap_cont",
    )


def test_viewpoint_synthesizes(store):
    _seed_artifacts(store)
    stage = ViewpointStage(store)
    artifact_id = stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", artifact_id, Viewpoint)
    assert vp.ticker == "TSLA.US"
    assert vp.direction in list(ViewpointDirection)
    assert vp.confidence in list(Confidence)
    assert len(vp.counter_arguments) >= 1


def test_viewpoint_bullish_on_good_backtest_and_offensive(store):
    _seed_artifacts(store, stance=MarketStance.OFFENSIVE, conclusion="小仓位验证")
    stage = ViewpointStage(store)
    stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", "TSLA.US", Viewpoint)
    assert vp.direction == ViewpointDirection.BULLISH


def test_viewpoint_bearish_on_bad_backtest(store):
    _seed_artifacts(store, conclusion="放弃")
    stage = ViewpointStage(store)
    stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", "TSLA.US", Viewpoint)
    assert vp.direction == ViewpointDirection.BEARISH


def test_viewpoint_missing_brief_raises(store):
    store.save(
        MacroSnapshot(date=date(2026, 6, 9), stance=MarketStance.CAUTIOUS),
        "snapshots", "2026-06-09",
    )
    stage = ViewpointStage(store)
    with pytest.raises(FileNotFoundError):
        stage.run(ticker="UNKNOWN.US")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_viewpoint.py -v`
预期：FAIL — `cannot import name 'ViewpointStage'`

- [ ] **步骤 3：实现观点阶段**

```python
# src/vts/stages/viewpoint.py
"""观点阶段：将上游产物综合为 Viewpoint。"""

from vts.artifacts.schemas import (
    BacktestReport, Confidence, MacroSnapshot, MarketStance,
    ResearchBrief, Viewpoint, ViewpointDirection,
)
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_POSITIVE_CONCLUSIONS = {"小仓位验证", "模拟观察"}
_NEGATIVE_CONCLUSIONS = {"放弃"}


class ViewpointStage(Stage):
    """将 MacroSnapshot + ResearchBrief + BacktestReport 综合为 Viewpoint。"""

    def __init__(self, store: ArtifactStore):
        super().__init__(store)

    def run(self, **kwargs) -> str:
        ticker: str = kwargs["ticker"]
        snapshot = self.store.latest("snapshots", MacroSnapshot)
        brief = self.store.load("briefs", ticker, ResearchBrief)

        bt_report = self._find_report(ticker)

        direction = self._determine_direction(snapshot, bt_report)
        confidence = self._determine_confidence(snapshot, bt_report)
        macro_support = self._describe_macro(snapshot)
        counter_args = self._generate_counter_arguments(brief, snapshot)

        viewpoint = Viewpoint(
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            macro_support=macro_support,
            core_logic=f"{brief.thesis} — 回测结论: {bt_report.conclusion if bt_report else 'N/A'}",
            supporting_evidence="; ".join(brief.key_evidence),
            counter_arguments=counter_args,
            invalidation=brief.invalidation,
            valid_until="下一催化剂或宏观变化",
        )

        self.store.save(viewpoint, "viewpoints", ticker)
        return ticker

    def _find_report(self, ticker: str) -> BacktestReport | None:
        report_ids = self.store.list_ids("reports")
        matching = [rid for rid in report_ids if rid.startswith(ticker)]
        if not matching:
            return None
        return self.store.load("reports", matching[-1], BacktestReport)

    def _determine_direction(
        self, snapshot: MacroSnapshot | None, report: BacktestReport | None
    ) -> ViewpointDirection:
        if report and report.conclusion in _NEGATIVE_CONCLUSIONS:
            return ViewpointDirection.BEARISH
        if snapshot and snapshot.stance == MarketStance.DEFENSIVE:
            return ViewpointDirection.NEUTRAL
        if report and report.conclusion in _POSITIVE_CONCLUSIONS:
            if snapshot and snapshot.stance == MarketStance.OFFENSIVE:
                return ViewpointDirection.BULLISH
            return ViewpointDirection.BULLISH
        return ViewpointDirection.NEUTRAL

    def _determine_confidence(
        self, snapshot: MacroSnapshot | None, report: BacktestReport | None
    ) -> Confidence:
        if report is None or report.sample_count < 10:
            return Confidence.LOW
        if report.win_rate and report.win_rate > 0.55 and report.profit_loss_ratio and report.profit_loss_ratio > 1.5:
            if snapshot and snapshot.stance != MarketStance.DEFENSIVE:
                return Confidence.HIGH
        if report.win_rate and report.win_rate > 0.45:
            return Confidence.MEDIUM
        return Confidence.LOW

    def _describe_macro(self, snapshot: MacroSnapshot | None) -> str:
        if snapshot is None:
            return "无宏观数据"
        return f"市场立场: {snapshot.stance.value}, VIX: {snapshot.vix}"

    def _generate_counter_arguments(
        self, brief: ResearchBrief, snapshot: MacroSnapshot | None
    ) -> list[str]:
        args = []
        if brief.invalidation:
            args.append(f"失效风险: {brief.invalidation}")
        if snapshot and snapshot.stance == MarketStance.DEFENSIVE:
            args.append("宏观环境处于防守状态 — 风险偏好降低")
        if not args:
            args.append("历史数据有限，难以得出稳健结论")
        return args
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_viewpoint.py -v`
预期：全部 4 个测试通过

- [ ] **步骤 5：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/stages/viewpoint.py tests/test_viewpoint.py
git commit -m "feat: viewpoint stage — rule-based synthesis from macro + brief + backtest"
```

---

## 任务 7：计划阶段（ExecutionPlan + 人工审批）

**文件：**
- 修改：`src/vts/stages/plan.py`
- 新建：`tests/test_plan.py`

- [ ] **步骤 1：编写计划阶段测试**

```python
# tests/test_plan.py
import pytest
from datetime import date

from vts.stages.plan import PlanStage
from vts.artifacts.schemas import (
    Viewpoint, ViewpointDirection, Confidence,
    ExecutionPlan, ApprovalStatus,
)


def _seed_viewpoint(store, direction=ViewpointDirection.BULLISH, confidence=Confidence.MEDIUM):
    store.save(
        Viewpoint(
            ticker="TSLA.US",
            direction=direction,
            confidence=confidence,
            macro_support="有利",
            core_logic="论点稳固",
            counter_arguments=["风险 A", "风险 B"],
            invalidation="交付不及预期",
            valid_until="下次财报",
        ),
        "viewpoints", "TSLA.US",
    )


def test_plan_generates_from_viewpoint(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    artifact_id = stage.generate(ticker="TSLA.US")
    plan = store.load("plans", artifact_id, ExecutionPlan)
    assert plan.ticker == "TSLA.US"
    assert plan.direction == "做多"
    assert plan.approval_status == ApprovalStatus.PENDING


def test_plan_skips_neutral(store):
    _seed_viewpoint(store, direction=ViewpointDirection.NEUTRAL)
    stage = PlanStage(store)
    with pytest.raises(ValueError, match="neutral"):
        stage.generate(ticker="TSLA.US")


def test_plan_skips_low_confidence(store):
    _seed_viewpoint(store, confidence=Confidence.LOW)
    stage = PlanStage(store)
    with pytest.raises(ValueError, match="confidence"):
        stage.generate(ticker="TSLA.US")


def test_plan_approve(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "approve", "看起来不错，开盘时入场")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.APPROVED
    assert plan.approval_notes == "看起来不错，开盘时入场"
    assert plan.approved_at is not None


def test_plan_reject(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "reject", "宏观不确定性太大")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.REJECTED


def test_plan_revise(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "revise", "仓位降至 3%")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.REVISED
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_plan.py -v`
预期：FAIL — `cannot import name 'PlanStage'`

- [ ] **步骤 3：实现计划阶段**

```python
# src/vts/stages/plan.py
"""计划阶段：生成 ExecutionPlan 并支持人工审批流程。"""

from datetime import datetime

from vts.artifacts.schemas import (
    ApprovalStatus, Confidence, ExecutionPlan,
    Viewpoint, ViewpointDirection,
)
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_DIRECTION_MAP = {
    ViewpointDirection.BULLISH: "做多",
    ViewpointDirection.BEARISH: "做空",
}


class PlanStage(Stage):
    """从 Viewpoint 生成 ExecutionPlan 并管理人工审批。"""

    def __init__(self, store: ArtifactStore):
        super().__init__(store)

    def run(self, **kwargs) -> str:
        return self.generate(**kwargs)

    def generate(self, ticker: str) -> str:
        viewpoint = self.store.load("viewpoints", ticker, Viewpoint)

        if viewpoint.direction == ViewpointDirection.NEUTRAL:
            raise ValueError(f"Cannot generate plan for neutral viewpoint on {ticker}")
        if viewpoint.confidence == Confidence.LOW:
            raise ValueError(f"Cannot generate plan: confidence too low for {ticker}")

        direction = _DIRECTION_MAP.get(viewpoint.direction, "观望")

        plan = ExecutionPlan(
            ticker=ticker,
            direction=direction,
            position_pct="5%",
            entry_condition=f"基于: {viewpoint.core_logic}",
            prerequisites=viewpoint.macro_support,
        )

        artifact_id = ticker
        self.store.save(plan, "plans", artifact_id)
        return artifact_id

    def review(self, plan_id: str, action: str, notes: str = "") -> None:
        plan = self.store.load("plans", plan_id, ExecutionPlan)

        status_map = {
            "approve": ApprovalStatus.APPROVED,
            "reject": ApprovalStatus.REJECTED,
            "revise": ApprovalStatus.REVISED,
        }
        if action not in status_map:
            raise ValueError(f"Invalid action: {action}. Use: approve, reject, revise")

        plan.approval_status = status_map[action]
        plan.approval_notes = notes
        if action == "approve":
            plan.approved_at = datetime.now()

        self.store.save(plan, "plans", plan_id)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_plan.py -v`
预期：全部 6 个测试通过

- [ ] **步骤 5：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/stages/plan.py tests/test_plan.py
git commit -m "feat: plan stage — ExecutionPlan generation with approve/reject/revise human gate"
```

---

## 任务 8：CLI 集成与管道编排

**文件：**
- 新建：`src/vts/orchestrator/pipeline.py`
- 修改：`src/vts/cli/main.py`
- 新建：`tests/test_pipeline.py`

- [ ] **步骤 1：编写管道测试**

```python
# tests/test_pipeline.py
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from vts.orchestrator.pipeline import Pipeline
from vts.artifacts.schemas import MacroSnapshot, ResearchBrief, BacktestReport, Viewpoint, ExecutionPlan


@pytest.fixture
def mock_loader_pipeline():
    loader = MagicMock()
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 1.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 250,
        },
        index=dates,
    )
    loader.fetch_macro_indicators.return_value = {
        "treasury_10y": {"latest": 4.28, "data": ohlcv},
        "vix": {"latest": 15.0, "data": ohlcv},
        "dxy": {"latest": 104.0, "data": ohlcv},
        "spy": {"latest": 540.0, "data": ohlcv},
        "qqq": {"latest": 470.0, "data": ohlcv},
        "hyg": {"latest": 78.0, "data": ohlcv},
    }
    loader.compute_ma_status.return_value = {50: True, 200: True}
    loader.fetch_ohlcv.return_value = ohlcv
    return loader


def test_pipeline_research_only(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    result = pipe.run_research()
    assert result is not None
    snapshot = store.load("snapshots", result, MacroSnapshot)
    assert snapshot.vix == 15.0


def test_pipeline_discover(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    result = pipe.run_discover(
        ticker="TSLA.US",
        thesis="测试论点",
        key_evidence=["A", "B"],
        invalidation="失效条件",
    )
    brief = store.load("briefs", result, ResearchBrief)
    assert brief.ticker == "TSLA.US"


def test_pipeline_full_to_viewpoint(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    pipe.run_research()
    pipe.run_discover(
        ticker="TSLA.US", thesis="测试", key_evidence=["A"],
        invalidation="X",
    )

    def signal_fn(data):
        signals = pd.Series(0, index=data.index)
        for i in range(0, len(data) - 20, 30):
            signals.iloc[i] = 1
            signals.iloc[i + 15] = -1
        return signals

    pipe.run_backtest(
        ticker="TSLA.US", rule_name="test", signal_fn=signal_fn,
        start_date="2024-01-01", end_date="2025-01-01",
    )
    vp_id = pipe.run_viewpoint(ticker="TSLA.US")
    vp = store.load("viewpoints", vp_id, Viewpoint)
    assert vp.ticker == "TSLA.US"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_pipeline.py -v`
预期：FAIL — `ModuleNotFoundError`

- [ ] **步骤 3：实现管道编排器**

```python
# src/vts/orchestrator/pipeline.py
"""五阶段投资管道的顺序编排器。"""

from typing import Callable

import pandas as pd

from vts.artifacts.store import ArtifactStore
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.backtest import BacktestStage
from vts.stages.discover import DiscoverStage
from vts.stages.plan import PlanStage
from vts.stages.research import ResearchStage
from vts.stages.viewpoint import ViewpointStage


class Pipeline:
    """使用共享产物存储编排五个管道阶段。"""

    def __init__(self, store: ArtifactStore, loader: YFinanceLoader | None = None):
        self.store = store
        self.loader = loader or YFinanceLoader()

    def run_research(self) -> str:
        stage = ResearchStage(self.store, loader=self.loader)
        return stage.run()

    def run_discover(self, **kwargs) -> str:
        stage = DiscoverStage(self.store)
        return stage.run(**kwargs)

    def run_backtest(self, **kwargs) -> str:
        stage = BacktestStage(self.store, loader=self.loader)
        return stage.run(**kwargs)

    def run_viewpoint(self, **kwargs) -> str:
        stage = ViewpointStage(self.store)
        return stage.run(**kwargs)

    def run_plan(self, **kwargs) -> str:
        stage = PlanStage(self.store)
        return stage.run(**kwargs)

    def review_plan(self, plan_id: str, action: str, notes: str = "") -> None:
        stage = PlanStage(self.store)
        stage.review(plan_id, action, notes)
```

- [ ] **步骤 4：运行管道测试验证通过**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest tests/test_pipeline.py -v`
预期：全部 3 个测试通过

- [ ] **步骤 5：更新 CLI 接入真实实现**

```python
# src/vts/cli/main.py
"""CLI 入口。"""

import json

import click

from vts.artifacts.schemas import (
    BacktestReport, ExecutionPlan, MacroSnapshot, ResearchBrief, Viewpoint,
)
from vts.artifacts.store import ArtifactStore
from vts.orchestrator.pipeline import Pipeline


def _get_pipeline(artifacts_dir: str) -> Pipeline:
    store = ArtifactStore(base_dir=artifacts_dir)
    return Pipeline(store)


@click.group()
@click.version_option(package_name="vibe-trading-system")
@click.option("--artifacts-dir", default="artifacts", help="产物存储目录")
@click.pass_context
def cli(ctx, artifacts_dir):
    """vts — 五阶段美股投资自动化管道。"""
    ctx.ensure_object(dict)
    ctx.obj["artifacts_dir"] = artifacts_dir


@cli.command()
@click.pass_context
def research(ctx):
    """运行研究阶段：获取宏观指标并生成 MacroSnapshot。"""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    artifact_id = pipe.run_research()
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    click.echo(f"MacroSnapshot 已保存: {artifact_id}")
    click.echo(f"  立场: {snapshot.stance.value}")
    click.echo(f"  VIX: {snapshot.vix}")
    click.echo(f"  10 年期国债: {snapshot.treasury_10y}")


@cli.command()
@click.argument("ticker")
@click.option("--thesis", prompt=True, help="一句话投资论点")
@click.option("--evidence", prompt=True, help="关键证据（逗号分隔，最多 3 项）")
@click.option("--invalidation", prompt=True, help="论点失效条件")
@click.option("--next-action", default="继续研究", help="继续研究/决策挑战/回测 setup/放弃")
@click.pass_context
def discover(ctx, ticker, thesis, evidence, invalidation, next_action):
    """运行发现阶段：为 TICKER 创建 ResearchBrief。"""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    evidence_list = [e.strip() for e in evidence.split(",")]
    artifact_id = pipe.run_discover(
        ticker=ticker, thesis=thesis, key_evidence=evidence_list,
        invalidation=invalidation, next_action=next_action,
    )
    click.echo(f"ResearchBrief 已保存: {artifact_id}")


@cli.command()
@click.argument("ticker")
@click.pass_context
def viewpoint(ctx, ticker):
    """运行观点阶段：为 TICKER 综合全面观点。"""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    artifact_id = pipe.run_viewpoint(ticker=ticker)
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    vp = store.load("viewpoints", artifact_id, Viewpoint)
    click.echo(f"Viewpoint 已保存: {artifact_id}")
    click.echo(f"  方向: {vp.direction.value}")
    click.echo(f"  置信度: {vp.confidence.value}")
    click.echo(f"  反方论点: {len(vp.counter_arguments)} 条")


@cli.command()
@click.argument("ticker")
@click.pass_context
def plan(ctx, ticker):
    """为 TICKER 生成 ExecutionPlan（需要 Viewpoint）。"""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    try:
        artifact_id = pipe.run_plan(ticker=ticker)
        store = ArtifactStore(ctx.obj["artifacts_dir"])
        ep = store.load("plans", artifact_id, ExecutionPlan)
        click.echo(f"ExecutionPlan 已保存: {artifact_id}")
        click.echo(f"  方向: {ep.direction}")
        click.echo(f"  状态: {ep.approval_status.value}")
    except ValueError as e:
        click.echo(f"无法生成计划: {e}", err=True)


@cli.command()
@click.argument("plan_id")
@click.argument("action", type=click.Choice(["approve", "reject", "revise"]))
@click.option("--notes", default="", help="审批备注")
@click.pass_context
def review(ctx, plan_id, action, notes):
    """审批 ExecutionPlan：批准、拒绝或修改。"""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    pipe.review_plan(plan_id, action, notes)
    click.echo(f"计划 {plan_id} → {action}")


@cli.command()
@click.pass_context
def status(ctx):
    """显示当前产物计数和最新快照立场。"""
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    click.echo("产物计数:")
    for atype in ["snapshots", "briefs", "reports", "viewpoints", "plans"]:
        ids = store.list_ids(atype)
        click.echo(f"  {atype}: {len(ids)}")
    latest = store.latest("snapshots", MacroSnapshot)
    if latest:
        click.echo(f"\n最新宏观立场: {latest.stance.value}（{latest.date}）")
```

- [ ] **步骤 6：运行全部测试**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pytest -v`
预期：全部测试通过（store: 7, loader: 5, research: 4, discover: 4, engine: 4, backtest: 2, viewpoint: 4, plan: 6, pipeline: 3 = 约 39 个）

- [ ] **步骤 7：验证 CLI 可用**

运行：`cd /Users/jianjustin/workspaces/vibe-trading-system && pip install -e . && vts --help`
预期：显示所有命令（research, discover, viewpoint, plan, review, status）

- [ ] **步骤 8：提交**

```bash
cd /Users/jianjustin/workspaces/vibe-trading-system
git add src/vts/orchestrator/pipeline.py src/vts/cli/main.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestrator + CLI integration for all five stages"
```

---

## 自检清单

- [x] **规格覆盖：** 全部 5 个阶段已实现（研究/发现/回测/观点/计划）+ 产物存储 + 数据加载器 + CLI + 编排器
- [x] **占位符扫描：** 无 TBD/TODO — 所有代码完整
- [x] **类型一致性：** schemas.py 类型在所有阶段间保持一致；ArtifactStore 接口统一
- [x] **独立可测试性：** 每个阶段测试使用 fixture/mock，无跨阶段测试依赖
- [x] **人工审批门：** PlanStage.review() 实现了批准/拒绝/修改并持久化
