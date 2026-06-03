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
    assert turmeric["country"] == "IN"


def test_handles_missing_columns_gracefully():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    assert duke.entries_from_dataframe(df, limit=10) == []
