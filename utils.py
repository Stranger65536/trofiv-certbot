# coding=utf-8
"""
Utilities
"""
from logging import getLogger, WARNING, INFO, StreamHandler, \
    Formatter, Handler, info, Logger
from os import walk
from os.path import relpath, join, normpath
from subprocess import Popen, PIPE, STDOUT
from time import time
from typing import List, Tuple, Optional
from warnings import filterwarnings

# noinspection PyPackageRequirements
from google.cloud.secretmanager_v1 import SecretManagerServiceClient, \
    AccessSecretVersionResponse, SecretPayload
# noinspection PyPackageRequirements
from google.cloud.storage import Blob, Bucket, Client


def default_handler() -> Handler:
    """
    Returns default configured console handler
    """
    console_handler = StreamHandler()
    console_handler.setLevel(INFO)
    formatter = Formatter("[%(asctime)s] %(levelname)s %(name)s "
                          "%(threadName)s "
                          "{%(pathname)s:%(lineno)d} "
                          " - %(message)s")
    console_handler.setFormatter(formatter)
    return console_handler


def configure_logger() -> None:
    """
    Configures default logger
    """
    console = default_handler()
    getLogger().addHandler(console)
    getLogger("").addHandler(console)
    getLogger("").setLevel(INFO)
    getLogger().addHandler(console)
    getLogger().setLevel(INFO)
    getLogger("requests").setLevel(WARNING)
    getLogger("urllib3").setLevel(WARNING)
    getLogger("engineio.server").setLevel(WARNING)
    getLogger("socketio.server").setLevel(WARNING)
    getLogger("werkzeug").setLevel(WARNING)
    filterwarnings("ignore", module="urllib3")


def domain_to_path(domain: str) -> Tuple[List[str], str]:
    """
    Converts domain name to relative path within upload destination
    """
    parts: List[str] = [i for i in domain.split(".") if i]
    if not parts:
        raise ValueError(f"Domain is invalid: '{domain}'")
    if parts[0] == "*":
        return parts[1:], "wildcard"
    else:
        return parts[1:], parts[0]


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
        for file in files:
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
    info(f"Uploading {source_path} to {gcs_path}")
    blob: Blob = bucket.blob(gcs_path)
    blob.upload_from_filename(source_path)
    info(f"Upload {source_path} completed")


def get_storage_client(
    project: str,
    sa_path: Optional[str] = None
) -> Client:
    """
    Gets GCS client
    """
    if sa_path:
        info("Using provided SA to authenticate")
        return Client.from_service_account_json(sa_path,
                                                project=project)
    else:
        info("Using environment-based SA to authenticate")
        return Client(project=project)


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


def run_subprocess(
    *popenargs,
    timeout: int,
    logger: Optional[Logger] = None,
    **kwargs,
) -> int:
    """
    Runs subprocess with real time output. Returns exit code
    """
    if logger is None:
        logger = getLogger()
    kwargs["stdout"] = PIPE
    kwargs["stderr"] = STDOUT
    kwargs["universal_newlines"] = True
    with Popen(*popenargs, **kwargs) as process:
        start: float = time()
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
            current = time()
            if current - start > timeout:
                process.kill()
                raise TimeoutError("Command hangs!")
        return process.poll()
