"""Data sources for scheduled tasks.

This module provides source components that fetch data from external APIs
and services for processing by the task pipeline.
"""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

from agentrylab.runtime.tools.base import Tool, ToolResult, ToolError


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


class DataSource(ABC):
    """Abstract base class for data sources.
    
    Sources fetch raw data from external APIs and return it in a
    standardized format for processing by the pipeline.
    """
    
    @abstractmethod
    def fetch_data(self, **params: Any) -> List[Dict[str, Any]]:
        """Fetch raw data from the source.
        
        Args:
            **params: Source-specific parameters (search query, location, etc.)
            
        Returns:
            List of raw data dictionaries from the source
            
        Raises:
            ToolError: If the source fails to fetch data
        """
        pass


class ApifyActorSource(DataSource, Tool):
    """Source for Facebook Marketplace data via Apify actor.
    
    This source uses Apify's Facebook Marketplace scraper actor to fetch
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
            raise ToolError("ApifyActorSource requires 'apify_token' parameter")
    
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the Apify actor and return results.
        
        Args:
            search_query: Search terms for marketplace listings
            location: Location to search in (optional)
            max_results: Override max results for this run
            **kwargs: Additional parameters passed to Apify actor
            
        Returns:
            ToolResult with fetched marketplace data
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
            
            raw_data = self.fetch_data(
                search_query=search_query,
                location=location,
                max_results=max_results,
                **kwargs_copy
            )
            
            return ToolResult(
                ok=True,
                data=raw_data,
                meta={
                    "source": "apify_facebook_marketplace",
                    "actor_id": self.actor_id,
                    "count": len(raw_data),
                    "query": search_query,
                    "location": location,
                }
            )
            
        except Exception as e:
            self.logger.error(f"ApifyActorSource failed: {e}")
            return ToolResult(
                ok=False,
                data=[],
                error=f"Failed to fetch data from Apify: {e}"
            )
    
    def fetch_data(self, **params: Any) -> List[Dict[str, Any]]:
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
        # We need to construct search URLs for Facebook Marketplace
        search_query = params["search_query"]
        location = params.get("location", "")
        
        # Construct Facebook Marketplace search URL
        base_url = "https://www.facebook.com/marketplace/search/"
        search_params = []
        
        if search_query:
            search_params.append(f"query={search_query.replace(' ', '%20')}")
        if location:
            search_params.append(f"location={location.replace(' ', '%20')}")
        
        search_url = base_url + "?" + "&".join(search_params)
        
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
        
        self.logger.info(f"Running Apify actor {self.actor_id} with query: {params['search_query']}")
        
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
