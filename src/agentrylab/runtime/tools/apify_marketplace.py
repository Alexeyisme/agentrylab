"""Apify Facebook Marketplace tool for agentrylab.

This tool provides access to Facebook Marketplace data via Apify's scraper actor.
It includes data normalization to convert raw marketplace data into a standardized format.
"""

from __future__ import annotations

import re
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from .base import Tool, ToolError, ToolResult


@dataclass
class Listing:
    """Standardized listing format for marketplace data.
    
    This dataclass ensures consistent data structure across different
    marketplace sources (Facebook, eBay, Craigslist, etc.).
    """
    id: str
    title: str
    price: float
    currency: str
    url: str
    images: List[str] = field(default_factory=list)
    posted_at: Optional[datetime] = None
    location: Optional[Dict[str, Any]] = None  # {city, lat, lon, distance_km}
    seller: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None  # Original source data


class ListingNormalizer(ABC):
    """Abstract base class for listing normalizers.
    
    Normalizers convert raw data from sources into standardized Listing objects.
    Different sources may require different normalization logic.
    """
    
    @abstractmethod
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Listing]:
        """Normalize raw data into Listing objects.
        
        Args:
            raw_data: List of raw data dictionaries from source
            
        Returns:
            List of normalized Listing objects
        """
        raise NotImplementedError


