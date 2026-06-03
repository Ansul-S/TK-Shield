# src/ingestion/tk_sources/wikidata_harvester.py
#
# TK entries from a curated cross-region, cross-domain seed list of well-known
# traditional-knowledge plants, enriched with REAL Wikidata multilingual
# aliases + QIDs via the proven src/clients/wikidata_client. This deliberately
# avoids fragile SPARQL ontology assumptions (exact "medicinal plant" QIDs vary
# and can't be validated offline); the curated seed guarantees quality and the
# Wikidata enrichment supplies the multilingual coverage.

from typing import Iterator

from loguru import logger

from src.classifier.domain import infer_domain
from src.clients import wikidata_client
from src.utils.config import config

# (common name, scientific name, region/community, domain, representative use)
CURATED_TK_PLANTS = [
    ("turmeric", "Curcuma longa", "India (Ayurveda)", "medicinal", "wound healing and anti-inflammatory"),
    ("neem", "Azadirachta indica", "India", "agricultural", "antifungal and natural pesticide"),
    ("basmati rice", "Oryza sativa", "India/Pakistan", "agricultural", "aromatic traditional rice landrace"),
    ("ashwagandha", "Withania somnifera", "India (Ayurveda)", "medicinal", "adaptogen and tonic"),
    ("tulsi", "Ocimum tenuiflorum", "India", "medicinal", "respiratory and immunity remedy"),
    ("brahmi", "Bacopa monnieri", "India", "medicinal", "memory and cognition tonic"),
    ("giloy", "Tinospora cordifolia", "India", "medicinal", "fever and immunity"),
    ("amla", "Phyllanthus emblica", "India", "medicinal", "vitamin-C tonic and hair care"),
    ("ginger", "Zingiber officinale", "Asia", "food", "digestive and anti-nausea"),
    ("garlic", "Allium sativum", "Global", "medicinal", "antimicrobial and cardiovascular"),
    ("aloe vera", "Aloe barbadensis", "Africa/Arabia", "cosmetic", "skin healing and moisturizer"),
    ("ginseng", "Panax ginseng", "China/Korea", "medicinal", "energy tonic in TCM"),
    ("ginkgo", "Ginkgo biloba", "China", "medicinal", "circulation and memory"),
    ("astragalus", "Astragalus propinquus", "China", "medicinal", "immune tonic in TCM"),
    ("ephedra (ma huang)", "Ephedra sinica", "China", "medicinal", "respiratory remedy in TCM"),
    ("rooibos", "Aspalathus linearis", "South Africa", "food", "traditional herbal tea"),
    ("hoodia", "Hoodia gordonii", "Southern Africa (San)", "medicinal", "appetite suppressant"),
    ("kava", "Piper methysticum", "Pacific Islands", "medicinal", "ceremonial calming drink"),
    ("ayahuasca", "Banisteriopsis caapi", "Amazon", "medicinal", "ceremonial entheogen"),
    ("maca", "Lepidium meyenii", "Andes (Peru)", "food", "stamina and fertility food"),
    ("quinoa", "Chenopodium quinoa", "Andes", "food", "traditional staple grain"),
    ("cat's claw", "Uncaria tomentosa", "Amazon", "medicinal", "anti-inflammatory bark"),
    ("shea", "Vitellaria paradoxa", "West Africa", "cosmetic", "skin butter"),
    ("moringa", "Moringa oleifera", "India/Africa", "food", "nutritional leaf"),
    ("fenugreek", "Trigonella foenum-graecum", "India/Mediterranean", "food", "digestive and lactation"),
    ("sandalwood", "Santalum album", "India", "cosmetic", "fragrance and skin paste"),
    ("henna", "Lawsonia inermis", "India/North Africa", "cosmetic", "hair and skin dye"),
    ("frankincense", "Boswellia serrata", "Arabia/India", "medicinal", "anti-inflammatory resin"),
    ("black pepper", "Piper nigrum", "India", "food", "spice and digestive"),
    ("cinnamon", "Cinnamomum verum", "Sri Lanka", "food", "spice and blood-sugar remedy"),
]


def iter_tk_entries(limit: int) -> Iterator[dict]:
    yielded = 0
    for cname, sci, region, domain_hint, use in CURATED_TK_PLANTS:
        if yielded >= limit:
            break
        aliases = []
        if config.ENABLE_WIKIDATA:
            wd = wikidata_client.search_plant(sci) or wikidata_client.search_plant(cname)
            if wd:
                aliases = list(dict.fromkeys([wd["title"], *wd.get("aliases", [])]))
        desc = f"Traditional knowledge: {cname} ({sci}) used for {use} in {region}."
        yield {
            "practice_name": f"{cname.title()} — {use}",
            "description": desc,
            "community": region,
            "country": "",
            "documentation_date": "",
            "category": "traditional-knowledge",
            "domain": domain_hint or infer_domain(desc),
            "plants": [cname, sci],
            "uses": [use],
            "aliases": aliases,
        }
        yielded += 1
    logger.success(f"Wikidata harvester: yielded {yielded} curated+enriched TK entries")
