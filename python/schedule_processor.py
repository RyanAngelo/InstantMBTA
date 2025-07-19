"""Schedule processor for handling MBTA schedule data and time calculations."""

import logging
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

class ScheduleProcessor:
    """Handles processing of MBTA schedule and prediction data."""
    
    def __init__(self):
        self.logger = logging.getLogger('instantmbta.schedule_processor')
    
    def get_current_time(self) -> str:
        """Get current time in HH:MM format."""
        return datetime.now().strftime('%H:%M')
    
    def get_current_datetime(self) -> datetime:
        """Get current datetime with timezone."""
        return datetime.now().astimezone()
    
    def find_prediction_by_id(self, prediction_id: str, predictions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a prediction by ID in the predictions data."""
        if 'data' not in predictions:
            return None
            
        prediction_map = {pred['id']: pred for pred in predictions['data']}
        prediction = prediction_map.get(prediction_id)
        
        if prediction is None:
            self.logger.error("No prediction found for ID: %s", prediction_id)
        
        return prediction
    
    def extract_next_times(self, predicted_data: Dict[str, Any], scheduled_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract next arrival and departure times from API responses.
        
        Returns:
            Tuple of (inbound_arrival, outbound_arrival, inbound_departure, outbound_departure)
        """
        current_time = self.get_current_datetime()
        current_date = current_time.date()
        
        # Initialize result variables
        next_inbound_arrival = None
        next_outbound_arrival = None
        next_inbound_departure = None
        next_outbound_departure = None
        
        # Process predicted times
        if 'data' in predicted_data:
            for prediction in predicted_data['data']:
                if 'attributes' not in prediction:
                    continue
                    
                attrs = prediction['attributes']
                departure_time = attrs.get('departure_time')
                arrival_time = attrs.get('arrival_time')
                
                if not (departure_time or arrival_time):
                    continue
                
                try:
                    dt = datetime.fromisoformat(departure_time or arrival_time)
                    if dt > current_time and dt.date() == current_date:
                        direction_id = attrs.get('direction_id', 0)
                        
                        if direction_id == 0:  # Inbound
                            if next_inbound_departure is None:
                                next_inbound_departure = departure_time or arrival_time
                            if next_inbound_arrival is None and arrival_time:
                                next_inbound_arrival = arrival_time
                        else:  # Outbound
                            if next_outbound_departure is None:
                                next_outbound_departure = departure_time or arrival_time
                            if next_outbound_arrival is None and arrival_time:
                                next_outbound_arrival = arrival_time
                except ValueError as e:
                    self.logger.warning("Invalid datetime format: %s", e)
                    continue
        
        # Use arrival time as departure time if no departure time is available
        if next_inbound_departure is None and next_inbound_arrival is not None:
            next_inbound_departure = next_inbound_arrival
        if next_outbound_departure is None and next_outbound_arrival is not None:
            next_outbound_departure = next_outbound_arrival
        
        return (next_inbound_arrival, next_outbound_arrival, 
                next_inbound_departure, next_outbound_departure) 