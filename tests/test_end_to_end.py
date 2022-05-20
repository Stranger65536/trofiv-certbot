# coding=utf-8
"""
End-to-end tests
"""
from base64 import b64encode
from unittest.mock import patch, MagicMock

from BaseIntegrationTest import BaseTestCase


class EndToEndTests(BaseTestCase):
    """
    End-to-end tests
    """
    mock_secrets_client: MagicMock
    mock_storage_client: MagicMock
    mock_storage_bucket: MagicMock
    mock_storage_blob: MagicMock
    mock_run_subprocess: MagicMock

    def setUp(self):
        """
        Test init method
        """
        patcher_secrets_client = patch(
            "service.SecretManagerServiceClient",
            # autospec=True,
        )
        patcher_storage_client = patch(
            "service.Client",
            # autospec=True,
        )
        patcher_run_subprocess = patch(
            "service.run_subprocess"
        )
        self.addCleanup(patcher_secrets_client.stop)
        self.addCleanup(patcher_storage_client.stop)
        self.addCleanup(patcher_run_subprocess.stop)
        self.mock_secrets_client = patcher_secrets_client.start()
        self.mock_storage_client = patcher_storage_client.start()
        self.mock_run_subprocess = patcher_run_subprocess.start()

    def test_success_path(self):
        blob: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob.return_value

        dry_uploads = blob.upload_from_string
        dry_uploads.return_value = None

        file_uploads = blob.upload_from_filename
        file_uploads.return_value = None

        self.mock_secrets_client.return_value \
            .access_secret_version.return_value \
            .payload.data = b64encode("some-data".encode("utf-8"))

        self.mock_run_subprocess.return_value = 0, "ok"

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
