# Yhangry — Partner Signal Scraper & Enrichment Engine

A robust, intelligent data pipeline designed to discover, verify, and enrich potential yhangry B2B partnership candidates (luxury property management companies, villa operators, concierge businesses) in any target location.

**Input:** A target market/location (e.g. `"London"`, `"Ibiza"`, `"Tuscany"`)  
**Output:** Enriched partner profiles as a structured JSON array, ready to feed into the scoring model.

---

## Graceful Degradation & API Integrations

The scraper is designed with **graceful fallback architecture**. It works out-of-the-box using free tools, but automatically unlocks enterprise-grade intelligence if API keys are supplied in a `.env` file:

| Pipeline Step | Enhanced Mode (With API Keys) | Free Fallback Mode (Without API Keys) |
|---|---|---|
| **Layer 1: Discovery** | **Google Places API** — Operational businesses, official websites, phone numbers, and ratings. | **DuckDuckGo Search** — Direct scraping across 5 search templates (no API key needed). |
| **Layer 3a: Verification** | **UK Companies House API** — Fetches status, SIC codes, director name, and incorporation year. | **Skipped** — Gracefully omitted if API key is not supplied. |
| **Layer 3b: Enrichment** | **Groq LLM (Llama 3.1 8B)** — Deep semantic understanding (Luxury tier classification, true business-type confirmation, PMS tool extraction). | **Regex / Keyword Rules** — Matches luxury keywords, concierge phrases, high ADR patterns, and PMS platforms. |

---

## How It Works

```
        Input: --location "London" --limit 25
                        │
                        ▼
┌───────────────────────────────────────────────┐
│  Layer 1: Discovery                           │
│  - Google Places API (Operational matches)    │
│  - Fallback: DuckDuckGo templates             │
│  - Automatic domain blocklist & deduplication │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│  Layer 2: Scrape                              │
│  - polite requests + BeautifulSoup            │
│  - HTML stripping & text normalization        │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│  Layer 3a: Verification (Companies House)     │
│  - UK API match by name                       │
│  - Status, SIC codes, director, inc. year     │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│  Layer 3b: Enrichment                         │
│  - Groq LLM (Llama 3.1 8B instant)            │
│  - Fallback: Robust regex & keyword extractors│
└───────────────────────┬───────────────────────┘
                        │
                        ▼
            Output: sample_output/partners_london.json
```

---

## Quick Start

### 1. Installation

Clone this repository, navigate to the folder, and install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)

Create a `.env` file in the root of `yhangry-signal-scraper/` (use `.env.example` as a template):

```bash
cp .env.example .env
```

Open `.env` and fill in the API keys for the services you want to enable:
```ini
# Google Places API key (Text Search)
GOOGLE_PLACES_API_KEY=your_google_places_key

# UK Companies House API Key (Basic Auth Key)
COMPANIES_HOUSE_API_KEY=your_companies_house_key

# Groq API Key (for LLM extraction)
GROQ_API_KEY=your_groq_api_key
```
*Note: If no `.env` is created, the pipeline will still run perfectly using DuckDuckGo search + local regex parsing.*

### 3. Run the Pipeline

Run the scraping command from your terminal:

```bash
# Run for London, discover up to 25 companies
python3 main.py --location "London" --limit 25

# Run for Ibiza, discover up to 10 companies
python3 main.py --location "Ibiza" --limit 10

# Customize the output directory
python3 main.py --location "Tuscany" --limit 30 --output results/
```

---

## Output Schema

The output is written to a JSON array containing structured objects that strictly validate against our Pydantic model (`schema.py`):

```json
{
  "company_name": "Under The Doormat",
  "domain": "underthedoormat.com",
  "source_url": "https://underthedoormat.com",
  "location_searched": "London",
  "snippet": "Premium short term rentals in London. Fully managed service with bespoke hospitality.",
  "estimated_property_count": 300,
  "geographic_markets": [
    "London"
  ],
  "luxury_keywords_found": [
    "luxury",
    "bespoke",
    "exclusive",
    "concierge"
  ],
  "luxury_keyword_count": 4,
  "high_adr_signals": true,
  "concierge_mentioned": true,
  "pms_detected": [
    "Guesty"
  ],
  "channel_managers": [
    "Airbnb",
    "Booking.com"
  ],
  "contact_email": "bookings@underthedoormat.com",
  "companies_house_verified": true,
  "company_status": "active",
  "sic_codes": [
    "55209"
  ],
  "director_name": "SMITH, John",
  "incorporation_year": 2014,
  "is_property_manager": true,
  "luxury_tier": "luxury",
  "groq_extraction_success": true,
  "data_sources": [
    "duckduckgo_search",
    "website_scrape",
    "companies_house",
    "groq_llm"
  ],
  "enrichment_success": true
}
```

### Schema Field Classifications:
* **Identity**: `company_name`, `domain`, `source_url`, `location_searched`, `snippet`
* **Scale Signals**: `estimated_property_count` (int), `geographic_markets` (list)
* **Quality Signals**: `luxury_keywords_found`, `luxury_keyword_count`, `high_adr_signals`, `concierge_mentioned` (ideal alignment with yhangry)
* **Tech Stack**: `pms_detected` (e.g. Guesty, Hostaway), `channel_managers` (e.g. Airbnb)
* **Companies House Verification (Layer 3a)**: `companies_house_verified`, `company_status`, `sic_codes`, `director_name`, `incorporation_year`
* **LLM Enrichment (Layer 3b)**: `is_property_manager` (bool classification), `luxury_tier` (budget / mid / luxury / ultra), `groq_extraction_success`
* **Pipeline Metadata**: `data_sources` (tracks which APIs/engines enriched the profile), `enrichment_success`

---

## File Structure

```
yhangry-signal-scraper/
├── main.py          # CLI entrypoint + pipeline coordinator
├── scraper.py       # Layer 1 (Discovery - Google Places/DDG) & Layer 2 (Scraping)
├── enricher.py      # Layer 3: GTM signal extraction (Groq LLM + regex rules)
├── schema.py        # Pydantic model contract for output validation
├── .env.example     # Configuration file template
├── requirements.txt # Project dependencies
└── sample_output/   # Generated partner profiles (JSON)
```
