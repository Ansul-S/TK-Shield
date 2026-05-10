# src/nlp/ner_extractor.py

import spacy

nlp = spacy.load("en_core_web_sm")

# ── Custom TK Domain Knowledge ──────────────────────────────
# These are dictionaries of terms we teach the system
# In a real system this would be 1000s of entries from TKDL

PLANT_NAMES = {
    "neem", "turmeric", "haldi", "azadirachta indica",
    "curcuma longa", "basmati", "ashwagandha", "withania somnifera",
    "tulsi", "ocimum sanctum", "brahmi", "bacopa monnieri",
    "ayahuasca", "banisteriopsis caapi", "aloe vera", "giloy"
}

KNOWLEDGE_SYSTEMS = {
    "ayurvedic", "ayurveda", "unani", "siddha", "tcm",
    "traditional chinese medicine", "indigenous", "folk medicine",
    "tribal", "ethnobotanical"
}

MEDICAL_USES = {
    "wound healing", "antimalarial", "antifungal", "antibacterial",
    "fever", "malaria", "skin infection", "inflammation",
    "diabetes", "arthritis", "digestive", "antiviral"
}

PRACTICES = {
    "decoction", "paste", "poultice", "extract", "infusion",
    "fermentation", "distillation", "cold press", "tincture"
}


def extract_spacy_entities(text: str) -> list:
    """
    Use spaCy's built-in NER to find standard entities
    like locations, dates, organizations
    """
    doc = nlp(text)
    entities = []

    for ent in doc.ents:
        # We only care about these entity types for TK-Shield
        if ent.label_ in ["GPE", "ORG", "DATE", "PERSON", "LOC"]:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })

    return entities


def extract_tk_entities(text: str) -> dict:
    """
    Our custom NER for TK domain
    Uses dictionary matching — simple but effective for known terms
    """
    text_lower = text.lower()

    found = {
        "plants": [],
        "knowledge_systems": [],
        "medical_uses": [],
        "practices": [],
        "locations": []  # from spaCy
    }

    # Check each word/phrase against our dictionaries
    for plant in PLANT_NAMES:
        if plant in text_lower:
            found["plants"].append(plant)

    for system in KNOWLEDGE_SYSTEMS:
        if system in text_lower:
            found["knowledge_systems"].append(system)

    for use in MEDICAL_USES:
        if use in text_lower:
            found["medical_uses"].append(use)

    for practice in PRACTICES:
        if practice in text_lower:
            found["practices"].append(practice)

    # Use spaCy for locations
    spacy_ents = extract_spacy_entities(text)
    found["locations"] = [
        e["text"] for e in spacy_ents
        if e["label"] in ["GPE", "LOC"]
    ]

    return found


def extract_all(text: str) -> dict:
    """
    Master function — runs both extractors and combines results
    This is what TK-Shield will call for every input
    """
    tk_entities = extract_tk_entities(text)
    spacy_entities = extract_spacy_entities(text)

    return {
        "tk_entities": tk_entities,
        "standard_entities": spacy_entities,
        "summary": {
            "has_plant": len(tk_entities["plants"]) > 0,
            "has_location": len(tk_entities["locations"]) > 0,
            "has_medical_use": len(tk_entities["medical_uses"]) > 0,
            "risk_indicators": len(tk_entities["plants"]) + len(tk_entities["medical_uses"])
        }
    }


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    test_cases = [
        "Neem leaves boiled in water are used for malaria fever in Maharashtra",
        "Turmeric paste applied to wounds by Ayurvedic practitioners in Kerala",
        "The invention comprising use of Azadirachta indica extract for antifungal treatment filed in 1994 by W.R. Grace"
    ]

    print("=" * 60)
    print("TK-SHIELD — NER EXTRACTOR TEST")
    print("=" * 60)

    for text in test_cases:
        print(f"\nINPUT: {text}")
        result = extract_all(text)

        print(f"  Plants found     : {result['tk_entities']['plants']}")
        print(f"  Medical uses     : {result['tk_entities']['medical_uses']}")
        print(f"  Knowledge system : {result['tk_entities']['knowledge_systems']}")
        print(f"  Practices        : {result['tk_entities']['practices']}")
        print(f"  Locations        : {result['tk_entities']['locations']}")
        print(f"  Risk indicators  : {result['summary']['risk_indicators']}")
        print("-" * 60)