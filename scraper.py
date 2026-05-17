"""
scraper.py — Layer 1: Discovery + Layer 2: Raw Content Fetching

Discovery uses DuckDuckGo search (free, no API key required).

NOTE: In a production system, this discovery layer would call the AirDNA API
to pull the top PMCs in a region filtered by Average Daily Rate > £500 and
inventory size > 50 units. AirDNA requires an enterprise contract, so we use
DuckDuckGo here as a functionally equivalent free alternative for this POC.
The enrichment signals we extract downstream are identical either way.
"""

import sys
import os
import time
import logging
from typing import List, Dict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Multiple query templates to get diverse results for a given location.
# Each targets a different partner segment yhangry cares about.
SEARCH_QUERY_TEMPLATES = [
    "luxury property management company {location}",
    "luxury villa rental management {location}",
    "short term rental management company {location}",
    "holiday villa concierge company {location}",
    "luxury vacation rental operator {location}",
]

# Domains to skip — not potential yhangry partners
BLOCKLIST_DOMAINS = {
    # OTAs / aggregators
    "airbnb.com", "vrbo.com", "booking.com", "tripadvisor.com",
    "homeaway.com", "expedia.com", "tripadvisor.de", "tripadvisor.co.uk",
    # Property portals
    "rightmove.co.uk", "zoopla.co.uk", "onthemarket.com",
    # Job / social / encyclopedic
    "indeed.com", "linkedin.com", "uk.linkedin.com", "facebook.com",
    "instagram.com", "wikipedia.org", "youtube.com", "trustpilot.com",
    "twitter.com", "x.com",
    # Dictionaries / encyclopedias / news — not PMCs
    "merriam-webster.com", "dictionary.cambridge.org", "britannica.com",
    "cnn.com", "bbc.co.uk", "bbc.com", "theguardian.com", "forbes.com",
    "luxurydaily.com",
    # Review / directory sites
    "glassdoor.com", "yelp.com", "g2.com", "capterra.com",
}


