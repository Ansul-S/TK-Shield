# Tests for request-model input bounds (S3 n_results clamp, S4 max_length).
# Pure-Pydantic — no app/engine load, so these are fast.

import pytest
from pydantic import ValidationError

from api.schemas import MAX_NAME, MAX_TEXT, N_RESULTS_MAX, AnalyzeIn, MonitorIn, TKEntryIn


def test_n_results_clamped_high():
    # S3: an absurd page size is silently bounded, never reaches the engine/LLM.
    assert AnalyzeIn(n_results=100_000).n_results == N_RESULTS_MAX
    assert MonitorIn(n_results=100_000).n_results == N_RESULTS_MAX


def test_n_results_clamped_low_and_passthrough():
    assert AnalyzeIn(n_results=0).n_results == 1      # floor
    assert AnalyzeIn(n_results=-5).n_results == 1
    assert AnalyzeIn(n_results=5).n_results == 5      # in-range passes unchanged
    assert AnalyzeIn().n_results == 5                 # default unaffected


def test_max_length_rejects_oversized_text():
    # S4: oversized free-text is rejected (422) before storage/embedding/prompt.
    with pytest.raises(ValidationError):
        TKEntryIn(practice_name="x" * (MAX_NAME + 1))
    with pytest.raises(ValidationError):
        TKEntryIn(practice_name="ok", description="d" * (MAX_TEXT + 1))


def test_normal_input_passes():
    e = TKEntryIn(practice_name="Turmeric for wounds", description="Haldi paste")
    assert e.practice_name == "Turmeric for wounds"
