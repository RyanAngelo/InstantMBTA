import unittest
from unittest.mock import patch, MagicMock
import requests
from instantmbta import run_display_loop, setup_logging
import time
import logging
import platform

class TestInstantMBTA(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.ig = MagicMock()
        self.it = MagicMock()
        self.logger = MagicMock()
        self.route_id = "test_route"
        self.route_name = "Test Route"
        self.stop1 = "stop1"
        self.stop1_name = "Stop 1"
        self.stop2 = "stop2"
        self.stop2_name = "Stop 2"

    def test_successful_update(self):
        """Test successful display update."""
        # Mock successful schedule retrieval
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run one iteration of the loop
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [Exception("Break loop")]  # Break after first iteration
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was updated
        self.it.draw_inbound_outbound.assert_called_once()
        self.assertEqual(self.ig.get_current_schedule.call_count, 2)

    def test_network_error_handling(self):
        """Test handling of network errors with exponential backoff."""
        # Mock network error followed by success
        self.ig.get_current_schedule.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify error was logged
        self.logger.error.assert_called()
        
        # Verify exponential backoff was used
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertTrue(sleep_calls[0] < sleep_calls[1])  # Second wait should be longer

    def test_consecutive_failures(self):
        """Test handling of consecutive failures."""
        # Mock continuous network errors
        self.ig.get_current_schedule.side_effect = requests.exceptions.RequestException("Network error")

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify error was logged multiple times
        self.assertGreater(self.logger.error.call_count, 1)
        
        # Verify display was not updated
        self.it.draw_inbound_outbound.assert_not_called()

    def test_display_update_conditions(self):
        """Test conditions that trigger display updates."""
        # Mock schedule data
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35"),  # stop2
            ("10:00", "11:00", "10:05", "11:05"),  # stop1 (unchanged)
            ("10:30", "11:30", "10:35", "11:35")   # stop2 (unchanged)
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was only updated once
        self.assertEqual(self.it.draw_inbound_outbound.call_count, 1)

    def test_display_update_when_times_change(self):
        """Test that display updates when times change."""
        # Mock schedule data with changes
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35"),  # stop2
            ("10:15", "11:00", "10:05", "11:05"),  # stop1 (inbound arrival changed)
            ("10:30", "11:30", "10:35", "11:35")   # stop2 (unchanged)
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was updated twice (initial + change)
        self.assertEqual(self.it.draw_inbound_outbound.call_count, 2)

    def test_display_update_when_outbound_departure_changes(self):
        """Test that display updates when outbound departure time changes."""
        # Mock schedule data with outbound departure change
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35"),  # stop2
            ("10:00", "11:00", "10:05", "11:05"),  # stop1 (unchanged)
            ("10:30", "11:30", "10:35", "11:40")   # stop2 (outbound departure changed)
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was updated twice (initial + change)
        self.assertEqual(self.it.draw_inbound_outbound.call_count, 2)

    def test_no_display_when_it_is_none(self):
        """Test that no display update occurs when it (InkyTrain) is None."""
        # Mock successful schedule retrieval
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run one iteration of the loop with it=None
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [Exception("Break loop")]  # Break after first iteration
            try:
                run_display_loop(
                    self.ig, None,  # it is None
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify no display update was attempted
        self.assertEqual(self.ig.get_current_schedule.call_count, 2)
        # No draw_inbound_outbound should be called since it is None

    def test_setup_logging_console(self):
        """Test setup_logging with console output."""
        logger = setup_logging(log_to_console=True, log_level=logging.DEBUG)
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_file(self):
        """Test setup_logging with file output."""
        with patch('logging.handlers.RotatingFileHandler') as mock_handler:
            mock_handler_instance = MagicMock()
            mock_handler.return_value = mock_handler_instance
            
            logger = setup_logging(log_to_console=False, log_level=logging.WARNING)
            
            self.assertIsInstance(logger, logging.Logger)
            self.assertEqual(logger.level, logging.WARNING)
            self.assertEqual(len(logger.handlers), 1)
            mock_handler.assert_called_once()

    def test_setup_logging_duplicate_handlers(self):
        """Test that setup_logging clears existing handlers."""
        # Create a logger with existing handlers
        logger = logging.getLogger("test_logger")
        logger.addHandler(logging.StreamHandler())
        self.assertEqual(len(logger.handlers), 1)
        
        # Setup logging should clear existing handlers
        new_logger = setup_logging(log_to_console=True)
        self.assertEqual(len(new_logger.handlers), 1)

    @patch('platform.machine')
    def test_platform_detection_non_raspberry_pi(self, mock_machine):
        """Test platform detection for non-Raspberry Pi."""
        mock_machine.return_value = "x86_64"
        
        # Import after mocking platform
        import instantmbta
        
        # Check that InkyTrain class is None
        self.assertIsNone(instantmbta.inky_train_cls)

    def test_wait_time_constant(self):
        """Test that WAIT_TIME_BETWEEN_CHECKS is properly used."""
        # Mock successful schedule retrieval
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run one iteration of the loop
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [Exception("Break loop")]  # Break after first iteration
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify sleep was called with the correct wait time
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertIn(120, sleep_calls)  # WAIT_TIME_BETWEEN_CHECKS = 120

if __name__ == '__main__':
    unittest.main() 