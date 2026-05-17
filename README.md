# Yhangry — Partner Signal Scraper & Enrichment Engine

A proof-of-concept data pipeline that discovers, scrapes, and enriches potential yhangry partnership candidates (luxury property management companies, villa operators, concierge businesses) from a target location.

**Input:** a location (e.g. `"London"`, `"Ibiza"`, `"Tuscany"`)  
**Output:** enriched partner profiles as JSON, ready to feed into the scoring model (separate component)

---

## How It Works

```
Input: --location "London" --limit 25
        │
        ▼
┌─────────────────────────────────────────┐
│  Layer 1: Discovery                     │
│  DuckDuckGo search across 5 query       │
│  templates (luxury PMC, villa rental,   │
│  short-term rental, concierge, etc.)    │
│  → deduped list of company domains      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Layer 2: Scraping                      │
│  requests + BeautifulSoup               │
│  → raw text content from each homepage  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Layer 3: Enrichment                    │
│  Keyword matching + regex extraction    │
│  Signals: luxury keywords, portfolio    │
│  size, ADR tier, PMS tech stack,        │
│  concierge mentions, email, markets     │
└────────────────┬────────────────────────┘
                 │
                 ▼
Output: partners_london.json
        → feeds into scoring model (separate component)
```

---

## Quick Start

```bash
# Install dependencies (all free, no API keys needed)
pip install -r requirements.txt

# Run for London, discover 25 companies
python main.py --location "London" --limit 25

# Run for Ibiza, discover 15 companies
python main.py --location "Ibiza" --limit 15

# Custom output directory
python main.py --location "Tuscany" --limit 30 --output results/
```

---

## Output Schema

Each partner profile is written to JSON following this structure (`schema.py`):

```json
{
  "company_name": "Under The Doormat",
  "domain": "underthedoormat.com",
  "source_url": "https://underthedoormat.com",
  "location_searched": "London",
  "estimated_property_count": null,
  "geographic_markets": ["London", "Dordogne", "Umbria"],
  "luxury_keywords_found": ["luxury", "bespoke", "exclusive", "concierge", "estate"],
  "luxury_keyword_count": 6,
  "high_adr_signals": true,
  "concierge_mentioned": true,
  "pms_detected": [],
  "channel_managers": ["Airbnb"],
  "contact_email": null,
  "data_sources": ["duckduckgo_search", "website_scrape"],
  "enrichment_success": true
}
```

The output is a JSON array of these profiles — one object per discovered company.

---

## What This Would Look Like in Production

This POC uses free tools to demonstrate the architecture. In a production system:

| Layer | POC (this) | Production |
|---|---|---|
| **Discovery** | DuckDuckGo search | **AirDNA API** — pulls top PMCs by region, filtered by ADR > £500 and inventory > 50 units |
| **Contact enrichment** | Regex on scraped pages | **Hunter.io API** — verified decision-maker email + confidence score |
| **Company data** | Website scraping | **Apollo.io API** — firmographics, headcount, tech stack, LinkedIn |
| **Signal extraction** | Keyword matching | **GPT-4o web research agent** — structured extraction with reasoning |
| **Output** | JSON file | Direct write to scoring model input queue or HubSpot via API |

The schema is identical either way — this swap requires no architectural changes, only replacing the data source clients.

---

## File Structure

```
yhangry-signal-scraper/
├── main.py          # CLI entrypoint + pipeline orchestrator
├── scraper.py       # Layer 1 (DuckDuckGo discovery) + Layer 2 (website scraping)
├── enricher.py      # Layer 3: signal extraction from scraped content
├── schema.py        # Pydantic model — the partner profile contract
├── requirements.txt
└── sample_output/   # Generated JSON output
```
