import unittest
from unittest.mock import patch, MagicMock
import sys
import argparse
from io import StringIO

class TestMainExecution(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_args = [
            "Red", "Red Line", "place-cntsq", "Central Square", 
            "place-harsq", "Harvard Square"
        ]

    @patch('platform.machine')
    def test_platform_detection_non_pi_architectures(self, mock_machine):
        """Test platform detection for non-Raspberry Pi architectures."""
        non_pi_architectures = ["x86_64", "i386", "amd64", "arm64"]
        
        for arch in non_pi_architectures:
            mock_machine.return_value = arch
            
            # Import after mocking platform
            import instantmbta
            
            # Check that InkyTrain class is None for non-Pi architectures
            self.assertIsNone(instantmbta.inky_train_cls)

if __name__ == '__main__':
    unittest.main() 