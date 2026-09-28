import numpy as np

from alm_engine.risk.irrbb_scenarios import apply_shock, standard_irrbb_scenarios


def test_standard_scenarios_count_is_six():
    scenarios = standard_irrbb_scenarios()
    assert len(scenarios) == 6


def test_parallel_up_increases_curve():
    base = np.full(12, 0.02)
    mats = np.arange(1, 13) / 12
    up = [s for s in standard_irrbb_scenarios() if s.name == "Parallel Up"][0]
    shocked = apply_shock(base, mats, up)
    assert np.all(shocked >= base)


def test_parallel_down_floor_zero():
    base = np.full(12, 0.005)
    mats = np.arange(1, 13) / 12
    down = [s for s in standard_irrbb_scenarios() if s.name == "Parallel Down"][0]
    shocked = apply_shock(base, mats, down)
    assert np.all(shocked >= 0.0)

