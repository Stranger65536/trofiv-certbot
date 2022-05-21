# coding=utf-8
"""
End-to-end tests
"""
from datetime import datetime
from itertools import zip_longest
from os import makedirs
from os.path import join, exists
from typing import Callable, Any, List, Tuple
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

        self.maxDiff = None

    def test_success_path(self):
        blob: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob.return_value
        blob.upload_from_string.return_value = None
        blob.upload_from_filename.return_value = None

        self.mock_secrets_client.return_value \
            .access_secret_version.return_value \
            .payload.data = "some-data".encode("utf-8")
        self.mock_run_subprocess.return_value = 0, "ok"
        self.mock_datetime.now.return_value = datetime(
            year=1996, month=2, day=22, hour=9, minute=10, second=11)
        self._mock_cert_files_creation()

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

        self._assert_secret_fetch()
        self._assert_certbot_env()
        self._assert_certbot_workdir_cleaned()

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

        self._assert_file_uploads([
            "chain.pem", "certificate.pem",
            "fullchain.pem", "privkey.pem"
        ], expect_log_file=True, time="1996-02-22_09-10-11_UTC")

    def test_certbot_failed(self):
        blob: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob.return_value
        blob.upload_from_string.return_value = None
        blob.upload_from_filename.return_value = None

        self.mock_secrets_client.return_value \
            .access_secret_version.return_value \
            .payload.data = "some-data".encode("utf-8")
        self.mock_run_subprocess.return_value = 1, "something is wrong"
        self.mock_datetime.now.return_value = datetime(
            year=1996, month=2, day=22, hour=9, minute=10, second=11)
        self._intercept_workdir(lambda *args: None)

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
        self.assert500(response)

        expected_certbot_command = [
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
        ]
        self.assertEqual(response.json, {
            "error": {
                "command": expected_certbot_command,
                "message": "Certbot instance failed",
                "output": ["something is wrong"],
                "timeout": 1200,
                "type": "CertbotError"},
            "success": False})

        self._assert_secret_fetch()
        self._assert_certbot_env()
        self._assert_certbot_workdir_cleaned()

        self.mock_run_subprocess.assert_called_once_with(
            expected_certbot_command,
            timeout=1200,
            shell=False,
            stdin=None,
        )

        self._assert_file_uploads(
            [], expect_log_file=True,
            time="1996-02-22_09-10-11_UTC"
        )

    def _assert_certbot_workdir_cleaned(self):
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

    def _assert_certbot_env(self):
        self.assertEqual(len({
            self.certbot_env.secret_location,
            self.certbot_env.logs_dir,
            self.certbot_env.workspace_dir,
            self.certbot_env.certificates_dir,
            self.certbot_env.config_dir
        }), 5, msg="certbot env directories must be unique")

    @staticmethod
    def _create_cert_files(
        secret: str,
        temp_directory: str,
        env: CertbotEnv
    ) -> None:
        certs_dir = env.certificates_dir
        makedirs(certs_dir)
        open(join(certs_dir, "certificate.pem"), "a").close()
        open(join(certs_dir, "privkey.pem"), "a").close()
        open(join(certs_dir, "chain.pem"), "a").close()
        open(join(certs_dir, "fullchain.pem"), "a").close()

    def _intercept_workdir(
        self, fun: Callable[[str, str, CertbotEnv], Any]
    ) -> None:
        def _interceptor(
            secret: str,
            temp_directory: str
        ) -> CertbotEnv:
            result: CertbotEnv = \
                prepare_certbot_directory(secret, temp_directory)
            fun(secret, temp_directory, result)
            self.certbot_env = result
            return result

        self.mock_prepare_dir.side_effect = _interceptor

    def _mock_cert_files_creation(self) -> None:
        self._intercept_workdir(self._create_cert_files)

    def _assert_file_uploads(
        self,
        expected_files: List[str],
        expect_log_file: bool,
        time: str
    ) -> None:
        blob_fun: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob
        blob: MagicMock = blob_fun.return_value
        call_args = [(i[0], i[1]) for i in blob_fun.call_args_list]
        call_sources = [(i[0], i[1], i[2]) for i in blob.method_calls]
        self.assertEqual(len(call_args), len(call_sources),
                         msg="Blob operations call count mismatch")
        call_pairs = list(zip_longest(call_sources, call_args))
        text = "upload_from_string"
        file = "upload_from_filename"
        base_path = self.certbot_env.certificates_dir
        expected: List[Tuple] = [i for j in [[
            ((file, (f"{base_path}/{i}",), {}),
             ((f"some-path/live/{i}",), {})),
            ((file, (f"{base_path}/{i}",), {}),
             ((f"some-path/{time}/{i}",), {}))
        ] for i in expected_files] for i in j]

        if expect_log_file:
            expected.append((
                ("upload_from_string", (), {"data": ""}),
                ((f"some-path/logs/{time}",), {}),
            ))

        self.assertCountEqual(
            call_pairs, expected,
            msg="Files are not uploaded to expected locations")

    def _assert_secret_fetch(self):
        secrets_fun: MagicMock = self.mock_secrets_client.return_value \
            .access_secret_version
        secrets_fun.assert_called_once_with(request={
            "name": "projects/some-project-id/secrets"
                    "/some-secret-id/versions/latest"
        })
