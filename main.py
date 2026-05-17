"""
main.py — Yhangry Partner Signal Scraper & Enrichment Engine

Entry point. Runs the 3-layer pipeline:
    Layer 1: Discovery  → DuckDuckGo search by location
    Layer 2: Scraping   → Fetch company website content
    Layer 3: Enrichment → Extract GTM signals from content

Outputs a structured JSON + CSV of enriched partner profiles ready to be
fed into the scoring model (separate component).

Usage:
    python main.py --location "London" --limit 25
    python main.py --location "Ibiza" --limit 10
    python main.py --location "Tuscany" --limit 50 --output results/
"""

import argparse
import json
import logging
import time
from pathlib import Path

from schema import PartnerProfile
from scraper import discover_companies, scrape_website
from enricher import enrich


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def run_pipeline(location: str, limit: int, output_dir: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Yhangry Partner Signal Scraper & Enrichment Engine")
    print(f"  Target market : {location}")
    print(f"  Company limit : {limit}")
    print(f"{'='*60}\n")

    # ---------------------------------------------------------------
    # LAYER 1: DISCOVERY
    # ---------------------------------------------------------------
    logging.info(f"[Layer 1] Discovering companies in '{location}'...")
    companies = discover_companies(location=location, limit=limit)
    logging.info(f"[Layer 1] {len(companies)} unique companies found\n")

    profiles = []

    for i, company in enumerate(companies, 1):
        logging.info(
            f"[{i:02d}/{len(companies):02d}] {company['company_name']} "
            f"({company['domain']})"
        )

        # -----------------------------------------------------------
        # LAYER 2: SCRAPE
        # -----------------------------------------------------------
        scraped_text = scrape_website(company["source_url"])
        time.sleep(0.5)  # Polite rate limiting

        # -----------------------------------------------------------
        # LAYER 3: ENRICH
        # -----------------------------------------------------------
        enriched = enrich(company, scraped_text)
        enriched["location_searched"] = location

        # Log a human-readable summary for each company
        status = "✓" if enriched["enrichment_success"] else "~"
        logging.info(
            f"  {status} Luxury kws: {enriched['luxury_keyword_count']}  |  "
            f"ADR+: {enriched['high_adr_signals']}  |  "
            f"Concierge: {enriched['concierge_mentioned']}  |  "
            f"PMS: {enriched['pms_detected'] or 'none'}"
        )
        if enriched["luxury_keywords_found"]:
            logging.info(
                f"    Keywords: {', '.join(enriched['luxury_keywords_found'][:5])}"
            )
        if enriched["contact_email"]:
            logging.info(f"    Email: {enriched['contact_email']}")
        print()

        # Build and store the validated profile
        try:
            profile = PartnerProfile(**enriched)
            profiles.append(profile)
        except Exception as e:
            logging.warning(f"  Schema validation error for {company['domain']}: {e}")

    # ---------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    slug = location.lower().replace(" ", "_")
    json_file = output_path / f"partners_{slug}.json"

    # Write JSON
    json_data = [p.model_dump() for p in profiles]
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    enriched_count = sum(1 for p in profiles if p.enrichment_success)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Companies discovered  : {len(profiles)}")
    print(f"  Successfully enriched : {enriched_count}")
    print(f"  Snippet-only          : {len(profiles) - enriched_count}")
    print(f"\n  Output: {json_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Yhangry Partner Signal Scraper & Enrichment Engine\n"
            "Discovers and enriches luxury property management companies\n"
            "as potential yhangry partnership candidates.\n"
            "Output feeds directly into the scoring model (separate component)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Target market to search (e.g. 'London', 'Ibiza', 'Tuscany')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Max number of companies to discover and process (default: 25)",
    )
    parser.add_argument(
        "--output",
        default="sample_output",
        help="Output directory for JSON and CSV files (default: sample_output/)",
    )
    args = parser.parse_args()

    run_pipeline(
        location=args.location,
        limit=args.limit,
        output_dir=args.output,
    )
