# src/nlp/ner_extractor.py

import spacy

from src.utils.config import config

nlp = spacy.load(config.SPACY_MODEL)

# ── Custom TK Domain Knowledge ──────────────────────────────
# These are dictionaries of terms we teach the system
# In a real system this would be 1000s of entries from TKDL

# Broadened across domains (medicinal, agricultural, food, cosmetic) and with
# common transliterations (Hindi/regional) to aid multilingual coverage.
PLANT_NAMES = {
    # India / Ayurveda
    "neem", "azadirachta indica", "turmeric", "haldi", "curcuma longa",
    "basmati", "ashwagandha", "withania somnifera", "tulsi", "holy basil",
    "ocimum sanctum", "ocimum tenuiflorum", "brahmi", "bacopa monnieri",
    "giloy", "tinospora cordifolia", "amla", "phyllanthus emblica", "aamla",
    "shatavari", "asparagus racemosus", "arjuna", "terminalia arjuna",
    "guggul", "kalmegh", "andrographis", "jamun", "methi", "fenugreek",
    "trigonella foenum-graecum", "adrak", "ginger", "zingiber officinale",
    "lehsun", "garlic", "allium sativum", "sandalwood", "santalum album",
    "henna", "lawsonia inermis", "moringa", "moringa oleifera",
    "black pepper", "piper nigrum", "frankincense", "boswellia serrata",
    # China / TCM & East Asia
    "ginseng", "panax ginseng", "ginkgo", "ginkgo biloba", "astragalus",
    "ephedra", "ma huang", "cinnamon", "cinnamomum verum",
    # Americas / Amazon / Andes
    "ayahuasca", "banisteriopsis caapi", "maca", "lepidium meyenii",
    "quinoa", "chenopodium quinoa", "cat's claw", "uncaria tomentosa",
    # Africa / Arabia
    "aloe vera", "aloe barbadensis", "rooibos", "aspalathus linearis",
    "hoodia", "hoodia gordonii", "shea", "vitellaria paradoxa",
    # Pacific
    "kava", "piper methysticum",
}

KNOWLEDGE_SYSTEMS = {
    "ayurvedic", "ayurveda", "unani", "siddha", "tcm",
    "traditional chinese medicine", "kampo", "indigenous", "folk medicine",
    "tribal", "ethnobotanical", "ethnomedicine", "traditional knowledge",
}

# Kept key name "medical_uses" for compatibility, but now spans all domains.
MEDICAL_USES = {
    # Medicinal
    "wound healing", "antimalarial", "antifungal", "antibacterial",
    "antimicrobial", "antiviral", "anti-inflammatory", "fever", "malaria",
    "skin infection", "inflammation", "diabetes", "arthritis", "digestive",
    "immunity", "memory", "respiratory", "ulcer", "pain relief",
    # Agricultural
    "pesticide", "insecticide", "pest control", "crop protection",
    "yield improvement", "drought resistance", "plant variety",
    # Food
    "flavoring", "spice", "preservative", "sweetener", "beverage",
    "nutrition", "dietary supplement", "fermented food",
    # Cosmetic
    "skin care", "hair care", "moisturizer", "fragrance", "dye",
    "anti-aging", "complexion",
}

PRACTICES = {
    "decoction", "paste", "poultice", "extract", "infusion",
    "fermentation", "distillation", "cold press", "tincture",
    "powder", "churna", "oil", "pressing", "smoke", "wrap",
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