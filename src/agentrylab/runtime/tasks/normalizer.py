"""Data normalization components for scheduled tasks.

This module provides components that normalize raw data from different sources
into standardized formats for processing by the task pipeline.
"""

from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .sources import Listing


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
        pass


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


class UniversalNormalizer(ListingNormalizer):
    """Universal normalizer that can handle multiple source formats.
    
    This normalizer attempts to extract common fields from any data source
    using flexible field mapping. It's useful for prototyping or when
    dealing with multiple different source formats.
    """
    
    def __init__(self, field_mapping: Optional[Dict[str, str]] = None, **params: Any):
        self.logger = logging.getLogger(__name__)
        self.field_mapping = field_mapping or {
            "id": ["id", "listingId", "url"],
            "title": ["title", "name", "text", "heading"],
            "price": ["price", "priceText", "amount"],
            "url": ["url", "link", "href"],
            "images": ["images", "imageUrls", "photos"],
            "location": ["location", "city", "area"],
        }
        self.params = params
    
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Listing]:
        """Normalize data using flexible field mapping.
        
        Args:
            raw_data: List of raw data dictionaries
            
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
        
        return normalized
    
    def _normalize_item(self, item: Dict[str, Any]) -> Optional[Listing]:
        """Normalize a single item using field mapping."""
        # Extract fields using mapping
        id_value = self._extract_field(item, self.field_mapping["id"])
        title = self._extract_field(item, self.field_mapping["title"])
        price_str = self._extract_field(item, self.field_mapping["price"])
        url = self._extract_field(item, self.field_mapping["url"])
        
        if not all([id_value, title, url]):
            return None
        
        # Parse price
        price = self._parse_price(price_str) if price_str else 0.0
        currency = self._extract_currency(item, price_str)
        
        # Extract other fields
        images = self._extract_images(item)
        location = self._extract_location(item)
        
        return Listing(
            id=str(id_value),
            title=str(title),
            price=price,
            currency=currency,
            url=str(url),
            images=images,
            location=location,
            raw_data=item
        )
    
    def _extract_field(self, item: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """Extract field value using list of possible field names."""
        for field_name in field_names:
            if field_name in item and item[field_name]:
                return str(item[field_name]).strip()
        return None
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float."""
        if not price_str:
            return 0.0
        
        # Clean price string
        price_str = re.sub(r"[^\d.,]", "", str(price_str))
        price_str = price_str.replace(",", "")
        
        try:
            return float(price_str)
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_currency(self, item: Dict[str, Any], price_str: Optional[str]) -> str:
        """Extract currency from item or price string."""
        if price_str:
            price_str = str(price_str).upper()
            if "$" in price_str:
                return "USD"
            elif "€" in price_str:
                return "EUR"
            elif "₪" in price_str:
                return "ILS"
        
        return "USD"  # Default
    
    def _extract_images(self, item: Dict[str, Any]) -> List[str]:
        """Extract images from item."""
        images = []
        for field in self.field_mapping["images"]:
            if field in item and item[field]:
                if isinstance(item[field], list):
                    images.extend([str(img) for img in item[field] if img])
                elif isinstance(item[field], str):
                    images.append(item[field])
        return list(set(filter(None, images)))
    
    def _extract_location(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract location from item."""
        for field in self.field_mapping["location"]:
            if field in item and item[field]:
                return {"city": str(item[field]).strip()}
        return None
