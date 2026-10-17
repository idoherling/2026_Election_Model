"""src/pipeline.py: step order, stop-on-failure, logging, refresh handling.

No model code runs here: Pipeline.run is replaced by a recorder, or pointed
at tiny throwaway scripts.
"""
from __future__ import annotations

import pytest

import pipeline as pl

ALL_STEPS = ["scrape_polls", "scrape_cec", "bayes_model", *pl.CHAIN, *pl.SITE_STEPS]


@pytest.fixture
def recorder(monkeypatch, tmp_path):
    """Replace Pipeline.run with a recorder; fail the step named in .fail."""
    calls = []

    class Rec:
        fail = None
        env = {}

    def fake_run(self, name, script, args=(), env=None):
        if name in self.skip:
            self.timings.append((name, 0.0, "skipped"))
            return
        calls.append(name)
        Rec.env[name] = env or {}
        if name == Rec.fail:
            raise pl.StepFailed(f"{name} exited with code 1")
        self.timings.append((name, 0.0, "ok"))

    monkeypatch.setattr(pl.Pipeline, "run", fake_run)
    monkeypatch.setattr(pl, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(pl, "step_checks", lambda p: calls.append("checks"))
    monkeypatch.setattr(pl, "step_tests", lambda p: calls.append("tests"))
    monkeypatch.setattr(pl, "write_publish_copy", lambda p: calls.append("publish_copy"))
    monkeypatch.setattr(pl, "step_refresh", lambda p, stamp: (p.run("scrape_polls", "scrape_polls.py"),
                                                              p.run("scrape_cec", "scrape_cec.py")))
    monkeypatch.setattr(pl, "headline", lambda: "HEADLINE")
    nc = tmp_path / "m3_idata.nc"
    nc.write_bytes(b"x")
    monkeypatch.setattr(pl, "PROCESSED", tmp_path)
    Rec.calls = calls
    return Rec


def test_full_run_order(recorder):
    assert pl.main(["--refresh", "--project-only", "--publish-check"]) == 0
    assert recorder.calls == ALL_STEPS + ["checks", "tests", "publish_copy"]
    assert recorder.env["bayes_model"] == {"BAYES_PROJECT_ONLY": "1"}


def test_default_run_skips_refresh_and_model(recorder):
    assert pl.main([]) == 0
    assert recorder.calls == [*pl.CHAIN, *pl.SITE_STEPS, "checks"]


def test_stops_at_the_first_failure(recorder, tmp_path, capsys):
    recorder.fail = "build_sources"
    assert pl.main(["--project-only"]) == 1
    assert recorder.calls[-1] == "build_sources"
    assert "build_decision_log" not in recorder.calls and "checks" not in recorder.calls
    out = capsys.readouterr().out
    assert "PIPELINE FAILED: build_sources exited with code 1" in out
    logs = list((tmp_path / "logs").glob("pipeline_*.log"))
    assert len(logs) == 1 and "PIPELINE FAILED" in logs[0].read_text()


def test_skip_is_honoured_and_logged(recorder, tmp_path):
    assert pl.main(["--skip", "build_sources", "--skip", "kalpi_model"]) == 0
    assert "build_sources" not in recorder.calls and "kalpi_model" not in recorder.calls
    log = next((tmp_path / "logs").glob("pipeline_*.log")).read_text()
    assert "WARNING skipping: build_sources, kalpi_model" in log


def test_refit_and_project_only_are_exclusive():
    with pytest.raises(SystemExit):
        pl.main(["--refit", "--project-only"])


def test_project_only_needs_the_saved_posterior(recorder, tmp_path):
    (tmp_path / "m3_idata.nc").unlink()
    assert pl.main(["--project-only"]) == 1
    assert "bayes_model" not in recorder.calls


def test_chain_without_a_posterior_stops_before_any_fit(recorder, tmp_path, capsys):
    """registration_scenarios would fit a posterior of its own; the
    pipeline refuses instead (only --refit fits)."""
    (tmp_path / "m3_idata.nc").unlink()
    assert pl.main([]) == 1
    assert recorder.calls == []
    assert "no saved posterior" in capsys.readouterr().out


def _script_pipeline(tmp_path, monkeypatch, body):
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    (src / "step.py").write_text(body, encoding="utf-8")
    monkeypatch.setattr(pl, "SRC", src)
    monkeypatch.setattr(pl, "ROOT", tmp_path)
    return pl.Pipeline(tmp_path / "logs" / "t.log")


def test_run_streams_output_to_the_log_and_raises_on_exit_code(tmp_path, monkeypatch):
    p = _script_pipeline(tmp_path, monkeypatch, "print('hello from step')\nraise SystemExit(3)\n")
    with pytest.raises(pl.StepFailed, match="exited with code 3"):
        p.run("dummy", "step.py")
    p.close()
    log = (tmp_path / "logs" / "t.log").read_text()
    assert "hello from step" in log and "[run ] dummy" in log


def test_run_fails_when_outputs_are_not_written(tmp_path, monkeypatch):
    p = _script_pipeline(tmp_path, monkeypatch, "print('ok')\n")
    monkeypatch.setitem(pl.OUTPUTS, "dummy", [tmp_path / "never.csv"])
    with pytest.raises(pl.StepFailed, match="did not write"):
        p.run("dummy", "step.py")
    p.close()


def test_run_records_timing(tmp_path, monkeypatch):
    out = tmp_path / "made.csv"
    p = _script_pipeline(tmp_path, monkeypatch,
                         f"open({str(out)!r}, 'w').write('x')\n")
    monkeypatch.setitem(pl.OUTPUTS, "dummy", [out])
    p.run("dummy", "step.py")
    p.close()
    assert p.timings[-1][0] == "dummy" and p.timings[-1][2] == "ok"
    assert "[ ok ] dummy (" in (tmp_path / "logs" / "t.log").read_text()


def test_refresh_moves_the_archive_page_aside_and_restores_it_on_failure(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "2026_main.html").write_text("old page")
    monkeypatch.setattr(pl, "RAW", raw)
    monkeypatch.setattr(pl, "ROOT", tmp_path)
    seen = {}

    def fake_run(self, name, script, args=(), env=None):
        seen[name] = (raw / "2026_main.html").exists()
        raise pl.StepFailed("network down")

    monkeypatch.setattr(pl.Pipeline, "run", fake_run)
    p = pl.Pipeline(tmp_path / "t.log")
    with pytest.raises(pl.StepFailed):
        pl.step_refresh(p, "20261017_120000")
    p.close()
    assert seen == {"scrape_polls": False}          # the page was moved before the scrape
    assert (raw / "previous" / "2026_main_20261017_120000.html").read_text() == "old page"
    assert (raw / "2026_main.html").read_text() == "old page"     # restored after the failure


def test_headline_reads_the_committed_outputs():
    text = pl.headline()
    assert text.startswith("HEADLINE") and "P(Netanyahu bloc >= 61)" in text
    assert "Central seats" in text and "Likud" in text
