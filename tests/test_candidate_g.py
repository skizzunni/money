"""Candidate G (docs/CANDIDATE_G.md): a stop wider than the $125 budget moved in to the widest affordable distance,
hand-computed. The NinjaScript's StopFit agrees with the Python model on MNQ (tests/test_candidate_d.py)."""
from __future__ import annotations

import pytest

from mnqbot.candidate_d import PV, TICK, DConfig, fit_stop, max_r, sweep_prices


def planned(cfg: DConfig, r: float, allowance: int) -> float:
    return cfg.qty * (r * PV + 2 * cfg.commission + allowance * TICK * PV)


def test_max_r_is_the_widest_affordable_distance():
    cfg = DConfig()
    # (62.50 - 1.90 - 2.00) / 2 = 29.30 -> 29.25; (62.50 - 1.90 - 1.00) / 2 = 29.80 -> 29.75
    assert max_r(cfg, cfg.allowance_market) == 29.25
    assert max_r(cfg, cfg.allowance_limit) == 29.75
    assert planned(cfg, 29.25, 4) == pytest.approx(124.80)
    assert planned(cfg, 29.50, 4) > 125


@pytest.mark.parametrize("d", [1, -1])
def test_cap_moves_a_wide_stop_in_and_keeps_a_tight_one(d):
    cfg = DConfig(stop_fit="cap")
    assert fit_stop(d, 20000.0, 20000.0 - d * 100, cfg, 4) == 20000.0 - d * 29.25
    assert fit_stop(d, 20000.0, 20000.0 - d * 12.5, cfg, 4) == 20000.0 - d * 12.5


@pytest.mark.parametrize("d", [1, -1])
def test_budget_always_uses_the_budget_distance(d):
    cfg = DConfig(stop_fit="budget")
    assert fit_stop(d, 20000.0, 20000.0 - d * 12.5, cfg, 4) == 20000.0 - d * 29.25
    assert fit_stop(d, 20000.0, 20000.0 - d * 100, cfg, 4) == 20000.0 - d * 29.25


def test_skip_leaves_the_stop_alone():
    assert fit_stop(1, 20000.0, 19900.0, DConfig(), 4) == 19900.0


@pytest.mark.parametrize("d", [1, -1])
def test_off_grid_entry_rounds_toward_it_so_the_budget_holds(d):
    """Rescaled NQ closes are off the grid: the fitted stop rounds toward the entry, R just under 29.25."""
    cfg = DConfig(stop_fit="cap")
    c = 20000.10 if d > 0 else 19999.90
    stop = fit_stop(d, c, c - d * 80, cfg, 4)
    assert stop == (19971.00 if d > 0 else 20029.00)
    r = d * (c - stop)
    assert r == pytest.approx(29.10) and planned(cfg, r, 4) <= 125


@pytest.mark.parametrize("d", [1, -1])
def test_sweep_limit_stop_capped_at_29_75(d):
    cfg = DConfig(stop_fit="cap", e_stop="fvg")
    dec = {"d": d, "limit_raw": 20000.0, "far_raw": 20000.0 - d * 60, "extreme_raw": 20000.0 - d * 90, "atr_raw": 10.0}
    lim, stop, r, plan = sweep_prices(dec, 1.0, cfg)
    assert (lim, stop, r) == (20000.0, 20000.0 - d * 29.75, 29.75)
    assert plan == pytest.approx(2 * (29.75 * 2 + 1.90 + 1.00)) and plan <= 125
    # the far edge 20 points away is affordable: unchanged (+2 ticks)
    dec["far_raw"] = 20000.0 - d * 20
    assert sweep_prices(dec, 1.0, cfg)[2] == 20.5
