# coding=utf-8
"""
Main business logic
"""
from collections import namedtuple
from datetime import datetime
from logging import info
from os import makedirs, walk
from os.path import join, relpath, normpath
from subprocess import TimeoutExpired
from tempfile import TemporaryDirectory
from typing import List, Dict
from uuid import uuid4

# noinspection PyPackageRequirements
from google.cloud.secretmanager_v1 import SecretManagerServiceClient, \
    AccessSecretVersionResponse, SecretPayload
# noinspection PyPackageRequirements
from google.cloud.storage import Bucket, Blob, Client
from pytz import UTC

from dto import CertbotRequest
from errors import CertbotError, CertbotTimeoutError, \
    SecretFetchError, GCSUploadError, GCSError
from providers import DnsProvider, providers
from utils import run_subprocess


def issue_certificate(req: CertbotRequest) -> Dict[str, str]:
    """
    Issues certificate
    """
    provider: DnsProvider = providers[req.provider]

    with TemporaryDirectory(prefix="certbot-") as d:
        certificates_dir: str = call_certbot(provider, req, d)
        client = Client(req.project)
        try:
            bucket: Bucket = client.get_bucket(req.target_bucket)
        except Exception:
            raise GCSError(req.target_bucket)
        live_directory: str = join(req.target_bucket_path, "live")
        upload_directory_to_gcs(
            certificates_dir,
            bucket,
            live_directory
        )
        now: datetime = datetime.now(tz=UTC)
        timed_directory = join(
            req.target_bucket_path,
            now.strftime("%Y-%m-%d_%H-%M-%S_UTC"))
        upload_directory_to_gcs(
            certificates_dir,
            bucket,
            timed_directory
        )
    return {
        "live_gcs_path": f"gs://{bucket.name}/{live_directory}",
        "timed_gcs_path": f"gs://{bucket.name}/{timed_directory}"
    }


def call_certbot(
    provider: DnsProvider,
    req: CertbotRequest,
    temp_directory: str,
) -> str:
    """
    Calls certbot. Returns directory with live certificates.
    """
    try:
        secret: str = get_secret_value(
            req.project, req.secret_id)
    except Exception:
        raise SecretFetchError("Secret obtain filed!")

    name_options: List[str] = provider.name_option.split()
    secret_path_option: str = provider.secret_path_option
    propagation_time_option: str = provider.propagation_time_option

    certbot_env = prepare_certbot_directory(secret, temp_directory)

    command = [
        "certbot",
        "--noninteractive",
        f"--config-dir={certbot_env.config_dir}",
        f"--work-dir={certbot_env.workspace_dir}",
        f"--logs-dir={certbot_env.logs_dir}",
        "--force-renewal",
        "--agree-tos",
        "--email",
        f"{req.email}",
        "--manual-public-ip-logging-ok",
        "certonly",
        *name_options,
        secret_path_option,
        certbot_env.secret_location,
        propagation_time_option,
        str(req.propagation_seconds),
        "--cert-name",
        certbot_env.cert_name,
        *[e for v in [["-d", i] for i in req.domains] for e in v]
    ]
    info(f"Issue command: '{' '.join(command)}'")
    timeout = max(2 * req.propagation_seconds, 10)
    out: str = ""
    try:
        code, out = run_subprocess(
            command,
            timeout=timeout,
            shell=False,
            stdin=None,
        )
    except TimeoutExpired as e:
        raise CertbotTimeoutError(command, timeout, e.output)
    except Exception:
        raise CertbotError(command, timeout, out)
    if code:
        raise CertbotError(command, timeout, out)
    return certbot_env.certificates_dir


CertbotEnv = namedtuple("CertbotEnv",
                        "cert_name "
                        "certificates_dir "
                        "config_dir "
                        "logs_dir "
                        "workspace_dir "
                        "secret_location")


def prepare_certbot_directory(
    secret: str,
    temp_directory: str
) -> CertbotEnv:
    """
    Prepares specified directory for certbot
    """
    config_dir: str = join(temp_directory, "config")
    makedirs(config_dir)
    logs_dir: str = join(temp_directory, "logs")
    makedirs(logs_dir)
    workspace_dir: str = join(temp_directory, "workspace")
    makedirs(workspace_dir)
    secret_location = join(temp_directory, "secret.file")
    with open(secret_location, "w", encoding="utf-8") as f:
        f.write(secret)
    cert_name = "cert-" + str(uuid4())
    certificates_dir = join(config_dir, "live", cert_name)
    return CertbotEnv(
        cert_name=cert_name,
        certificates_dir=certificates_dir,
        config_dir=config_dir,
        logs_dir=logs_dir,
        workspace_dir=workspace_dir,
        secret_location=secret_location,
    )


def dry_run_upload(req: CertbotRequest) -> None:
    """
    Dry runs upload with uploading an empty file to
    logs directory under specified path
    """
    now = datetime.now(tz=UTC)
    gcs_path: str = join(req.target_bucket_path, "logs",
                         now.strftime("%Y-%m-%d_%H-%M-%S_UTC"))
    try:
        client = Client(req.project)
        bucket: Bucket = client.get_bucket(req.target_bucket)
        info(f"Uploading log file to {gcs_path}")
        blob: Blob = bucket.blob(gcs_path)
        blob.upload_from_string(data="")
        info(f"Upload of log file has completed")
    except Exception:
        raise GCSUploadError(
            "Empty log file",
            req.target_bucket,
            gcs_path
        )


def upload_directory_to_gcs(
    source_path: str,
    bucket: Bucket,
    gcs_path: str,
) -> None:
    """
    Uploads specified directory to GCS recursively
    """
    info(f"Uploading directory '{source_path}' content to "
         f"gs://{bucket.name}/{gcs_path}")
    for root, _, files in walk(source_path):
        for file in sorted(files):
            rel_dir: str = relpath(root, source_path)
            rel_file: str = join(rel_dir, file)
            bucket_path: str = normpath(join(gcs_path, rel_file))
            upload_file_to_gcs(join(root, file), bucket, bucket_path)
    info(f"Upload of '{source_path}' content to "
         f"gs://{bucket.name}/{gcs_path} has completed")


def upload_file_to_gcs(
    source_path: str,
    bucket: Bucket,
    gcs_path: str,
) -> None:
    """
    Uploads specified file to GCS
    """
    # noinspection PyBroadException
    try:
        info(f"Uploading {source_path} to {gcs_path}")
        blob: Blob = bucket.blob(gcs_path)
        blob.upload_from_filename(source_path)
        info(f"Upload {source_path} completed")
    except Exception:
        raise GCSUploadError(
            source_path=source_path,
            bucket_name=bucket.name,
            bucket_path=gcs_path
        )


def get_secret_value(project: str, secret_id: str) -> str:
    """
    Returns secret by secret id
    """
    info(f"Getting secret {secret_id} from project {project}")
    client = SecretManagerServiceClient()
    rsp: AccessSecretVersionResponse = \
        client.access_secret_version(request={
            "name": f"projects/{project}"
                    f"/secrets/{secret_id}/versions/latest"
        })
    info(f"Secret {secret_id} from project {project} fetched")
    payload: SecretPayload = rsp.payload
    payload_bytes: bytes = payload.data
    return payload_bytes.decode("utf-8")
