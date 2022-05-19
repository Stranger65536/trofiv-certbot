# coding=utf-8
"""
Base class for all integration tests
"""
from flask.testing import FlaskClient
from flask_testing import TestCase

from server import app


class BaseTestCase(TestCase):
    def create_app(self):
        """
        Creates a test cases-ready flask app
        """
        app.config['TESTING'] = True
        return app

    def http(self) -> FlaskClient:
        """
        Returns http client for test server
        """
        return self.client
