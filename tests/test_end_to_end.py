# coding=utf-8
"""
End-to-end tests
"""
from datetime import datetime
from os import makedirs
from os.path import join, exists
from unittest.mock import patch, MagicMock

from BaseIntegrationTest import BaseTestCase
from service import prepare_certbot_directory, CertbotEnv


class EndToEndTests(BaseTestCase):
    """
    End-to-end tests
    """
    mock_secrets_client: MagicMock
    mock_storage_client: MagicMock
    mock_storage_bucket: MagicMock
    mock_storage_blob: MagicMock
    mock_run_subprocess: MagicMock
    certbot_env: CertbotEnv

    def setUp(self):
        """
        Test init method
        """
        patcher_secrets_client = patch(
            "service.SecretManagerServiceClient",
            autospec=True,
        )
        patcher_storage_client = patch(
            "service.Client",
            autospec=True,
        )
        patcher_run_subprocess = patch(
            "service.run_subprocess"
        )
        patcher_prepare_dir = patch(
            "service.prepare_certbot_directory"
        )
        patcher_datetime = patch(
            "service.datetime"
        )
        self.addCleanup(patcher_secrets_client.stop)
        self.addCleanup(patcher_storage_client.stop)
        self.addCleanup(patcher_run_subprocess.stop)
        self.addCleanup(patcher_prepare_dir.stop)
        self.addCleanup(patcher_datetime.stop)
        self.mock_secrets_client = patcher_secrets_client.start()
        self.mock_storage_client = patcher_storage_client.start()
        self.mock_run_subprocess = patcher_run_subprocess.start()
        self.mock_prepare_dir = patcher_prepare_dir.start()
        self.mock_datetime = patcher_datetime.start()

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
            .payload.data = "some-data".encode("utf-8")

        self.mock_run_subprocess.return_value = 0, "ok"

        def _intercept_workdir(
            secret: str,
            temp_directory: str
        ) -> CertbotEnv:
            result: CertbotEnv = \
                prepare_certbot_directory(secret, temp_directory)
            certs_dir = result.certificates_dir
            makedirs(certs_dir)
            open(join(certs_dir, "certificate.pem"), "a").close()
            open(join(certs_dir, "privkey.pem"), "a").close()
            open(join(certs_dir, "chain.pem"), "a").close()
            open(join(certs_dir, "fullchain.pem"), "a").close()
            self.certbot_env = result
            return result

        self.mock_prepare_dir.side_effect = _intercept_workdir
        self.mock_datetime.now.return_value = datetime(
            year=1996, month=2, day=22, hour=9, minute=10, second=11)

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

        secrets_fun: MagicMock = self.mock_secrets_client.return_value \
            .access_secret_version
        secrets_fun.assert_called_once_with(request={
            "name": "projects/some-project-id/secrets"
                    "/some-secret-id/versions/latest"
        })
        dry_run_fun: MagicMock = blob.upload_from_string
        dry_run_fun.assert_called_once_with(data="")

        self.assertEqual(len({
            self.certbot_env.secret_location,
            self.certbot_env.logs_dir,
            self.certbot_env.workspace_dir,
            self.certbot_env.certificates_dir,
            self.certbot_env.config_dir
        }), 5, msg="certbot env directories must be unique")

        self.assertFalse(exists(self.certbot_env.secret_location),
                         msg="Workspace must be cleaned after call")
        self.assertFalse(exists(self.certbot_env.logs_dir),
                         msg="Workspace must be cleaned after call")
        self.assertFalse(exists(self.certbot_env.workspace_dir),
                         msg="Workspace must be cleaned after call")
        self.assertFalse(exists(self.certbot_env.certificates_dir),
                         msg="Workspace must be cleaned after call")
        self.assertFalse(exists(self.certbot_env.config_dir),
                         msg="Workspace must be cleaned after call")

        self.mock_run_subprocess.assert_called_once_with([
            "certbot", "--noninteractive",
            f"--config-dir={self.certbot_env.config_dir}",
            f"--work-dir={self.certbot_env.workspace_dir}",
            f"--logs-dir={self.certbot_env.logs_dir}",
            "--force-renewal", "--agree-tos",
            "--email", "test@example.com",
            "--manual-public-ip-logging-ok", "certonly",
            "--dns-google", "--dns-google-credentials",
            f"{self.certbot_env.secret_location}",
            "--dns-google-propagation-seconds", "600",
            "--cert-name", f"{self.certbot_env.cert_name}",
            "-d", "*.example.com", "-d", "www.example.com"
        ], timeout=1200, shell=False, stdin=None, )

        blob_fun: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob
        self.assertEqual(blob_fun.call_count, 9,
                         msg="There are 9 blobs must be uploaded to "
                             "GCS during call: 4 certificated-related "
                             "files in 2 directories + 1 log file")
        call_args = [(i[0], i[1]) for i in blob_fun.call_args_list]
        call_sources = [(i[0], i[1], i[2]) for i in blob.method_calls]
        self.assertEqual(len(call_sources), 9,
                         msg="There are 9 blobs must be uploaded to "
                             "GCS during call: 4 certificated-related "
                             "files in 2 directories + 1 log file")
        call_pairs = list(zip(call_sources, call_args))

        text = "upload_from_string"
        file = "upload_from_filename"
        base_path = self.certbot_env.certificates_dir
        time = "1996-02-22_09-10-11_UTC"
        expected = [
            ((text, (), {"data": ""}),
             ((f"some-path/logs/{time}",), {})),
            ((file, (f"{base_path}/chain.pem",), {}),
             (("some-path/live/chain.pem",), {})),
            ((file, (f"{base_path}/certificate.pem",), {}),
             (("some-path/live/certificate.pem",), {})),
            ((file, (f"{base_path}/privkey.pem",), {}),
             (("some-path/live/privkey.pem",), {})),
            ((file, (f"{base_path}/fullchain.pem",), {}),
             (("some-path/live/fullchain.pem",), {})),
            ((file, (f"{base_path}/chain.pem",), {}),
             ((f"some-path/{time}/chain.pem",), {})),
            ((file, (f"{base_path}/certificate.pem",), {}),
             ((f"some-path/{time}/certificate.pem",), {})),
            ((file, (f"{base_path}/privkey.pem",), {}),
             ((f"some-path/{time}/privkey.pem",), {})),
            ((file, (f"{base_path}/fullchain.pem",), {}),
             ((f"some-path/{time}/fullchain.pem",), {}))
        ]
        self.assertCountEqual(
            call_pairs, expected,
            msg="Files are not uploaded to expected locations")
