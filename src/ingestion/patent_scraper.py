# src/ingestion/patent_scraper.py

import pandas as pd
from loguru import logger
from datasets import load_dataset
from src.utils.config import config

# TK-relevant keywords to filter within section A and C patents
# Since we don't have specific IPC subclass, we filter by content
TK_KEYWORDS = [
    "plant", "herb", "botanical", "medicinal", "traditional",
    "extract", "root", "leaf", "bark", "seed", "flower",
    "ayurved", "indigenous", "folk", "natural remedy",
    "turmeric", "neem", "ginger", "garlic", "aloe",
    "curcumin", "azadirachta", "withania", "ocimum",
    "fungal", "antimicrobial", "antiviral", "anti-inflammatory",
    "wound", "fever", "infection", "treatment",
    "rice", "wheat", "crop", "grain", "variety", "cultivar",
    "genetic", "organism", "biological", "enzyme", "protein",
    "ferment", "microorganism", "bacteria", "culture"
]

# Section labels we care about
# 0 = A (Human Necessities — medicinal, agricultural)
# 2 = C (Chemistry — compounds derived from plants)
TK_LABELS = {0, 2}

# Map label integer to IPC section
LABEL_TO_IPC = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
    4: "E",
    5: "F",
    6: "G",
    7: "H",
    8: "Y"
}


def is_tk_relevant(text: str, label: int) -> bool:
    """
    Two-step filter:
    1. Must be in section A or C (medicinal/chemistry)
    2. Must contain at least one TK-relevant keyword
    """
    if label not in TK_LABELS:
        return False

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TK_KEYWORDS)


def clean_patent(raw: dict, idx: int) -> dict | None:
    """
    Normalize raw record into our standard format
    """
    text  = (raw.get("text") or "").strip()
    label = int(raw.get("label", -1))

    if not text or len(text) < 50:
        return None

    if not is_tk_relevant(text, label):
        return None

    # Extract a pseudo-title from first sentence
    first_sentence = text.split(".")[0].strip()
    title = first_sentence[:120] if first_sentence else f"Patent {idx}"

    ipc_section = LABEL_TO_IPC.get(label, "UNKNOWN")

    return {
        "id":   f"PAT-{idx:07d}",
        "text": text,
        "metadata": {
            "patent_id":   f"PAT-{idx:07d}",
            "title":       title,
            "abstract":    text[:500],
            "assignee":    "Unknown",
            "filing_date": "",
            "country":     "US",
            "ipc_code":    ipc_section,
            "source":      "ccdv-patent-classification",
            "status":      "GRANTED"
        }
    }


def ingest_patents(max_patents: int = 5000) -> pd.DataFrame:
    """
    Load patents, filter for TK relevance, save to CSV
    """
    logger.info("Loading ccdv/patent-classification dataset...")

    dataset = load_dataset(
        "ccdv/patent-classification",
        "abstract",
        split="train",
        trust_remote_code=False
    )

    logger.success(f"Loaded {len(dataset)} total patents")
    logger.info(f"Filtering for TK-relevant patents in sections A and C...")

    # Show label distribution first
    from collections import Counter
    label_dist = Counter(dataset["label"])
    logger.info("Label distribution in dataset:")
    for label, count in sorted(label_dist.items()):
        section = LABEL_TO_IPC.get(label, "?")
        logger.info(f"  Label {label} (Section {section}): {count} patents")

    patents = []
    skipped = 0

    for idx, raw in enumerate(dataset):
        cleaned = clean_patent(raw, idx)
        if cleaned:
            patents.append(cleaned)
        else:
            skipped += 1

        if len(patents) >= max_patents:
            break

        if idx % 5000 == 0 and idx > 0:
            logger.info(f"  Scanned {idx} | Kept {len(patents)}...")

    logger.success(f"Kept {len(patents)} TK-relevant patents out of {len(dataset)}")

    if not patents:
        logger.error("No patents collected after filtering")
        return pd.DataFrame()

    # Save to CSV
    config.DATA_RAW_PATH.mkdir(parents=True, exist_ok=True)

    rows = [{
        "id":          p["id"],
        "text":        p["text"],
        "patent_id":   p["metadata"]["patent_id"],
        "title":       p["metadata"]["title"],
        "abstract":    p["metadata"]["abstract"],
        "assignee":    p["metadata"]["assignee"],
        "filing_date": p["metadata"]["filing_date"],
        "country":     p["metadata"]["country"],
        "ipc_code":    p["metadata"]["ipc_code"],
        "source":      p["metadata"]["source"],
        "status":      p["metadata"]["status"],
    } for p in patents]

    df = pd.DataFrame(rows)
    output_path = config.DATA_RAW_PATH / "patents_medicinal.csv"
    df.to_csv(output_path, index=False)
    logger.success(f"Saved {len(df)} patents → {output_path}")

    # Show keyword hit distribution
    print("\nTop keyword matches in collected patents:")
    all_text = " ".join(df["text"].tolist()).lower()
    for kw in sorted(TK_KEYWORDS, key=lambda k: -all_text.count(k))[:15]:
        count = all_text.count(kw)
        if count > 0:
            bar = "█" * min(count // 5, 40)
            print(f"  {kw:<25} {count:>5}  {bar}")

    return df


if __name__ == "__main__":
    logger.info("TK-SHIELD — Patent Ingestion Pipeline")
    logger.info("=" * 55)

    df = ingest_patents(max_patents=3000)

    if not df.empty:
        print(f"\n✅ Ingested {len(df)} TK-relevant patents")
        print(f"\nSample:")
        print(df[["patent_id", "ipc_code", "title"]].head(10).to_string())