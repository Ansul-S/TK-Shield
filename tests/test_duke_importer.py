# Tests for Dr. Duke ethnobotany parsing — no download, synthetic dataframe.

import pandas as pd

from src.ingestion.tk_sources import duke_importer as duke


def test_aggregates_uses_per_taxon():
    df = pd.DataFrame({
        "TAXON": ["Curcuma longa", "Curcuma longa", "Azadirachta indica"],
        "CNAME": ["Turmeric", "Turmeric", "Neem"],
        "ACTIVITY": ["Wound", "Inflammation", "Insecticide"],
        "COUNTRY": ["India", "India", "India"],
    })
    entries = duke.entries_from_dataframe(df, limit=10)
    by_name = {e["practice_name"]: e for e in entries}
    assert len(entries) == 2
    turmeric = by_name["Turmeric — traditional uses"]
    assert set(turmeric["uses"]) == {"Wound", "Inflammation"}
    assert "Curcuma longa" in turmeric["plants"]
    assert turmeric["country"] == "India"   # full country name, not truncated


def test_handles_missing_columns_gracefully():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    assert duke.entries_from_dataframe(df, limit=10) == []


def test_nan_common_name_and_country_are_cleaned():
    # Empty CNAME/COUNTRY cells (NaN) must not leak the literal "nan".
    df = pd.DataFrame({
        "TAXON": ["Curcuma longa", "Azadirachta indica"],
        "CNAME": [None, "Neem"],
        "ACTIVITY": ["Wound", "Insecticide"],
        "COUNTRY": [None, "India"],
    })
    by_taxon = {e["plants"][0]: e for e in duke.entries_from_dataframe(df, limit=10)}
    cur = by_taxon["Curcuma longa"]
    assert cur["practice_name"] == "Curcuma longa — traditional uses"   # falls back to taxon
    assert "nan" not in [str(p).lower() for p in cur["plants"]]
    assert cur["country"] == ""                                          # NaN country dropped
    assert by_taxon["Azadirachta indica"]["country"] == "India"          # real value kept
