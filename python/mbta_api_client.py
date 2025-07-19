"""MBTA API client for making requests to the MBTA V3 API."""

import requests
import logging
from datetime import datetime
from config import config

class MBTAApiClient:
    """Handles all direct API interactions with the MBTA V3 API."""
    
    def __init__(self, timeout=None):
        self.api_url = "https://api-v3.mbta.com"
        self.api_key = config.api_key
        self.timeout = timeout or config.api_timeout
        self.logger = logging.getLogger('instantmbta.api_client')
    
    def _build_url(self, endpoint, **params):
        """Build API URL with parameters."""
        url = f"{self.api_url}/{endpoint}?api_key={self.api_key}"
        for key, value in params.items():
            url += f"&{key}={value}"
        return url
    
    def get_routes(self, route_id=None):
        """Get route information."""
        endpoint = f"routes/{route_id}" if route_id else "routes"
        url = self._build_url(endpoint)
        self.logger.debug("Getting routes: %s", url)
        return requests.get(url, timeout=self.timeout)
    
    def get_lines(self, line_name):
        """Get line information."""
        url = self._build_url(f"lines/{line_name}")
        self.logger.debug("Getting line: %s", url)
        return requests.get(url, timeout=self.timeout)
    
    def get_stops(self, route_id):
        """Get stops for a route."""
        url = self._build_url("stops", **{"filter[route]": route_id})
        self.logger.debug("Getting stops: %s", url)
        return requests.get(url, timeout=self.timeout)
    
    def get_schedules(self, route_id, stop_id, direction_id, min_time=None):
        """Get schedules for a route/stop/direction."""
        params = {
            "filter[route]": route_id,
            "filter[stop]": stop_id,
            "filter[direction_id]": direction_id,
            "sort": "departure_time"
        }
        if min_time:
            params["filter[min_time]"] = min_time
        url = self._build_url("schedules", **params)
        self.logger.debug("Getting schedules: %s", url)
        return requests.get(url, timeout=self.timeout)
    
    def get_predictions(self, route_id=None, stop_id=None, direction_id=None):
        """Get predictions."""
        params = {"sort": "departure_time"}
        if route_id:
            params["filter[route]"] = route_id
        if stop_id:
            params["filter[stop]"] = stop_id
        if direction_id:
            params["filter[direction_id]"] = direction_id
        url = self._build_url("predictions", **params)
        self.logger.debug("Getting predictions: %s", url)
        return requests.get(url, timeout=self.timeout) 