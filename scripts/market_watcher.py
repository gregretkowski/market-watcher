#!/usr/bin/env python3
"""Market watcher script.

Reads `config.yaml` for the tickers to monitor and prints a short report
only when US markets are open (Eastern Time 09:30-16:00 local US market hours).

Outputs plain text suitable for creating an issue or other notification.
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
import zoneinfo
import yaml
import yfinance as yf
from pathlib import Path


DEFAULT_CONFIG = {
    "markets": {
        "S&P 500": "^GSPC",
        "NASDAQ 100": "^NDX",
        "Russell 2000": "^RUT",
        "10Y Treasury": "^TNX",
        "Crude Oil": "CL=F",
    }
}


def load_config(path: Path) -> dict:
    if not path.exists():
        return DEFAULT_CONFIG
    with path.open() as f:
        return yaml.safe_load(f) or DEFAULT_CONFIG


def market_is_open(now: datetime) -> bool:
    # US equities market hours in Eastern Time: 09:30 - 16:00, Mon-Fri
    if now.weekday() >= 5:
        return False
    open_time = time(9, 30)
    close_time = time(16, 0)
    return open_time <= now.time() <= close_time


def fmt_pct(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.2f}%"


def analyze_ticker(symbol: str, now_utc: datetime) -> str:
    t = yf.Ticker(symbol)
    # Get minute-level data for today
    try:
        hist = t.history(period="1d", interval="1m", auto_adjust=False, actions=False)
    except Exception:
        return f"{symbol}: error fetching data"

    if hist.empty:
        return f"{symbol}: no intraday data"

    # Ensure index is timezone-aware UTC
    idx = hist.index
    if idx.tz is None:
        hist.index = hist.index.tz_localize("UTC")

    # Most recent close
    current = hist["Close"].dropna()
    if current.empty:
        return f"{symbol}: no price points"
    last_price = float(current.iloc[-1])

    # previous close (yesterday)
    prev_close = None
    try:
        info = t.get_info()
        prev_close = info.get("previousClose")
    except Exception:
        prev_close = None
    if prev_close is None:
        # fallback: use earliest value from previous day if available
        prev = t.history(period="2d", interval="1d")
        if not prev.empty and "Close" in prev.columns and len(prev) >= 2:
            prev_close = float(prev["Close"].iloc[0])

    pct_change = None
    if prev_close:
        pct_change = (last_price - float(prev_close)) / float(prev_close) * 100.0

    # Drawdown since market open: compare against max close since start of day
    highs = hist["Close"].dropna()
    high_since_open = float(highs.max()) if not highs.empty else None
    drawdown_since_open = None
    if high_since_open and high_since_open > 0:
        drawdown_since_open = (last_price - high_since_open) / high_since_open * 100.0

    # Drawdown in previous hour
    now = now_utc
    one_hour_ago = now - timedelta(hours=1)
    last_hour = hist[hist.index >= one_hour_ago]
    drawdown_prev_hour = None
    if not last_hour.empty:
        try:
            high_last_hour = float(last_hour["Close"].max())
            if high_last_hour > 0:
                drawdown_prev_hour = (last_price - high_last_hour) / high_last_hour * 100.0
        except Exception:
            drawdown_prev_hour = None

    parts = [f"{symbol}: {last_price:.2f}"]
    if pct_change is not None:
        parts.append(f"day: {fmt_pct(pct_change)}")
    else:
        parts.append("day: n/a")
    parts.append(f"drawdown_since_open: {fmt_pct(drawdown_since_open)}")
    parts.append(f"drawdown_prev_hour: {fmt_pct(drawdown_prev_hour)}")
    return " | ".join(parts)


def main() -> int:
    cfg = load_config(Path(__file__).parent.parent / "config.yaml")

    # Current time in New York to check market hours
    try:
        tz = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        tz = zoneinfo.ZoneInfo("US/Eastern")
    now_et = datetime.now(tz)
    if not market_is_open(now_et):
        # Do not output anything if market is closed or before open
        return 0

    now_utc = datetime.now(zoneinfo.ZoneInfo("UTC"))

    markets = cfg.get("markets", {})
    if not markets:
        markets = DEFAULT_CONFIG["markets"]

    lines = []
    for label, symbol in markets.items():
        res = analyze_ticker(symbol, now_utc)
        lines.append(f"{label}: {res}")

    output = "\n".join(lines)
    if output.strip():
        print(output)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
