from alm_engine.instruments.fixed_rate_loan import FixedRateLoan


def test_fixed_rate_cashflows_positive_and_wal_reasonable():
    loan = FixedRateLoan(notional=1_000_000, annual_rate=0.03, maturity_years=20, cpr=0.06)
    cfs = loan.cashflows()
    assert not cfs.empty
    assert cfs["cashflow"].sum() > 0
    wal = loan.wal()
    assert 0 < wal < 20


def test_higher_cpr_reduces_wal():
    low = FixedRateLoan(notional=1_000_000, annual_rate=0.03, maturity_years=20, cpr=0.01)
    high = FixedRateLoan(notional=1_000_000, annual_rate=0.03, maturity_years=20, cpr=0.20)
    assert high.wal() < low.wal()

