"""Refactored InfoGather class using separated concerns."""

import logging
import time
from mbta_api_client import MBTAApiClient
from schedule_processor import ScheduleProcessor
from circuit_breaker import CircuitBreaker

class InfoGather:
    """
    Coordinates MBTA API interactions with error handling and retry logic.
    Uses separate classes for API calls, data processing, and circuit breaker.
    """

    def __init__(self, max_retries=None, base_retry_delay=None):
        from config import config
        
        self.logger = logging.getLogger('instantmbta.infogather')
        self.circuit_breaker = CircuitBreaker()
        self.api_client = MBTAApiClient()
        self.schedule_processor = ScheduleProcessor()
        
        self.last_successful_request = None
        self.consecutive_failures = 0
        self.max_retries = max_retries or config.max_retries
        self.base_retry_delay = base_retry_delay or config.retry_delay

    def verify_connection(self) -> bool:
        """Verify connection to the MBTA API."""
        try:
            response = self.api_client.get_routes()
            response.raise_for_status()
            self.last_successful_request = time.time()
            self.consecutive_failures = 0
            return True
        except Exception as e:
            self.logger.warning("Connection verification failed: %s", e)
            self.consecutive_failures += 1
            return False

    def _make_api_request(self, request_func, *args, **kwargs):
        """Make an API request with circuit breaker protection and retry logic."""
        retry_delay = self.base_retry_delay
        
        for attempt in range(self.max_retries):
            try:
                if not self.verify_connection():
                    if attempt < self.max_retries - 1:
                        self.logger.info("Waiting %d seconds before retry %d/%d", 
                                       retry_delay, attempt + 1, self.max_retries)
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise Exception("Max retries exceeded")
                
                return self.circuit_breaker.execute(request_func, *args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error("Circuit breaker prevented request after %d retries: %s", 
                                    self.max_retries, e)
                    raise
                retry_delay *= 2  # Exponential backoff

    # API Methods - now delegate to API client
    def get_line(self, line_name):
        """Get information for a specific line."""
        return self._make_api_request(self.api_client.get_lines, line_name)

    def get_routes(self, route_id):
        """Get information for a specific route."""
        return self._make_api_request(self.api_client.get_routes, route_id)

    def get_schedule(self, route_id, stop_id, direction_id):
        """Get the schedule given a route, stop and direction."""
        current_time = self.schedule_processor.get_current_time()
        return self._make_api_request(
            self.api_client.get_schedules, 
            route_id, stop_id, direction_id, current_time
        )

    def get_predictions(self, stop_id, direction_id):
        """Get predictions for a stop and direction."""
        return self._make_api_request(
            self.api_client.get_predictions, 
            stop_id=stop_id, direction_id=direction_id
        )

    def get_stops(self, route_id):
        """Get stops for a route."""
        return self._make_api_request(self.api_client.get_stops, route_id)

    # Utility methods - now delegate to schedule processor
    def get_current_time(self):
        """Get the current time of the system."""
        return self.schedule_processor.get_current_time()

    def find_prediction_by_id(self, prediction_id, predictions):
        """Find a prediction by ID."""
        return self.schedule_processor.find_prediction_by_id(prediction_id, predictions)

    def get_current_schedule(self, route_id, stop_id):
        """Get current schedule for a route and stop."""
        try:
            # Get predicted times
            predicted_response = self._make_api_request(
                self.api_client.get_predictions, 
                route_id=route_id, stop_id=stop_id
            )
            
            if predicted_response is None:
                self.logger.error(f"Failed to get predicted times for route {route_id} at stop {stop_id}")
                return None, None, None, None
                
            predicted_data = predicted_response.json()
            self.logger.debug(f"Predicted times response: {predicted_data}")
            
            # Get scheduled times
            scheduled_response = self._make_api_request(
                self.api_client.get_predictions, 
                route_id=route_id, stop_id=stop_id
            )
            
            if scheduled_response is None:
                self.logger.error(f"Failed to get scheduled times for route {route_id} at stop {stop_id}")
                return None, None, None, None
                
            scheduled_data = scheduled_response.json()
            self.logger.debug(f"Scheduled times response: {scheduled_data}")

            # Process the data using the schedule processor
            return self.schedule_processor.extract_next_times(predicted_data, scheduled_data)
                    
        except Exception as e:
            self.logger.error(f"Error getting schedule for route {route_id} at stop {stop_id}: {str(e)}")
            return None, None, None, None 