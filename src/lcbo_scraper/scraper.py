# ==============================================================================
#  Copyright 2025 Matthew Pounsett <matt@conundrum.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ==============================================================================
"""LCBO website scraper using Coveo search API and BeautifulSoup."""

import logging

import httpx
from bs4 import BeautifulSoup
from furl import furl

from lcbo_scraper.models import Product

logger = logging.getLogger(__name__)

# Coveo API configuration (extracted from LCBO website)
COVEO_API_URL = "https://platform.cloud.coveo.com/rest/search/v2"
COVEO_ORG_ID = "lcboproductionx2kwygnc"
COVEO_ACCESS_TOKEN = "xx883b5583-07fb-416b-874b-77cce565d927"

# LCBO base URL
LCBO_BASE_URL = "https://www.lcbo.com"


def normalize_product_url(url: str) -> str:
    """Normalize a product URL to the consumer website.

    The Coveo API sometimes returns wholesale URLs that need to be
    converted to consumer URLs.

    Args:
        url: The URL returned from search results.

    Returns:
        Normalized URL for the consumer website.
    """
    # Convert wholesale URLs to consumer URLs
    # wholesale: https://wholesale.lcbo.com/b2b_en/product-name-12345
    # consumer:  https://www.lcbo.com/en/product-name-12345
    if "wholesale.lcbo.com/b2b_en/" in url:
        url = url.replace("wholesale.lcbo.com/b2b_en/", "www.lcbo.com/en/")
    return url


class LcboScraper:
    """Scraper for LCBO website products."""

    def __init__(self) -> None:
        """Initialize the scraper with an HTTPX client."""
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

    def __enter__(self) -> "LcboScraper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close the client."""
        self.close()

    def close(self) -> None:
        """Close the httpx client."""
        self.client.close()

    def search_product(self, product_number: str) -> str | None:
        """Search for a product by number using Coveo API.

        Args:
            product_number: The LCBO product number to search for.

        Returns:
            The product page URL if found, None otherwise.
        """
        headers = {
            "Authorization": f"Bearer {COVEO_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "q": product_number,
            "numberOfResults": 10,
            "sortCriteria": "relevancy",
            "searchHub": "Web_Main_Search_EN",
            "locale": "en-CA",
            "tab": "Products",
            "fieldsToInclude": [
                "clickUri",
                "ec_name",
                "ec_price",
                "ec_skus",
            ],
            "aq": "@ec_visibility==(3,4)",
        }

        url = furl(COVEO_API_URL)
        url.args["organizationId"] = COVEO_ORG_ID

        try:
            response = self.client.post(
                str(url),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                logger.warning("No results found for product number: %s", product_number)
                return None

            # Look for exact match on product number in SKUs or URL
            for result in results:
                click_uri = result.get("clickUri", "")
                ec_skus = result.get("raw", {}).get("ec_skus", [])

                # Check if product number matches SKU or is in URL
                if product_number in ec_skus or product_number in click_uri:
                    normalized_url = normalize_product_url(click_uri)
                    logger.debug("Found product URL: %s", normalized_url)
                    return normalized_url

            # If no exact match, return first result
            first_result = results[0]
            click_uri = first_result.get("clickUri")
            if click_uri:
                normalized_url = normalize_product_url(click_uri)
                logger.debug(
                    "No exact match, using first result: %s", normalized_url
                )
                return normalized_url

            logger.warning(
                "No product URL found in results for: %s", product_number
            )
            return None

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error searching for product %s: %s", product_number, e
            )
            return None
        except httpx.RequestError as e:
            logger.error(
                "Request error searching for product %s: %s", product_number, e
            )
            return None

    def scrape_product_page(self, url: str, product_number: str) -> Product:
        """Scrape product information from a product page.

        Args:
            url: The product page URL.
            product_number: The product number being searched.

        Returns:
            A Product instance with scraped information.
        """
        product = Product(product_number=product_number, url=url)

        try:
            response = self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error fetching product page %s: %s", url, e)
            return product
        except httpx.RequestError as e:
            logger.error("Request error fetching product page %s: %s", url, e)
            return product

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract product name from h1
        h1 = soup.find("h1")
        if h1:
            product.name = h1.get_text(strip=True)

        # Extract price - look for span with class "price"
        # The page has nested spans: span.price-wrapper > span.price
        # We want the innermost span.price that contains just the price
        price_spans = soup.find_all("span", class_="price")
        for price_span in price_spans:
            # Skip if this span contains child spans (it's a wrapper)
            if price_span.find("span"):
                continue
            price_text = price_span.get_text(strip=True)
            # Only take price if it starts with $ (valid price format)
            if price_text.startswith("$"):
                product.price = price_text
                break

        # Extract More Details from the moredetail section
        # Structure: <div class="moredetail"><ul><li><div class="label">Key</div><div class="value">Value</div></li></ul></div>
        details = {}

        moredetail = soup.find("div", class_="moredetail")
        if moredetail:
            for li in moredetail.find_all("li"):
                label_div = li.find("div", class_="label")
                value_div = li.find("div", class_="value")
                if label_div and value_div:
                    key = label_div.get_text(strip=True)
                    value = value_div.get_text(strip=True)
                    if key and value:
                        details[key] = value

        # Fallback: try dt/dd structure
        if not details:
            for dt in soup.find_all("dt"):
                dd = dt.find_next_sibling("dd")
                if dd:
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    if key and value:
                        details[key] = value

        product.details = details

        return product

    def get_product(self, product_number: str) -> Product:
        """Search for and scrape a product by number.

        Args:
            product_number: The LCBO product number.

        Returns:
            A Product instance with all available information.
        """
        url = self.search_product(product_number)
        if not url:
            logger.warning("Product not found: %s", product_number)
            return Product(product_number=product_number)

        return self.scrape_product_page(url, product_number)