class FacebookMarketplaceNormalizer(ListingNormalizer):
    """Normalizer for Facebook Marketplace data from Apify actor.
    
    This normalizer handles the specific data structure returned by the
    Facebook Marketplace scraper actor and converts it to standardized
    Listing objects.
    """
    
    def __init__(self, **params: Any):
        self.logger = logging.getLogger(__name__)
        self.params = params
    
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Listing]:
        """Normalize Facebook Marketplace data to Listing objects.
        
        Args:
            raw_data: Raw data from Apify Facebook Marketplace actor
            
        Returns:
            List of normalized Listing objects
        """
        normalized = []
        
        for item in raw_data:
            try:
                listing = self._normalize_item(item)
                if listing:
                    normalized.append(listing)
            except Exception as e:
                self.logger.warning(f"Failed to normalize item: {e}")
                continue
        
        self.logger.info(f"Normalized {len(normalized)} items from {len(raw_data)} raw items")
        return normalized
    
    def _normalize_item(self, item: Dict[str, Any]) -> Optional[Listing]:
        """Normalize a single marketplace item.
        
        Args:
            item: Raw marketplace item data
            
        Returns:
            Normalized Listing object or None if item is invalid
        """
        # Extract basic fields
        listing_id = self._extract_id(item)
        title = self._extract_title(item)
        price = self._extract_price(item)
        currency = self._extract_currency(item)
        url = self._extract_url(item)
        
        if not all([listing_id, title, price, currency, url]):
            self.logger.debug(f"Skipping item with missing required fields: {item.get('title', 'unknown')}")
            return None
        
        # Extract optional fields
        images = self._extract_images(item)
        posted_at = self._extract_posted_at(item)
        location = self._extract_location(item)
        seller = self._extract_seller(item)
        
        return Listing(
            id=listing_id,
            title=title,
            price=price,
            currency=currency,
            url=url,
            images=images,
            posted_at=posted_at,
            location=location,
            seller=seller,
            raw_data=item
        )
    
    def _extract_id(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract unique ID from marketplace item."""
        # Try different possible ID fields (Apify format)
        for field in ["id", "listingId", "listingUrl"]:
            if field in item and item[field]:
                value = item[field]
                if field == "listingUrl":
                    # Extract ID from listing URL
                    match = re.search(r"/item/(\d+)", str(value))
                    if match:
                        return match.group(1)
                return str(value)
        
        # Fallback: use URL as ID
        url = item.get("listingUrl") or item.get("facebookUrl")
        if url:
            # Extract ID from URL if possible
            match = re.search(r"/(\d+)/", str(url))
            if match:
                return match.group(1)
            return str(url)
        
        return None
    
    def _extract_title(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract title from marketplace item."""
        # Try Apify Facebook Marketplace fields
        title = (item.get("marketplace_listing_title") or 
                item.get("custom_title") or 
                item.get("title") or 
                item.get("name") or 
                item.get("text"))
        if title:
            return str(title).strip()
        return None
    
    def _extract_price(self, item: Dict[str, Any]) -> Optional[float]:
        """Extract price from marketplace item."""
        # Try Apify Facebook Marketplace price fields
        price_data = item.get("listing_price")
        if price_data and isinstance(price_data, dict):
            # Try formatted_amount first, then amount
            price_str = price_data.get("formatted_amount") or price_data.get("amount")
        else:
            # Fallback to direct fields
            price_str = item.get("price") or item.get("priceText") or item.get("formatted_amount")
        
        if not price_str:
            return None
        
        # Clean price string and extract number
        price_str = str(price_str).strip()
        
        # Remove currency symbols and common text
        price_str = re.sub(r"[^\d.,]", "", price_str)
        price_str = price_str.replace(",", "")
        
        try:
            return float(price_str)
        except (ValueError, TypeError):
            self.logger.debug(f"Could not parse price: {price_str}")
            return None
    
    def _extract_currency(self, item: Dict[str, Any]) -> str:
        """Extract currency from marketplace item."""
        # Try Apify Facebook Marketplace price fields
        price_data = item.get("listing_price")
        if price_data and isinstance(price_data, dict):
            price_text = price_data.get("formatted_amount", "")
        else:
            price_text = item.get("price") or item.get("priceText", "")
        
        if not price_text:
            return "USD"  # Default currency
        
        price_text = str(price_text).upper()
        
        # Common currency symbols and codes
        currency_map = {
            "$": "USD",
            "€": "EUR", 
            "£": "GBP",
            "₪": "ILS",
            "₽": "RUB",
            "¥": "JPY",
            "USD": "USD",
            "EUR": "EUR",
            "GBP": "GBP",
            "ILS": "ILS",
            "RUB": "RUB",
            "JPY": "JPY",
        }
        
        for symbol, currency in currency_map.items():
            if symbol in price_text:
                return currency
        
        return "USD"  # Default fallback
    
    def _extract_url(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract URL from marketplace item."""
        # Try Apify Facebook Marketplace URL fields
        url = (item.get("listingUrl") or 
               item.get("facebookUrl") or 
               item.get("url") or 
               item.get("link"))
        if url:
            return str(url).strip()
        return None
    
    def _extract_images(self, item: Dict[str, Any]) -> List[str]:
        """Extract image URLs from marketplace item."""
        images = []
        
        # Try Apify Facebook Marketplace image fields
        primary_photo = item.get("primary_listing_photo")
        if primary_photo and isinstance(primary_photo, dict):
            photo_url = primary_photo.get("photo_image_url")
            if photo_url:
                images.append(photo_url)
        
        # Try other possible image fields
        image_fields = ["images", "imageUrls", "photos", "picture"]
        
        for field in image_fields:
            if field in item and item[field]:
                if isinstance(item[field], list):
                    images.extend([str(img) for img in item[field] if img])
                elif isinstance(item[field], str):
                    images.append(item[field])
        
        # Remove duplicates and empty strings
        return list(set(filter(None, images)))
    
    def _extract_posted_at(self, item: Dict[str, Any]) -> Optional[datetime]:
        """Extract posting date from marketplace item."""
        date_fields = ["postedAt", "createdAt", "date", "timestamp"]
        
        for field in date_fields:
            if field in item and item[field]:
                try:
                    date_value = item[field]
                    if isinstance(date_value, (int, float)):
                        # Unix timestamp
                        return datetime.fromtimestamp(date_value)
                    elif isinstance(date_value, str):
                        # Try to parse various date formats
                        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                            try:
                                return datetime.strptime(date_value, fmt)
                            except ValueError:
                                continue
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_location(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract location information from marketplace item."""
        location = {}
        
        # Try Apify Facebook Marketplace location structure
        location_data = item.get("location")
        if location_data and isinstance(location_data, dict):
            reverse_geocode = location_data.get("reverse_geocode")
            if reverse_geocode and isinstance(reverse_geocode, dict):
                city = reverse_geocode.get("city")
                state = reverse_geocode.get("state")
                if city:
                    location["city"] = str(city).strip()
                if state:
                    location["state"] = str(state).strip()
                
                # Try to get full location name
                city_page = reverse_geocode.get("city_page")
                if city_page and isinstance(city_page, dict):
                    display_name = city_page.get("display_name")
                    if display_name:
                        location["full_name"] = str(display_name).strip()
        
        # Fallback to direct fields
        if not location:
            city = item.get("city") or item.get("area")
            if city:
                location["city"] = str(city).strip()
        
        # Extract coordinates if available
        lat = item.get("latitude") or item.get("lat")
        lon = item.get("longitude") or item.get("lng") or item.get("lon")
        
        if lat is not None and lon is not None:
            try:
                location["lat"] = float(lat)
                location["lon"] = float(lon)
            except (ValueError, TypeError):
                pass
        
        # Extract distance if available
        distance = item.get("distance") or item.get("distanceKm")
        if distance is not None:
            try:
                location["distance_km"] = float(distance)
            except (ValueError, TypeError):
                pass
        
        return location if location else None
    
    def _extract_seller(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract seller information from marketplace item."""
        seller = {}
        
        # Try Apify Facebook Marketplace seller fields
        seller_data = item.get("marketplace_listing_seller")
        if seller_data and isinstance(seller_data, dict):
            seller_name = seller_data.get("name") or seller_data.get("display_name")
            if seller_name:
                seller["name"] = str(seller_name).strip()
            
            seller_url = seller_data.get("url") or seller_data.get("profile_url")
            if seller_url:
                seller["url"] = str(seller_url).strip()
        
        # Fallback to direct fields
        if not seller:
            seller_name = item.get("sellerName") or item.get("seller") or item.get("author")
            if seller_name:
                seller["name"] = str(seller_name).strip()
            
            seller_url = item.get("sellerUrl") or item.get("sellerProfile")
            if seller_url:
                seller["url"] = str(seller_url).strip()
        
        # Extract seller rating if available
        rating = item.get("sellerRating") or item.get("rating")
        if rating is not None:
            try:
                seller["rating"] = float(rating)
            except (ValueError, TypeError):
                pass
        
        return seller if seller else None


class ApifyMarketplaceTool(Tool):
    """Tool for Facebook Marketplace data via Apify actor.
    
    This tool uses Apify's Facebook Marketplace scraper actor to fetch
    marketplace listings. It handles authentication, rate limiting, and
    data normalization.
    
    Configuration:
        actor_id: Apify actor ID (default: "apify/facebook-marketplace-scraper")
        apify_token: Apify API token (from environment or config)
        timeout_s: Request timeout in seconds (default: 300)
        max_results: Maximum number of results to fetch (default: 100)
        retries: Number of retry attempts (default: 3)
        backoff: Backoff multiplier for retries (default: 2.0)
    """
    
    def __init__(self, **params: Any):
        super().__init__(**params)
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.actor_id = params.get("actor_id", "apify/facebook-marketplace-scraper")
        self.apify_token = params.get("apify_token")
        self.timeout_s = int(params.get("timeout_s", 300))
        self.max_results = int(params.get("max_results", 100))
        self.retries = int(params.get("retries", 3))
        self.backoff = float(params.get("backoff", 2.0))
        
        if not self.apify_token:
            raise ToolError("ApifyMarketplaceTool requires 'apify_token' parameter")
        
        # Initialize normalizer
        self.normalizer = FacebookMarketplaceNormalizer(**params)
    
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the Apify actor and return normalized results.
        
        Args:
            search_query: Search terms for marketplace listings
            location: Location to search in (optional)
            max_results: Override max results for this run
            **kwargs: Additional parameters passed to Apify actor
            
        Returns:
            ToolResult with normalized marketplace data
        """
        search_query = kwargs.get("search_query", "")
        location = kwargs.get("location")
        max_results = kwargs.get("max_results", self.max_results)
        
        if not search_query:
            return ToolResult(
                ok=False,
                data=[],
                error="search_query parameter is required"
            )
        
        try:
            # Remove search_query from kwargs to avoid duplicate parameter
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop("search_query", None)
            kwargs_copy.pop("location", None)
            kwargs_copy.pop("max_results", None)
            
            raw_data = self._fetch_data(
                search_query=search_query,
                location=location,
                max_results=max_results,
                **kwargs_copy
            )
            
            # Normalize the data
            normalized_listings = self.normalizer.normalize(raw_data)
            
            # Convert to dict format for tool result
            data = []
            for listing in normalized_listings:
                data.append({
                    "id": listing.id,
                    "title": listing.title,
                    "price": listing.price,
                    "currency": listing.currency,
                    "url": listing.url,
                    "images": listing.images,
                    "posted_at": listing.posted_at.isoformat() if listing.posted_at else None,
                    "location": listing.location,
                    "seller": listing.seller,
                })
            
            return ToolResult(
                ok=True,
                data=data,
                meta={
                    "provider": "apify_facebook_marketplace",
                    "actor_id": self.actor_id,
                    "count": len(data),
                    "query": search_query,
                    "location": location,
                }
            )
            
        except Exception as e:
            self.logger.error(f"ApifyMarketplaceTool failed: {e}")
            return ToolResult(
                ok=False,
                data=[],
                error=f"Failed to fetch data from Apify: {e}"
            )
    
    def _fetch_data(self, **params: Any) -> List[Dict[str, Any]]:
        """Fetch data from Apify Facebook Marketplace actor.
        
        Args:
            search_query: Search terms
            location: Location filter (optional)
            max_results: Maximum results to return
            **params: Additional actor parameters
            
        Returns:
            List of raw marketplace listing data
            
        Raises:
            ToolError: If the actor fails or returns no data
        """
        try:
            from apify_client import ApifyClient
        except ImportError:
            raise ToolError(
                "apify-client package is required. Install with: pip install apify-client"
            )
        
        # Initialize Apify client
        client = ApifyClient(self.apify_token)
        
        # Prepare actor input - Facebook Marketplace scraper requires startUrls
        search_query = params["search_query"]
        location = params.get("location", "")
        
        # Construct Facebook Marketplace search URL
        search_url = self._build_search_url(search_query, location)
        
        actor_input = {
            "startUrls": [{"url": search_url}],
            "maxResults": min(int(params.get("max_results", self.max_results)), 1000),
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        # Add any additional parameters
        for key, value in params.items():
            if key not in ["search_query", "location", "max_results"] and value is not None:
                actor_input[key] = value
        
        self.logger.info(f"Running Apify actor {self.actor_id} with query: {search_query}")
        
        # Run the actor with retries
        for attempt in range(self.retries + 1):
            try:
                # Start the actor run
                run = client.actor(self.actor_id).call(
                    run_input=actor_input,
                    timeout_secs=self.timeout_s,
                    wait_secs=10
                )
                
                if not run or not run.get("defaultDatasetId"):
                    raise ToolError("Apify actor run failed or returned no dataset")
                
                # Fetch results from dataset
                dataset = client.dataset(run["defaultDatasetId"])
                items = list(dataset.iterate_items())
                
                if not items:
                    self.logger.warning("Apify actor returned no results")
                    return []
                
                self.logger.info(f"Fetched {len(items)} items from Apify actor")
                return items
                
            except Exception as e:
                if attempt < self.retries:
                    wait_time = self.backoff ** attempt
                    self.logger.warning(
                        f"Apify actor attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise ToolError(f"Apify actor failed after {self.retries + 1} attempts: {e}")
        
        return []  # Should never reach here, but for type safety
    
    def _build_search_url(self, search_query: str, location: str = "") -> str:
        """Build Facebook Marketplace search URL.
        
        Args:
            search_query: Search terms
            location: Location filter (optional)
            
        Returns:
            Complete Facebook Marketplace search URL
        """
        base_url = "https://www.facebook.com/marketplace/search/"
        params = {}
        
        if search_query:
            params["query"] = search_query
        if location:
            params["location"] = location
        
        if params:
            return base_url + "?" + urlencode(params)
        return base_url
    
    def validate_args(self, kwargs: Dict[str, Any]) -> None:
        """Validate input arguments for the Apify actor.
        
        Args:
            kwargs: Arguments to validate
            
        Raises:
            ToolError: If arguments are invalid
        """
        if not kwargs.get("search_query"):
            raise ToolError("search_query is required")
        
        max_results = kwargs.get("max_results", self.max_results)
        if max_results > 1000:
            raise ToolError("max_results cannot exceed 1000 (Apify limit)")
        
        if max_results <= 0:
            raise ToolError("max_results must be positive")


