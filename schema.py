from pydantic import BaseModel
from typing import Optional, List


class PartnerProfile(BaseModel):
    """
    Structured output schema for a single enriched partner prospect.
    This is the output contract of the scraper/enrichment engine.
    It feeds directly into the scoring model as a separate downstream component.
    """

    # --- Identity ---
    company_name: str
    domain: str
    source_url: str
    location_searched: str = ""
    snippet: str = ""  # DuckDuckGo search snippet (fast-path signal)

    # --- Scale Signals ---
    estimated_property_count: Optional[int] = None  # e.g. 120
    geographic_markets: List[str] = []              # e.g. ["London", "Ibiza"]

    # --- Quality Signals ---
    luxury_keywords_found: List[str] = []
    luxury_keyword_count: int = 0
    high_adr_signals: bool = False        # Pricing language suggests £500+/night
    concierge_mentioned: bool = False     # Natural alignment with yhangry's offer

    # --- Tech Stack (PMS / Channels) ---
    pms_detected: List[str] = []          # e.g. ["Guesty", "Hostaway"]
    channel_managers: List[str] = []      # e.g. ["Airbnb", "Vrbo"]

    # --- Contact ---
    contact_email: Optional[str] = None

    # --- Pipeline Meta ---
    data_sources: List[str] = []
    enrichment_success: bool = False      # False if site couldn't be scraped
