"""Crowd simulation, levels and forecasting model (STORY-002 to STORY-007)."""
import datetime as dt

import numpy as np
import pytest

from app.services import crowd, crowd_sim, forecast

FALLS = dict(key="falls", category="waterfall", capacity=900, popularity=1.2, open_hour=8, close_hour=19,
             covered=False, sensitive=False, best_months=[10, 11, 12, 1, 2], climate="mountain")
FRAGILE = dict(FALLS, key="fragile", sensitive=True, capacity=120, popularity=0.6)
MUSEUM = dict(key="museum", category="museum", capacity=250, popularity=0.4, open_hour=10, close_hour=17,
              covered=True, sensitive=False, best_months=[10, 11, 12, 1, 2], climate="plains")


# ---------------------------------------------------------------- levels
@pytest.mark.parametrize("util,level", [(0.10, "Low"), (0.45, "Moderate"), (0.80, "High"), (0.95, "At Capacity")])
def test_level_of_uses_standard_thresholds(util, level):
    assert crowd.level_of(util, sensitive=False) == level


def test_sensitive_sites_use_stricter_thresholds():
    assert crowd.level_of(0.45, sensitive=False) == "Moderate"
    assert crowd.level_of(0.45, sensitive=True) == "Moderate"
    assert crowd.level_of(0.60, sensitive=True) == "High"
    assert crowd.level_of(0.75, sensitive=True) == "At Capacity"


def test_p_exceed_rises_with_predicted_utilisation():
    lo = crowd.p_exceed(0.4, sensitive=False, sigma=0.12)
    hi = crowd.p_exceed(0.95, sensitive=False, sigma=0.12)
    assert 0 <= lo < 0.05 < 0.5 < hi <= 1


# ---------------------------------------------------------------- simulation
def test_simulated_counts_are_zero_when_closed_and_deterministic():
    d = dt.date(2026, 11, 14)
    a = crowd_sim.counts([FALLS], [d])
    b = crowd_sim.counts([FALLS], [d])
    assert a.equals(b)
    assert set(a["hour"]) == set(range(8, 19))  # only open hours are produced
    assert (a["count"] >= 0).all()


def test_simulated_weekends_and_season_are_busier():
    sat, wed = dt.date(2026, 11, 14), dt.date(2026, 11, 11)
    off_sat = dt.date(2026, 7, 11)  # July: off-season monsoon for this falls
    c = crowd_sim.counts([FALLS], [sat, wed, off_sat]).groupby("date")["count"].sum()
    assert c[sat] > 1.3 * c[wed]
    assert c[sat] > 1.3 * c[off_sat]


def test_simulated_peak_hour_matches_category_profile():
    d = dt.date(2026, 11, 14)
    c = crowd_sim.counts([FALLS, MUSEUM], [d])
    falls_peak = c[c.key == "falls"].sort_values("count").iloc[-1]["hour"]
    assert 13 <= falls_peak <= 17  # waterfalls peak in the afternoon


# ---------------------------------------------------------------- model
@pytest.fixture(scope="module")
def trained():
    m = forecast.CrowdModel()
    info = m.train([FALLS, FRAGILE, MUSEUM], end_date=dt.date(2026, 11, 1), days=150)
    return m, info


def test_training_uses_chronological_train_validation_test_split(trained):
    _, info = trained
    s = info["split"]
    assert s["train_end"] < s["val_start"] <= s["val_end"] < s["test_start"] <= s["test_end"]
    assert info["rows"]["train"] > info["rows"]["validation"] > 0 and info["rows"]["test"] > 0


def test_model_beats_both_baselines_on_held_out_test_period(trained):
    _, info = trained
    mape = info["test_metrics"]["mape"]
    assert mape < info["baselines"]["seasonal_naive"]["mape"]
    assert mape < info["baselines"]["weekday_hour_mean"]["mape"]
    assert info["data_provenance"] == "demonstration"


def test_predict_returns_one_utilisation_per_requested_hour(trained):
    m, _ = trained
    rows = [(FALLS, dt.date(2026, 11, 14), h, 0.0) for h in range(8, 19)]
    u = m.predict_util(rows)
    assert u.shape == (11,)
    assert np.all(u >= 0)


def test_model_round_trips_through_disk(trained, tmp_path):
    m, _ = trained
    m.save(tmp_path)
    m2 = forecast.CrowdModel.load(tmp_path)
    rows = [(MUSEUM, dt.date(2026, 11, 14), 12, 0.0)]
    assert m2.predict_util(rows)[0] == pytest.approx(m.predict_util(rows)[0])


# ---------------------------------------------------------------- forecast helpers
def test_day_forecast_has_levels_and_uncertainty_band(trained):
    m, _ = trained
    day = crowd.day_forecast(m, FALLS, dt.date(2026, 11, 14))
    assert [h["hour"] for h in day] == list(range(8, 19))
    for h in day:
        assert h["level"] in crowd.LEVELS
        assert h["low"] <= h["visitors"] <= h["high"]


def test_best_times_returns_quietest_slots_first(trained):
    m, _ = trained
    best = crowd.best_times(m, FALLS, dt.date(2026, 11, 9), days=7, n=3)
    assert len(best) == 3
    utils = [b["util"] for b in best]
    assert utils == sorted(utils)


def test_traveller_reports_pull_the_live_estimate_towards_reported_level():
    est = crowd.blend_reports(0.30, ["packed", "packed", "packed"])
    assert est["util"] > 0.6 and est["reports"] == 3
    assert crowd.blend_reports(0.30, [])["util"] == 0.30
