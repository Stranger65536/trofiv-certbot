# coding=utf-8
"""
Integration tests with mocking
"""
from unittest.mock import patch, MagicMock

from tests.BaseIntegrationTest import BaseTestCase


class TestApi(BaseTestCase):
    mock_dry_run_upload: MagicMock
    mock_issue_certificate: MagicMock

    def setUp(self):
        """
        Tests init method
        """
        patcher_dry_run_upload = patch("server.dry_run_upload")
        self.addCleanup(patcher_dry_run_upload.stop)
        self.mock_dry_run_upload = patcher_dry_run_upload.start()

        patcher_issue_certificate = patch("server.issue_certificate")
        self.addCleanup(patcher_issue_certificate.stop)
        self.mock_issue_certificate = patcher_issue_certificate.start()

    def test_non_json(self):
        response = self.http().post("/certs")
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": [
                    "Request json is absent or invalid!"
                ],
                "message": "Request is invalid",
                "type": "ValidationError"
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

    def test_empty_request(self):
        response = self.http().post("/certs", json={})
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "domains": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "email": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "project": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "provider": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "secret_id": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "target_bucket": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ],
                    "target_bucket_path": [
                        "Missing data for required field for class "
                        "CertbotRequest"
                    ]
                },
                "message": "Request is invalid",
                "type": "ValidationError"
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

    def test_all_request_params_valid(self):
        """
        Tests request parsing with all request params
        """
        self.mock_dry_run_upload.return_value = None
        self.mock_issue_certificate.return_value = {
            "live_gcs_path": "gs://live",
            "timed_gcs_path": "gs://timed",
        }
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
        response = self.http().post("/certs", json=req)
        self.assert200(response)
        self.assertEqual(response.json, {
            "result": {
                "live_gcs_path": "gs://live",
                "timed_gcs_path": "gs://timed",
            },
            "success": True
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 1)
        self.assertEqual(self.mock_dry_run_upload.call_count, 1)
        self.assertEqual(
            vars(self.mock_issue_certificate.call_args.args[0]), req
        )

    def test_request_params_valid_with_default(self):
        """
        Tests request parsing with request params with default values
        """
        self.mock_dry_run_upload.return_value = None
        self.mock_issue_certificate.return_value = {
            "live_gcs_path": "gs://live",
            "timed_gcs_path": "gs://timed",
        }
        req = {
            "provider": "google",
            "secret_id": "some-secret-id",
            "project": "some-project-id",
            "domains": ["*.example.com", "www.example.com"],
            "email": "test@example.com",
            "target_bucket": "some-bucket",
            "target_bucket_path": "some-path",
        }
        response = self.http().post("/certs", json=req)
        self.assert200(response)
        self.assertEqual(self.mock_issue_certificate.call_count, 1)
        self.assertEqual(self.mock_dry_run_upload.call_count, 1)
        self.assertEqual(
            vars(self.mock_issue_certificate.call_args.args[0]), {
                **req,
                "propagation_seconds": 60,
            }
        )
        self.assertEqual(response.json, {
            "result": {
                "live_gcs_path": "gs://live",
                "timed_gcs_path": "gs://timed",
            },
            "success": True
        })

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
        response = self.http().post("/certs", json=req)
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "propagation_seconds": [
                        "Value must be greater than 0"
                    ]
                },
                "message": "Request is invalid",
                "type": "ValidationError",
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

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
        response = self.http().post("/certs", json=req)
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "domains": [
                        "Domains list can't be empty!"
                    ]
                },
                "message": "Request is invalid",
                "type": "ValidationError",
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

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
        response = self.http().post("/certs", json=req)
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "domains": [
                        "Domains list can't contain duplicates!"
                    ]
                },
                "message": "Request is invalid",
                "type": "ValidationError",
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

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
        response = self.http().post("/certs", json=req)
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "provider": [
                        "Must be one of: cloudflare, cloudxns, "
                        "digitalocean, dnsimple, dnsmadeeasy, gehirn, "
                        "godaddy, google, linode, luadns, nsone, ovh, "
                        "rfc2136, route53, sakuracloud."
                    ]
                },
                "message": "Request is invalid",
                "type": "ValidationError",
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)

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
        response = self.http().post("/certs", json=req)
        self.assert400(response)
        self.assertEqual(response.json, {
            "error": {
                "errors": {
                    "email": ["Not a valid email address."]
                },
                "message": "Request is invalid",
                "type": "ValidationError",
            },
            "success": False
        })
        self.assertEqual(self.mock_issue_certificate.call_count, 0)
        self.assertEqual(self.mock_dry_run_upload.call_count, 0)
