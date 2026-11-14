# Rebuilding the research data in a new container

The G-series runs (docs/NINJATRADER_V38.md) read a data folder that is not in the repository: the pickles are too big
and the MNQ exports are the user's. On 2026-11-14 the container that held it could not be restarted, so the folder is
rebuilt with `tools/rebuild_data.py`:

```bash
python tools/rebuild_data.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
```

| Input | Source | Built from it |
|---|---|---|
| NQ futures 1-minute, 2015-2025 | Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet` (MIT), downloaded by the script | `nq1m_scaled.pkl`, `nq5m_scaled.pkl` |
| Nasdaq-100 index 1-minute, Nov 2010-2026 | HistData.com: ASCII → 1-Minute Bar Quotes → NSXUSD, the yearly zips 2010-2025 and the 2026 monthly zips, put in `<data dir>/histdata_raw/` by hand | `bars5_scaled.pkl` |
| The user's MNQ bars | NinjaTrader exports `MNQ_09-26.Last.txt`, `MNQ_12-26.Last.txt` | `proxy_5m.pkl`, `proxy_30m.pkl` (with NQ and the index) |
| U48, the runs' base settings | `tests/test_ninjatrader_v38.py`'s Funded growth with U58, G473 and G511 taken back out | `u48_JS.json` (the old `g247_JS.json`) |

**Check before any new test:** rerun G519 (the script prints the command). Its Funded growth rows must match
`verification/noise_v2/g519_growth_time_stop.txt` exactly (fresh 16 starts: 18.8% / $7,557.66; development 31:
19.4% / $10,586.92; unseen 64: 40.6% / $16,740.83). The result of that check is recorded here.

**Status (2026-11-14):** NQ and `u48_JS.json` rebuilt; waiting for the HistData NSXUSD zips and the two MNQ exports.
