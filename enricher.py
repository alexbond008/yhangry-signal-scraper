"""
enricher.py — Layer 3: Signal Extraction

Extracts structured GTM signals from raw website text + search snippets.
Each signal maps directly to a feature in the downstream scoring model.

NOTE: In production, contact enrichment (email, decision-maker name/title)
would use the Hunter.io API (find-email endpoint) and Apollo.io company search.
Both require accounts. For this POC we extract emails via regex from the
scraped page content, which works well for smaller operators who publish
contact details on their sites.
"""

import re
import os
import json
import logging
from typing import List, Optional, Dict

try:
    from groq import Groq
except ImportError:
    Groq = None

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None


# ---------------------------------------------------------------------------
# Signal dictionaries
# ---------------------------------------------------------------------------

LUXURY_KEYWORDS = [
    "luxury", "bespoke", "ultra-luxury", "curated", "exclusive", "premium",
    "high-end", "boutique", "concierge", "villa", "estate", "manor",
    "chateau", "château", "private", "handpicked", "tailored", "elite",
    "five-star", "5-star", "bespoke experience", "opulent", "lavish",
    "prestige", "signature", "world-class",
]

CONCIERGE_KEYWORDS = [
    "concierge", "private chef", "personal chef", "butler", "bespoke dining",
    "in-home dining", "private dining", "chef experience", "private cook",
    "culinary experience",
]

PMS_PLATFORMS = [
    "Guesty", "Hostaway", "Lodgify", "Smoobu", "Tokeet", "iGMS",
    "OwnerRez", "Beds24", "Rentals United", "Escapia", "LiveRez",
    "Cloudbeds", "Little Hotelier", "Kigo", "365Villas",
]

CHANNEL_MANAGERS = [
    "Airbnb", "Vrbo", "VRBO", "Booking.com", "HomeAway",
    "TripAdvisor", "Expedia", "Google Vacation Rentals",
]

# Major luxury travel markets relevant to yhangry's ICP
LUXURY_MARKETS = [
    "London", "Ibiza", "Tuscany", "Santorini", "Mykonos", "Mallorca",
    "Monaco", "Côte d'Azur", "Amalfi", "Lake Como", "Dubai", "Marbella",
    "Cannes", "Nice", "Barcelona", "Rome", "Florence", "Sardinia",
    "Cyprus", "Edinburgh", "Cotswolds", "Cornwall", "Lake District",
    "Provence", "Dordogne", "Umbria", "Algarve", "Lisbon",
    "Hamptons", "Aspen", "Palm Beach", "Malibu", "St Tropez",
    "Verbier", "Gstaad", "Courchevel",
]

# ADR patterns: £500+/night signals
HIGH_ADR_PATTERNS = [
    r"£\s*[5-9]\d{2,}",            # £500–£999
    r"£\s*[1-9]\d{3,}",            # £1,000+
    r"\$\s*[5-9]\d{2,}",           # $500+
    r"from\s+£\s*[5-9]\d{2}",
    r"rates\s+from\s+£\s*[5-9]",
    r"starting\s+(?:from\s+)?£\s*[5-9]\d{2}",
    r"nightly\s+rate[s]?\s+(?:from\s+)?£\s*[5-9]",
]

# Portfolio size extraction patterns
PORTFOLIO_PATTERNS = [
    r"(\d{2,4})\+?\s*(?:properties|homes|villas|listings|rentals|units|residences)",
    r"portfolio\s+of\s+(?:over\s+)?(\d{2,4})",
    r"managing\s+(?:over\s+)?(\d{2,4})\s*(?:properties|homes|villas)?",
    r"over\s+(\d{2,4})\s+(?:properties|homes|villas|listings)",
    r"more\s+than\s+(\d{2,4})\s+(?:properties|homes|villas|listings)",
    r"(\d{2,4})\s+(?:luxury\s+)?(?:properties|homes|villas)\s+(?:across|in|throughout)",
]


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_luxury_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    return [kw for kw in LUXURY_KEYWORDS if kw.lower() in text_lower]


def extract_concierge_signal(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in CONCIERGE_KEYWORDS)


def extract_property_count(text: str) -> Optional[int]:
    """Attempts to extract portfolio size from natural language on the site."""
    for pattern in PORTFOLIO_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            # Sanity check — ignore obviously wrong values
            if 5 <= count <= 10000:
                return count
    return None


def detect_high_adr(text: str) -> bool:
    """Returns True if pricing language suggests ADR > £500/night."""
    return any(re.search(p, text, re.IGNORECASE) for p in HIGH_ADR_PATTERNS)


def detect_pms(text: str) -> List[str]:
    return [pms for pms in PMS_PLATFORMS if pms.lower() in text.lower()]


