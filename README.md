# market-watcher

Market Watcher collects a small set of market metrics and notifies the
repository owner via GitHub Issues when there is output (runs only during
US market hours). This repo contains a Python script that queries Yahoo
Finance and a GitHub Actions workflow that runs on push and on a schedule.

**Files added**
- `scripts/market_watcher.py`: the monitoring script
- `config.yaml`: simple mapping of friendly labels → Yahoo tickers
- `requirements.txt`: Python deps
- `.github/workflows/market-watcher.yml`: GitHub Actions workflow

**Behavior**
- The Python script checks if the US equities market is open (Eastern
	Time 09:30–16:00 Mon–Fri). If the market is closed (including before
	open), the script produces no output.
- When open, the script reports for each configured symbol:
	- current value
	- percent change for the day vs previous close
	- drawdown since market open (percent below the intraday high)
	- drawdown in the previous hour
- The workflow runs on every push to `main` and every 15 minutes between
	13:00–22:59 UTC (this broad window covers daylight-saving transitions
	for US market hours). If the script produced output, the workflow
	creates a GitHub Issue titled `Market Watcher: update` containing the
	script output (this generates a native GitHub notification to repo
	watchers/owner).

Usage
-----

1. Edit `config.yaml` to add/remove the tickers you want monitored. Keys
	 are friendly labels and values are Yahoo Finance tickers.

2. Commit changes to `main` or wait for the scheduled run window. The
	 workflow will execute the script and create an issue if there is any
	 output.

Running locally
---------------
Create a virtualenv, install deps and run the script:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/market_watcher.py
```

Notes and customization
-----------------------
- To change the market open/close logic, edit `market_is_open` in
	`scripts/market_watcher.py`.
- The workflow creates an issue for every run that produces output. If
	you'd rather not create issues so frequently, modify the workflow to
	use another notification channel (email via external service, Slack,
	or aggregate state and only alert on thresholds).

If you'd like, I can:
- Add unit tests around the parsing/analysis functions
- Limit issue creation frequency (dedupe or update an existing issue)
- Add thresholds so only significant moves create notifications

