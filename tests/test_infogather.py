import unittest
from unittest.mock import patch, MagicMock
import requests
from infogather import InfoGather
from circuit_breaker import CircuitBreaker
import time
from datetime import datetime

class TestInfoGather(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.ig = InfoGather()
        # Mock the logger to prevent actual logging during tests
        self.ig.logger = MagicMock()

    def test_verify_connection_success(self):
        """Test successful connection verification."""
        with patch.object(self.ig.api_client, 'get_routes') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = self.ig.verify_connection()
            
            self.assertTrue(result)
            self.assertEqual(self.ig.consecutive_failures, 0)
            self.assertIsNotNone(self.ig.last_successful_request)

    def test_verify_connection_failure(self):
        """Test failed connection verification."""
        with patch.object(self.ig.api_client, 'get_routes') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")

            result = self.ig.verify_connection()
            
            self.assertFalse(result)
            self.assertEqual(self.ig.consecutive_failures, 1)
            self.assertIsNone(self.ig.last_successful_request)

    def test_make_api_request_with_retries(self):
        """Test API request with retry logic."""
        def test_func():
            return "success"
            
        with patch.object(self.ig, 'verify_connection') as mock_verify:
            # First two attempts fail, then always succeed
            mock_verify.side_effect = [False, False, True, True, True, True]
            
            # Should succeed on third attempt
            result = self.ig._make_api_request(test_func)
            
            # Verify the number of attempts
            self.assertGreaterEqual(mock_verify.call_count, 3)
            
            # Verify the result
            self.assertEqual(result, "success")

    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1)
        
        # Simulate a failing function
        def failing_func():
            raise Exception("Test failure")

        # First failure
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.failures, 1)
        self.assertEqual(cb.state, "CLOSED")

        # Second failure should open the circuit
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.failures, 2)
        self.assertEqual(cb.state, "OPEN")

        # Circuit should be open
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.state, "OPEN")

        # Wait for reset timeout
        time.sleep(1.1)
        # Call execute to trigger HALF-OPEN state, but since it fails, state returns to OPEN
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.state, "OPEN")
        
        # Now, after timeout, a successful call should close the circuit
        time.sleep(1.1)
        def success_func(*args, **kwargs):
            return "success"
        result = cb.execute(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, "CLOSED")

    def test_exponential_backoff(self):
        """Test exponential backoff in retry logic."""
        def test_func():
            raise Exception("Test error")
            
        with patch.object(self.ig, 'verify_connection', return_value=False):
            with patch('time.sleep') as mock_sleep:
                try:
                    self.ig._make_api_request(test_func)
                except Exception:
                    pass
                
                # Verify sleep calls with exponential backoff
                expected_sleeps = [5, 10, 20, 40]  # 5 * 2^n for 4 attempts
                actual_sleeps = [call[0][0] for call in mock_sleep.call_args_list]
                self.assertEqual(actual_sleeps, expected_sleeps)

    def test_consecutive_failures_reset(self):
        """Test that consecutive failures counter resets on success."""
        with patch.object(self.ig.api_client, 'get_routes') as mock_get:
            # Simulate failure then success
            mock_get.side_effect = [
                requests.exceptions.RequestException("Failure"),
                MagicMock()
            ]
            
            # First attempt fails
            self.ig.verify_connection()
            self.assertEqual(self.ig.consecutive_failures, 1)
            
            # Reset the mock for the second attempt
            mock_get.reset_mock()
            mock_get.return_value = MagicMock()
            
            # Second attempt succeeds
            self.ig.verify_connection()
            self.assertEqual(self.ig.consecutive_failures, 0)

    def test_get_line(self):
        """Test get_line method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response
            
            result = self.ig.get_line("Red")
            
            mock_request.assert_called_once()
            self.assertEqual(result, mock_response)
            # Verify the method call
            call_args = mock_request.call_args[0]
            self.assertEqual(call_args[0], self.ig.api_client.get_lines)
            self.assertEqual(call_args[1], "Red")

    def test_get_routes(self):
        """Test get_routes method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response
            
            result = self.ig.get_routes("Red")
            
            mock_request.assert_called_once()
            self.assertEqual(result, mock_response)
            # Verify the method call
            call_args = mock_request.call_args[0]
            self.assertEqual(call_args[0], self.ig.api_client.get_routes)
            self.assertEqual(call_args[1], "Red")

    def test_get_schedule(self):
        """Test get_schedule method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            with patch.object(self.ig.schedule_processor, 'get_current_time', return_value="14:30"):
                mock_response = MagicMock()
                mock_request.return_value = mock_response
                
                result = self.ig.get_schedule("Red", "stop1", "0")
                
                mock_request.assert_called_once()
                self.assertEqual(result, mock_response)
                # Verify the method call
                call_args = mock_request.call_args[0]
                self.assertEqual(call_args[0], self.ig.api_client.get_schedules)
                self.assertEqual(call_args[1], "Red")
                self.assertEqual(call_args[2], "stop1")
                self.assertEqual(call_args[3], "0")
                self.assertEqual(call_args[4], "14:30")

    def test_get_predictions(self):
        """Test get_predictions method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response
            
            result = self.ig.get_predictions("stop1", "0")
            
            mock_request.assert_called_once()
            self.assertEqual(result, mock_response)
            # Verify the method call
            call_args = mock_request.call_args
            self.assertEqual(call_args[0][0], self.ig.api_client.get_predictions)
            self.assertEqual(call_args[1]['stop_id'], "stop1")
            self.assertEqual(call_args[1]['direction_id'], "0")

    def test_get_stops(self):
        """Test get_stops method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_request.return_value = mock_response
            
            result = self.ig.get_stops("Red")
            
            mock_request.assert_called_once()
            self.assertEqual(result, mock_response)
            # Verify the method call
            call_args = mock_request.call_args[0]
            self.assertEqual(call_args[0], self.ig.api_client.get_stops)
            self.assertEqual(call_args[1], "Red")

    def test_get_current_time(self):
        """Test get_current_time method."""
        with patch('schedule_processor.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "14:30"
            
            result = self.ig.get_current_time()
            
            self.assertEqual(result, "14:30")
            mock_datetime.now.assert_called_once()

    def test_find_prediction_by_id_found(self):
        """Test find_prediction_by_id when prediction is found."""
        predictions = {
            'data': [
                {'id': 'pred1', 'attributes': {'time': '10:00'}},
                {'id': 'pred2', 'attributes': {'time': '10:15'}}
            ]
        }
        
        result = self.ig.find_prediction_by_id('pred1', predictions)
        
        self.assertEqual(result, {'id': 'pred1', 'attributes': {'time': '10:00'}})

    def test_find_prediction_by_id_not_found(self):
        """Test find_prediction_by_id when prediction is not found."""
        predictions = {
            'data': [
                {'id': 'pred1', 'attributes': {'time': '10:00'}},
                {'id': 'pred2', 'attributes': {'time': '10:15'}}
            ]
        }
        
        # Mock the schedule processor logger
        with patch.object(self.ig.schedule_processor, 'logger') as mock_logger:
            result = self.ig.find_prediction_by_id('pred3', predictions)
            
            self.assertIsNone(result)
            mock_logger.error.assert_called_once()

    def test_get_current_schedule_api_failure(self):
        """Test get_current_schedule when API requests fail."""
        with patch.object(self.ig, '_make_api_request', return_value=None):
            result = self.ig.get_current_schedule("Red", "stop1")
            
            self.assertEqual(result, (None, None, None, None))

    def test_get_current_schedule_empty_response(self):
        """Test get_current_schedule with empty API responses."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': []}
        
        with patch.object(self.ig, '_make_api_request', return_value=mock_response):
            result = self.ig.get_current_schedule("Red", "stop1")
            
            # Should return None values for all times
            self.assertEqual(result, (None, None, None, None))

    def test_get_current_schedule_exception_handling(self):
        """Test get_current_schedule exception handling."""
        with patch.object(self.ig, '_make_api_request', side_effect=Exception("API Error")):
            result = self.ig.get_current_schedule("Red", "stop1")
            
            self.assertEqual(result, (None, None, None, None))
            self.ig.logger.error.assert_called_once()

if __name__ == '__main__':
    unittest.main() 