def detect_channels(text: str) -> List[str]:
    return [ch for ch in CHANNEL_MANAGERS if ch.lower() in text.lower()]


def detect_markets(text: str) -> List[str]:
    return [m for m in LUXURY_MARKETS if m.lower() in text.lower()]


def extract_email(text: str) -> Optional[str]:
    """
    Extracts first email address found in text.
    NOTE: In production this is replaced by Hunter.io's find-email endpoint
    which returns the verified decision-maker email with confidence score.
    """
    match = re.search(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text
    )
    if match:
        email = match.group(0)
        # Filter out common non-contact emails
        if not any(skip in email.lower() for skip in ["noreply", "no-reply", "support@", "info@example"]):
            return email
    return None


# ---------------------------------------------------------------------------
# LLM Signal Extraction (Groq / Llama 3.1)
# ---------------------------------------------------------------------------

def extract_signals_with_llm(text: str) -> Optional[Dict]:
    """Uses Groq to extract structured GTM signals from text."""
    if not groq_client:
        return None

    prompt = f"""You are a data extraction assistant for yhangry, a private chef marketplace.
You are analyzing a potential B2B partner's website. Read the website text and extract the following signals as a JSON object:

- is_property_manager (bool): Does this company manage short-term rental properties/villas on behalf of owners?
- luxury_tier (str or null): Classify their portfolio as "budget", "mid", "luxury", or "ultra". Return null if unclear.
- estimated_property_count (int or null): The number of properties they manage. Look for numbers near words like "homes", "villas", "properties". Return null if not found.
- concierge_fit (bool): Do they mention offering concierge, private chef, butler, or bespoke experiential services?
- pms_software (str or null): Do they mention any property management software (e.g., Guesty, Hostaway)?
- geographic_markets (list of str): Cities or regions where they operate.

Return ONLY raw, valid JSON. No markdown formatting, no explanations. Do not wrap in ```json ```.

Website text:
{text[:4000]}
"""
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        response_text = completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        logging.warning(f"  Groq LLM extraction failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------

def enrich(company: Dict, scraped_text: str) -> Dict:
    """
    Runs all signal extractors against the combined text corpus
    (website content + DuckDuckGo search snippet).

    Args:
        company:      Raw company dict from scraper (name, domain, url, snippet)
        scraped_text: Full text scraped from the company's homepage

    Returns:
        Enriched dict with all extracted signals added.
    """
    # Combine scraped page + snippet for maximum signal coverage
    snippet = company.get("snippet", "")
    full_text = scraped_text + " " + snippet

    luxury_keywords = extract_luxury_keywords(full_text)
    property_count = extract_property_count(full_text)
    high_adr = detect_high_adr(full_text)
    pms = detect_pms(full_text)
    channels = detect_channels(full_text)
    markets = detect_markets(full_text)
    email = extract_email(full_text)
    concierge = extract_concierge_signal(full_text)

    enrichment_success = len(scraped_text) > 200  # Meaningful content scraped

    if not enrichment_success:
        logging.debug(f"  Low content scraped for {company.get('domain')} — using snippet only")

    # Initialize results with regex fallbacks
    results = {
        **company,
        "luxury_keywords_found": luxury_keywords,
        "luxury_keyword_count": len(luxury_keywords),
        "estimated_property_count": property_count,
        "high_adr_signals": high_adr,
        "pms_detected": pms,
        "channel_managers": channels,
        "geographic_markets": markets,
        "contact_email": email,
        "concierge_mentioned": concierge,
        "enrichment_success": enrichment_success,
        "groq_extraction_success": False,
        "is_property_manager": None,
        "luxury_tier": None,
        "data_sources": (
            ["duckduckgo_search", "website_scrape"]
            if enrichment_success
            else ["duckduckgo_search"]
        ),
    }

    # Try Groq LLM extraction
    if groq_client and enrichment_success:
        llm_data = extract_signals_with_llm(full_text)
        if llm_data:
            results["groq_extraction_success"] = True
            if "data_sources" in results:
                results["data_sources"].append("groq_llm")

            # Merge LLM fields
            results["is_property_manager"] = llm_data.get("is_property_manager")
            results["luxury_tier"] = llm_data.get("luxury_tier")

            # Override regex with LLM if LLM found something
            if llm_data.get("estimated_property_count"):
                results["estimated_property_count"] = llm_data["estimated_property_count"]
            if llm_data.get("concierge_fit") is not None:
                results["concierge_mentioned"] = llm_data["concierge_fit"]
            if llm_data.get("geographic_markets"):
                # Merge lists
                merged = set(results["geographic_markets"]) | set(llm_data["geographic_markets"])
                results["geographic_markets"] = list(merged)
            if llm_data.get("pms_software"):
                results["pms_detected"].append(llm_data["pms_software"])

    return results
