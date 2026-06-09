"""Viewpoint stage: synthesize upstream artifacts into a Viewpoint."""

from vts.artifacts.schemas import (
    BacktestReport, Confidence, MacroSnapshot, MarketStance,
    ResearchBrief, Viewpoint, ViewpointDirection,
)
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_POSITIVE_CONCLUSIONS = {"小仓位验证", "模拟观察"}
_NEGATIVE_CONCLUSIONS = {"放弃"}


class ViewpointStage(Stage):
    """Synthesize MacroSnapshot + ResearchBrief + BacktestReport into a Viewpoint."""

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
            core_logic=f"{brief.thesis} — backtest: {bt_report.conclusion if bt_report else 'N/A'}",
            supporting_evidence="; ".join(brief.key_evidence),
            counter_arguments=counter_args,
            invalidation=brief.invalidation,
            valid_until="Next catalyst or macro shift",
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
            return "No macro data available"
        return f"Market stance: {snapshot.stance.value}, VIX: {snapshot.vix}"

    def _generate_counter_arguments(
        self, brief: ResearchBrief, snapshot: MacroSnapshot | None
    ) -> list[str]:
        args = []
        if brief.invalidation:
            args.append(f"Invalidation risk: {brief.invalidation}")
        if snapshot and snapshot.stance == MarketStance.DEFENSIVE:
            args.append("Macro environment is defensive — risk-off")
        if not args:
            args.append("Limited historical data for robust conclusion")
        return args
