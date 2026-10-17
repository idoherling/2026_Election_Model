"""Bayesian stacking of error-stack variants (dossier s.62): the optimiser,
the scores, and the production flag (bayes_model.ERROR_STACK)."""
from __future__ import annotations

import numpy as np
import pytest

import bayes_model as bm
import stacking as st
from test_projection import synthetic_data, synthetic_posterior




@pytest.fixture(autouse=True)
def _stack_base(monkeypatch):
    """The s.62 stack owns the residual line and t scaling, and was built on
    the pre-18-Oct line ("seat"). Production ships "seat_fix" since s.62.5,
    so these tests pin the stack's own base explicitly."""
    import bayes_model as _bm
    monkeypatch.setattr(_bm, "RESID_SPACE", "seat")
    monkeypatch.setattr(_bm, "T_UNIT_VAR", False)

def _components(n_out=40):
    """Three overlapping discrete predictive distributions on 0..n_out-1."""
    x = np.arange(n_out)
    comps = []
    for mu, sd in ((10, 3.0), (18, 4.0), (26, 2.5)):
        p = np.exp(-0.5 * ((x - mu) / sd) ** 2)
        comps.append(p / p.sum())
    return np.array(comps)          # (K, n_out)


@pytest.mark.parametrize("truth", [(0.5, 0.3, 0.2), (0.15, 0.6, 0.25), (0.8, 0.0, 0.2)])
def test_stacking_recovers_known_weights(truth):
    """Outcomes drawn from a known mixture of the candidates: the stacking
    weights (the mixture-weight MLE) recover the mixing weights."""
    rng = np.random.default_rng(3)
    C = _components()
    truth = np.array(truth)
    n = 40000
    k = rng.choice(len(truth), size=n, p=truth)
    y = np.array([rng.choice(C.shape[1], p=C[j]) for j in k])
    P = np.maximum(C[:, y].T, st.EPS)          # (n, K): each candidate's pmf at the outcome
    w = st.stack_weights(P)
    assert np.isclose(w.sum(), 1.0)
    assert (w >= 0).all()
    assert np.abs(w - truth).max() < 0.03
    # the EM fixed point agrees with BFGS on the concave objective
    w_em = st.stack_weights_em(P)
    assert np.abs(w - w_em).max() < 5e-3
    assert st.stack_objective(w, P) >= st.stack_objective(w_em, P) - 1e-9


def test_stacking_weights_on_simplex_and_mixture_beats_components():
    """Weights sum to one and are non-negative; when the truth is a mixture,
    the stacked score beats every single candidate."""
    rng = np.random.default_rng(11)
    C = _components()
    k = rng.choice(3, size=5000, p=[0.4, 0.4, 0.2])
    y = np.array([rng.choice(C.shape[1], p=C[j]) for j in k])
    P = np.maximum(C[:, y].T, st.EPS)
    a = rng.uniform(0.5, 1.5, len(y))          # observation weights are honoured
    w = st.stack_weights(P, a)
    assert np.isclose(w.sum(), 1.0, atol=1e-12)
    assert (w >= 0).all()
    best_single = max(st.stack_objective(np.eye(3)[j], P, a) for j in range(3))
    assert st.stack_objective(w, P, a) > best_single


def test_stacking_puts_weight_on_the_true_candidate():
    """A candidate that is the data-generating distribution takes (almost)
    all the weight against two wrong ones."""
    rng = np.random.default_rng(5)
    C = _components()
    y = rng.choice(C.shape[1], size=20000, p=C[1])
    w = st.stack_weights(np.maximum(C[:, y].T, st.EPS))
    assert w[1] > 0.97 and np.isclose(w.sum(), 1.0)


def test_round_weights_production_form():
    r = st.round_weights([0.33333, 0.33333, 0.33334, 0.0002, 0.0], st.ARMS)
    assert np.isclose(sum(r.values()), 1.0, atol=1e-12)
    assert set(r) == {"shipped", "cal_A", "cal_B"}      # arms that round to zero drop out
    assert all(round(v, 3) == v for v in r.values())


