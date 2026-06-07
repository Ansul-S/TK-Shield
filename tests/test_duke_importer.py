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


def test_split_geo_extracts_community_and_strips_artifacts():
    assert duke.split_geo("INDIA(SANTAL)") == ("INDIA", "Santal")
    assert duke.split_geo("US(AMERINDIAN)") == ("US", "Amerindian")
    assert duke.split_geo("JAPAN*") == ("JAPAN", "")
    assert duke.split_geo("CHINA") == ("CHINA", "")
    assert duke.split_geo(None) == ("", "")
    assert duke.split_geo("nan") == ("", "")


def test_split_geo_does_not_misattribute_country_or_region_as_people():
    # A parenthetical that is a country/region/religion is NOT a holder people —
    # it must be dropped, not stored as a community (M2).
    assert duke.split_geo("INDIA(ASIA)") == ("INDIA", "")
    assert duke.split_geo("INDIA(INDIA)") == ("INDIA", "")
    assert duke.split_geo("X(HINDU)") == ("X", "")
    assert duke.split_geo("X(SOUTH AFRICA)") == ("X", "")
    # Genuine peoples still pass through.
    assert duke.split_geo("MEXICO(AZTEC)") == ("MEXICO", "Aztec")


def test_is_not_a_people():
    assert duke.is_not_a_people("India") is True
    assert duke.is_not_a_people("Asia") is True
    assert duke.is_not_a_people("Hindu") is True
    assert duke.is_not_a_people("Santal") is False
    assert duke.is_not_a_people("Aztec") is False


def test_country_parenthetical_becomes_community():
    # INDIA(SANTAL) must consolidate the country to INDIA and attribute Santal.
    df = pd.DataFrame({
        "TAXON": ["Curcuma longa"],
        "CNAME": ["Turmeric"],
        "ACTIVITY": ["Wound"],
        "COUNTRY": ["INDIA(SANTAL)"],
    })
    e = duke.entries_from_dataframe(df, limit=10)[0]
    assert e["country"] == "INDIA"
    assert e["community"] == "Santal"


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