def _extract_domain(url: str) -> str:
    """Extracts a clean root domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").lower()
        return domain if "." in domain else ""
    except Exception:
        return ""


def _discover_places_api(location: str, limit: int = 25) -> List[Dict]:
    """
    Uses Google Places API (New) Text Search to find property management companies.
    Returns verified, operational businesses.
    """
    results: List[Dict] = []
    seen_domains: set = set()

    queries = [
        f"property management company in {location}",
        f"villa rental agency in {location}",
        f"concierge service in {location}"
    ]

    per_query = max((limit // len(queries)) + 2, 5)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.websiteUri,places.businessStatus,places.rating,places.internationalPhoneNumber"
    }

    for query in queries:
        if len(results) >= limit:
            break

        logging.info(f"  [Places API] Searching: \"{query}\"")
        payload = {
            "textQuery": query,
            "maxResultCount": min(per_query, 20)  # max is 20 per page
        }

        try:
            resp = requests.post(
                "https://places.googleapis.com/v1/places:searchText",
                json=payload,
                headers=headers,
                timeout=10
            )
            if resp.status_code != 200:
                logging.warning(f"  Places API error: {resp.text}")
                continue

            places = resp.json().get("places", [])
            for place in places:
                if len(results) >= limit:
                    break

                # We only want operational businesses with websites
                if place.get("businessStatus") != "OPERATIONAL":
                    continue

                url = place.get("websiteUri", "")
                if not url:
                    continue

                domain = _extract_domain(url)
                if not domain or domain in seen_domains or domain in BLOCKLIST_DOMAINS:
                    continue
                if any(domain.endswith(ext) for ext in [".gov", ".edu", ".gov.uk"]):
                    continue

                seen_domains.add(domain)
                
                # Build snippet from Places data to feed into the pipeline
                name = place.get("displayName", {}).get("text", "Unknown")
                rating = place.get("rating", "N/A")
                phone = place.get("internationalPhoneNumber", "")
                
                snippet = f"Google Places API Record. Rating: {rating}. Phone: {phone}."

                results.append({
                    "company_name": name,
                    "domain": domain,
                    "source_url": url,
                    "snippet": snippet,
                })
        except Exception as e:
            logging.warning(f"  Places API request failed for '{query}': {e}")

    return results


def discover_companies(location: str, limit: int = 25) -> List[Dict]:
    """
    Discovers companies via Google Places API (if key is set) or DuckDuckGo.
    
    Args:
        location: Target market string, e.g. "London", "Ibiza", "Tuscany"
        limit:    Max number of unique companies to return

    Returns:
        List of dicts with keys: company_name, domain, source_url, snippet
    """
    if GOOGLE_PLACES_API_KEY:
        results = _discover_places_api(location, limit)
        if results:
            logging.info(f"  Discovered {len(results)} operational businesses via Google Places")
            return results
        else:
            logging.warning("  Google Places returned no results, falling back to DuckDuckGo...")

    # Fallback: DuckDuckGo Search
    results: List[Dict] = []
    seen_domains: set = set()

    # Spread the limit across query templates
    per_query = max((limit // len(SEARCH_QUERY_TEMPLATES)) + 2, 5)

    ddgs = DDGS()

    for template in SEARCH_QUERY_TEMPLATES:
        if len(results) >= limit:
            break

        query = template.format(location=location)
        logging.info(f"  Searching: \"{query}\"")

        try:
            search_hits = list(ddgs.text(query, max_results=per_query))
        except Exception as e:
            logging.warning(f"  DuckDuckGo search failed for '{query}': {e}")
            time.sleep(2)
            continue

        for hit in search_hits:
            if len(results) >= limit:
                break

            url = hit.get("href", "")
            domain = _extract_domain(url)

            if not domain or domain in seen_domains or domain in BLOCKLIST_DOMAINS:
                continue

            # Skip obviously irrelevant TLDs / gov sites
            if any(domain.endswith(ext) for ext in [".gov", ".edu", ".gov.uk"]):
                continue

            seen_domains.add(domain)
            results.append({
                "company_name": _clean_title(hit.get("title", "Unknown")),
                "domain": domain,
                "source_url": url,
                "snippet": hit.get("body", ""),
            })

        time.sleep(1.2)  # Respectful rate limiting between searches

    logging.info(f"  Discovered {len(results)} unique companies in {location}")
    return results


def scrape_website(url: str, char_limit: int = 6000) -> str:
    """
    Fetches and cleans text content from a company's website homepage.

    Returns:
        Cleaned text string (up to char_limit characters), or "" on failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract valuable metadata (emails, iframes, scripts, links) before decomposing
        # as get_text() will strip URLs which are critical for PMS detection
        extracted_urls = []
        for tag in soup(["a", "iframe", "script", "link"]):
            link = tag.get("href") or tag.get("src")
            if link:
                extracted_urls.append(link)

        # Remove non-content tags (WARNING: Do NOT remove nav/footer as they contain contact info!)
        for tag in soup(["script", "style", "head", "meta", "noscript", "svg"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        
        # Append unique extracted URLs so downstream regex can detect PMS domains and mailto links
        unique_urls = list(set(extracted_urls))
        urls_text = " ".join(unique_urls)
        
        full_scraped = f"{text} \n\n[HIDDEN_URLS] {urls_text}"
        
        # Collapse whitespace
        full_scraped = " ".join(full_scraped.split())
        return full_scraped[:char_limit]

    except Exception as e:
        logging.debug(f"  Could not scrape {url}: {e}")
        return ""


def _clean_title(title: str) -> str:
    """Cleans search result title into a company name."""
    for sep in [" - ", " | ", " – ", " — ", " : "]:
        if sep in title:
            title = title.split(sep)[0]
    return title.strip()
