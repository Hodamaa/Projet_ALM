import numpy as np

from alm_engine.risk.internal_scenarios import apply_internal_scenario, internal_icaap_scenarios


def test_internal_scenarios_count():
    assert len(internal_icaap_scenarios()) == 3


def test_internal_scenario_preserves_non_negative_rates():
    base = np.full(24, 0.015)
    mats = np.arange(1, 25) / 12
    scen = internal_icaap_scenarios()[0]
    shocked = apply_internal_scenario(base, mats, scen)
    assert np.all(shocked >= 0.0)
