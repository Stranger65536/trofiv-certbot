# coding=utf-8
"""
Request / response tests
"""
from json import dumps
from unittest import TestCase

from flask import Flask, request
from marshmallow import ValidationError

from dto import CertbotRequest


class DtoTests(TestCase):
    """
    Request / response tests
    """

    app = Flask(__name__)

    def test_all_request_params_valid(self):
        """
        Tests request parsing with all request params
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "propagation_seconds": 600,
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            parsed = CertbotRequest.from_request(request)
            self.assertEqual(
                dumps(vars(parsed), sort_keys=True),
                dumps(req, sort_keys=True))

    def test_request_params_valid_with_default(self):
        """
        Tests request parsing with request params with default values
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            parsed = CertbotRequest.from_request(request)
            self.assertEqual(
                dumps(vars(parsed), sort_keys=True),
                dumps({
                    "provider": "google",
                    "secret_id": "some-secret-id",
                    "project": "some-project-id",
                    "domains": ["*.example.com", "www.example.com"],
                    "propagation_seconds": 60,
                    "email": "test@example.com",
                    "target_bucket": "some-bucket",
                    "target_bucket_path": "some-path",
                }, sort_keys=True))

    def test_negative_propagation_seconds(self):
        """
        Tests request parsing with negative propagation seconds
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "propagation_seconds": -1,
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "propagation_seconds": [
                        "Value must be greater than 0"
                    ]
                })

    def test_no_domains(self):
        """
        Tests request parsing with no domains
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": [],
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "domains": [
                        "Domains list can't be empty!"
                    ]
                })

    def test_duplicate_domains(self):
        """
        Tests request parsing with duplicate domains
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["example.com", "example.com"],
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "domains": [
                        "Domains list can't contain duplicates!"
                    ]
                })

    def test_empty_request(self):
        """
        Tests empty request parsing
        """
        with self.app.test_request_context(json=None):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                ["Request json is absent or invalid!"])

    def test_unknown_provider_request(self):
        """
        Tests empty request parsing
        """
        req = {
            "provider": "unknown",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "provider": [
                        "Must be one of: cloudflare, cloudxns, "
                        "digitalocean, dnsimple, dnsmadeeasy, gehirn, "
                        "godaddy, google, linode, luadns, nsone, ovh, "
                        "rfc2136, route53, sakuracloud."
                    ]
                })

    def test_invalid_email_request(self):
        """
        Tests invalid email request parsing
        """
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "email": "invalid-mail-example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        with self.app.test_request_context(json=req):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "email": ["Not a valid email address."]
                })

    def test_missing_fields_request(self):
        """
        Tests missing fields logic
        """
        with self.app.test_request_context(json={}):
            with self.assertRaises(ValidationError) as e:
                CertbotRequest.from_request(request)
            self.assertEqual(
                e.exception.messages,
                {
                    "domains": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "provider": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "secret_id": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "project": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "email": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "target_bucket": [
                        "Missing data for required field "
                        "for class CertbotRequest"
                    ],
                    "target_bucket_path": [
                        "Missing data for required field for "
                        "class CertbotRequest"
                    ],
                })