def test_scores_on_a_known_sample():
    seats = np.array([[0, 5], [0, 5], [4, 6], [4, 7]])
    actual = np.array([4, 5])
    mask = np.array([True, True])
    # p(4) = .5 for list 0, p(5) = .5 for list 1
    assert np.isclose(st.log_score(seats, actual, mask), 2 * np.log(0.5))
    # a realised count no draw produced scores the floor
    assert np.isclose(st.log_score(seats, np.array([9, 5]), mask), np.log(st.EPS) + np.log(0.5))
    # discrete CRPS of a point mass at the outcome is zero
    F = st.cdf_matrix(np.array([[3, 7]] * 4))
    assert st.crps_from_cdf(F, np.array([3, 7]), mask) == 0.0
    # and one seat off costs exactly 1 per list
    assert st.crps_from_cdf(F, np.array([4, 6]), mask) == 2.0


def test_error_stack_assign_leaves_parent_stream():
    rng = np.random.default_rng(42)
    names, arm = bm.error_stack_assign(rng, {"shipped": 0.5, "cal_B": 0.5}, 1000)
    assert names == ["shipped", "cal_B"]
    # the parent generator was neither read nor advanced
    assert (rng.standard_normal(5) == np.random.default_rng(42).standard_normal(5)).all()
    # same seed, same assignment
    _, arm2 = bm.error_stack_assign(np.random.default_rng(42), {"shipped": 0.5, "cal_B": 0.5}, 1000)
    assert (arm == arm2).all() and 0.4 < arm.mean() < 0.6
    with pytest.raises(ValueError):
        bm.error_stack_assign(rng, {"shipped": 0.7, "cal_B": 0.7}, 10)
    with pytest.raises(ValueError):
        bm.error_stack_assign(rng, {"CBfix": 1.0}, 10)


def _project(monkeypatch, **flags):
    monkeypatch.setattr(bm, "N_PROJ", 1000)
    for k, v in flags.items():
        monkeypatch.setattr(bm, k, v)
    return bm.project(synthetic_data(), synthetic_posterior(), np.random.default_rng(bm.SEED))[0]


def test_error_stack_shipped_value_is_none():
    assert bm.ERROR_STACK is None
    assert set(bm.ERROR_STACK_ARMS) == set(st.ARMS)
    # the recorded (not shipped) s.62 production weights are a valid stack
    w = bm.ERROR_STACK_WEIGHTS
    assert set(w) <= set(st.ARMS) and np.isclose(sum(w.values()), 1.0, atol=1e-12)
    bm.error_stack_assign(np.random.default_rng(0), w, 10)


@pytest.mark.parametrize("arm,flags", [("shipped", {}), ("cal_A", {"T_UNIT_VAR": True}),
                                       ("cal_B", {"RESID_SPACE": "vote"}),
                                       ("resid_hybrid", {"RESID_SPACE": "hybrid"}),
                                       ("Bfix", {"RESID_SPACE": "seat_fix"})])
def test_single_arm_stack_reproduces_the_arm(monkeypatch, capsys, arm, flags):
    """ERROR_STACK = {arm: 1} gives the arm's own flags' draws bit for bit:
    the variant path uses the same expressions, and the variant generator
    leaves the parent stream alone."""
    want = _project(monkeypatch, **flags)
    for k in flags:   # back to shipped before the stack run
        monkeypatch.setattr(bm, k, {"T_UNIT_VAR": False, "RESID_SPACE": "seat"}[k])
    got = _project(monkeypatch, ERROR_STACK={arm: 1.0})
    assert (got == want).all()


def test_error_stack_mixture_projects(monkeypatch, capsys):
    w = {"shipped": 0.4, "cal_A": 0.1, "cal_B": 0.3, "resid_hybrid": 0.1, "Bfix": 0.1}
    seats = _project(monkeypatch, ERROR_STACK=w)
    assert (seats.sum(axis=1) == 120).all()
    frac = bm.project.last_error_stack
    assert set(frac) == set(w) and all(abs(frac[a] - w[a]) < 0.05 for a in w)
    # the stack owns the residual line: a second flag on the same axis is an error
    monkeypatch.setattr(bm, "RESID_SPACE", "vote")
    with pytest.raises(ValueError):
        bm.project(synthetic_data(), synthetic_posterior(), np.random.default_rng(1))
