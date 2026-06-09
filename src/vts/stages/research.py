"""Research stage: fetch macro indicators and produce MacroSnapshot artifacts."""

from datetime import date

from vts.artifacts.schemas import MacroSnapshot, MarketStance
from vts.artifacts.store import ArtifactStore
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.base import Stage


class ResearchStage(Stage):
    """Fetch macro indicators, determine market stance, save MacroSnapshot."""

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
