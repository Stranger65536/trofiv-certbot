# coding=utf-8
"""
End-to-end tests
"""
from datetime import datetime
from itertools import zip_longest
from os import makedirs
from os.path import join, exists
from subprocess import TimeoutExpired
from typing import Callable, Any, List, Tuple, Optional, Dict
from unittest.mock import patch, MagicMock

from BaseIntegrationTest import BaseTestCase
from service import prepare_certbot_directory, CertbotEnv, \
    issue_certificate


class EndToEndTests(BaseTestCase):
    """
    End-to-end tests
    """
    mock_secrets_client: MagicMock
    mock_storage_client: MagicMock
    mock_storage_bucket: MagicMock
    mock_storage_blob: MagicMock
    mock_run_subprocess: MagicMock
    mock_issue_certs: MagicMock
    certbot_env: CertbotEnv

    bucket: MagicMock
    blob: MagicMock

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
        patcher_issue_certs = patch(
            "server.issue_certificate"
        )
        self.addCleanup(patcher_secrets_client.stop)
        self.addCleanup(patcher_storage_client.stop)
        self.addCleanup(patcher_run_subprocess.stop)
        self.addCleanup(patcher_prepare_dir.stop)
        self.addCleanup(patcher_datetime.stop)
        self.addCleanup(patcher_issue_certs.stop)
        self.mock_secrets_client = patcher_secrets_client.start()
        self.mock_storage_client = patcher_storage_client.start()
        self.mock_run_subprocess = patcher_run_subprocess.start()
        self.mock_prepare_dir = patcher_prepare_dir.start()
        self.mock_datetime = patcher_datetime.start()
        self.mock_issue_certs = patcher_issue_certs.start()

        self.bucket = self.mock_storage_client.return_value \
            .get_bucket.return_value
        self.blob = self.bucket.blob.return_value

        # some default behavior stuff
        self.bucket.name = "some-bucket"
        self.blob.upload_from_string.return_value = None
        self.blob.upload_from_filename.return_value = None
        self.mock_secrets_client.return_value \
            .access_secret_version.return_value \
            .payload.data = "some-data".encode("utf-8")
        self.mock_run_subprocess.return_value = 0, "ok"
        self.mock_datetime.now.return_value = datetime(
            year=1996, month=2, day=22, hour=9, minute=10, second=11)
        self.mocked_time = "1996-02-22_09-10-11_UTC"
        self.mock_issue_certs.side_effect = issue_certificate
        self.maxDiff = None

    def test_success_path(self):
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
        self.assertEqual(response.json, {
            "result": {
                "live_gcs_path": "gs://some-bucket/some-path/live",
                "timed_gcs_path": "gs://some-bucket/some-path"
                                  "/1996-02-22_09-10-11_UTC"
            },
            "success": True
        })

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
        ], expect_log_file=True, time=self.mocked_time)

    def test_certbot_failed(self):
        self.mock_run_subprocess.return_value = 1, "something is wrong"
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
                "type": "CertbotError"
            },
            "success": False
        })

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
            time=self.mocked_time,
        )

    def test_certbot_failed_exc(self):
        self.mock_run_subprocess.return_value = OSError("some-err")
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
                "output": [""],
                "timeout": 1200,
                "type": "CertbotError"
            },
            "success": False
        })

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
            time=self.mocked_time,
        )

    def test_generic_err(self):
        self.mock_issue_certs.side_effect = ValueError("some-err")
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
        self.assertEqual(response.json, {
            "error": {
                "message": "Generic error happened. "
                           "Check logs for details",
                "type": "ValueError"
            },
            "success": False,
        })

        self._assert_secret_no_fetch()
        self.mock_run_subprocess.assert_not_called()

        self._assert_file_uploads(
            [], expect_log_file=True,
            time=self.mocked_time,
        )

    def test_certbot_timeout(self):
        self.mock_run_subprocess.side_effect = \
            TimeoutExpired(["a", "command"], timeout=1,
                           output="some output")
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
                "message": "Certbot instance aborted by timeout",
                "output": ["some output"],
                "timeout": 1200,
                "type": "CertbotTimeoutError"
            },
            "success": False
        })

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
            time=self.mocked_time
        )

    def test_dry_upload_failed(self):
        self.blob.upload_from_string.side_effect = \
            ValueError("some-err")
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
        self.assertEqual(response.json, {
            "error": {
                "bucket": "some-bucket",
                "bucket_path": "some-path/logs/1996-02-22_09-10-11_UTC",
                "message": "There is a problem with "
                           "file upload to GCS.",
                "source_path": "Empty log file",
                "type": "GCSUploadError"
            },
            "success": False
        })

        self._assert_secret_no_fetch()
        self.mock_run_subprocess.assert_not_called()

        self._assert_file_uploads(
            [], expect_log_file=True,
            time=self.mocked_time,
        )

    def test_bucket_err(self):
        self._mock_cert_files_creation()
        self.mock_storage_client.return_value.get_bucket.side_effect = [
            self.bucket, ValueError("bucket get error")
        ]

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
        self.assertEqual(response.json, {
            "error": {
                "message": "Generic error happened. "
                           "Check logs for details",
                "type": "GCSError"},
            "success": False
        })

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

        self._assert_file_uploads(
            [], expect_log_file=True,
            time=self.mocked_time,
        )

    def test_secret_fetch_failed(self):
        self.mock_secrets_client.return_value \
            .access_secret_version.side_effect = ValueError("some-err")
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
        self.assertEqual(response.json, {
            "error": {
                "message": "There is a problem with DNS provider "
                           "secret fetch error. "
                           "Check logs for details.",
                "type": "SecretFetchError",
            },
            "success": False,
        })

        self._assert_secret_fetch()
        self.mock_run_subprocess.assert_not_called()

        self._assert_file_uploads(
            [], expect_log_file=True,
            time=self.mocked_time,
        )

    def test_upload_failed(self):
        self.blob.upload_from_filename.side_effect = \
            ValueError("some-err")
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
        self.assert500(response)
        self.assertEqual(response.json, {
            "error": {
                "bucket": "some-bucket",
                "bucket_path": "some-path/live/certificate.pem",
                "message": "There is a problem with "
                           "file upload to GCS.",
                "source_path": f"{self.certbot_env.certificates_dir}"
                               f"/certificate.pem",
                "type": "GCSUploadError"
            },
            "success": False
        })

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
            "certificate.pem"
        ], expect_log_file=True,
            time=self.mocked_time,
            live_only={"certificate.pem": True}
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
        time: Optional[str] = None,
        live_only: Dict[str, bool] = None,
    ) -> None:
        if (expected_files or expect_log_file) and not time:
            raise ValueError("Time is optional only for no upload case")

        blob_fun: MagicMock = self.mock_storage_client.return_value \
            .get_bucket.return_value \
            .blob
        blob: MagicMock = blob_fun.return_value
        call_args = [(i[0], i[1]) for i in blob_fun.call_args_list]
        call_sources = [(i[0], i[1], i[2]) for i in blob.method_calls]
        self.assertEqual(len(call_args), len(call_sources),
                         msg="Blob operations call count mismatch")
        call_pairs = list(zip_longest(call_sources, call_args))

        expected: List[Tuple] = []

        if expected_files:
            file = "upload_from_filename"
            base_path = self.certbot_env.certificates_dir
            for i in expected_files:
                expected.append(
                    ((file, (f"{base_path}/{i}",), {}),
                     ((f"some-path/live/{i}",), {}))
                )
                if not live_only or not live_only.get(i):
                    expected.append(
                        ((file, (f"{base_path}/{i}",), {}),
                         ((f"some-path/{time}/{i}",), {}))
                    )

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

    def _assert_secret_no_fetch(self):
        secrets_fun: MagicMock = self.mock_secrets_client.return_value \
            .access_secret_version
        secrets_fun.assert_not_called()
