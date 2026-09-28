from alm_engine.engine import run_engine
from alm_engine.risk.hedge_optimizer import optimize_hedge_notional


def test_optimize_hedge_returns_grid_value():
    res = optimize_hedge_notional(
        run_engine,
        tier1_capital=120_000_000.0,
        cpr=0.06,
        include_internal_scenarios=True,
        search_min=0.0,
        search_max=30_000_000.0,
        step=10_000_000.0,
    )
    assert res.optimal_notional in {0.0, 10_000_000.0, 20_000_000.0, 30_000_000.0}
    assert res.objective_value >= 0.0
    assert isinstance(res.best_scenario, str)

