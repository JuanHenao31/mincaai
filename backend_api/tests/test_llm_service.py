import os
from pathlib import Path
import pandas as pd

from backend_api.app.services import llm_service


def test_transform_sheet_with_rules_valid_csv(monkeypatch):
    # Prepare a simple DataFrame
    df = pd.DataFrame({"a": [1, 2]})

    # Fake LLM to return a valid CSV
    def fake_call(system_prompt, user_prompt, model="m", max_retries=2, timeout=30):
        return "a,b\n1,foo\n2,bar"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_service, "_call_openai_csv", fake_call)

    out = llm_service.transform_sheet_with_rules(df, rules={}, use_llm=True)

    assert list(out.columns) == ["a", "b"]
    assert out.shape[0] == 2
    assert out.iloc[0]["b"] == "foo"


def test_transform_sheet_with_rules_failure_creates_debug(monkeypatch, tmp_path):
    # Ensure OPENAI key exists so LLM branch is attempted
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Force the _call_openai_csv to raise an exception
    def fake_call_raise(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(llm_service, "_call_openai_csv", fake_call_raise)

    # Clean potential existing debug files
    base_dir = Path(llm_service.__file__).resolve().parents[2]
    debug_dir = base_dir / "data" / "llm_debug"
    if debug_dir.exists():
        for f in debug_dir.glob("llm_raw_*.txt"):
            try:
                f.unlink()
            except Exception:
                pass

    df = pd.DataFrame({"a": [1]})
    out = llm_service.transform_sheet_with_rules(df, rules={}, use_llm=True)

    # On failure the fallback adds columns
    assert "DANOS MATERIALES LIMITES" in out.columns

    # A debug file should have been created
    files = list(debug_dir.glob("llm_raw_*.txt")) if debug_dir.exists() else []
    assert len(files) >= 1

    # Cleanup created debug files
    for f in files:
        try:
            f.unlink()
        except Exception:
            pass
