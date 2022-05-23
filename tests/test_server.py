# coding=utf-8
"""
Server start / stop tests
"""
from unittest import TestCase
from unittest.mock import patch, MagicMock

from server import main


class ServerTests(TestCase):
    """
    Server start / stop tests
    """
    mock_init_server: MagicMock

    def setUp(self):
        """
        Test init method
        """
        patcher_server = patch(
            "server.WSGIServer"
        )
        self.addCleanup(patcher_server.stop)
        self.mock_server = patcher_server.start()

    def test_keyboard_interrupt(self):
        self.mock_server.return_value.start.side_effect = \
            KeyboardInterrupt()
        main()
        stop: MagicMock = self.mock_server.return_value.stop
        stop.assert_called_once()

    def test_exc(self):
        self.mock_server.return_value.start.side_effect = OSError()
        main()
        stop: MagicMock = self.mock_server.return_value.stop
        stop.assert_called_once()
