"""Basic backtest metrics: win rate, P&L ratio, max drawdown."""


def calc_metrics(trades: list[dict]) -> dict:
    """Calculate summary statistics from a list of trade dicts with 'pnl_pct' key."""
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
