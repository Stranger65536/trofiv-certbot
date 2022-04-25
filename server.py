# coding=utf-8
"""
Server entry point
"""
from datetime import datetime
from logging import info, exception, getLogger
from os import makedirs
from os.path import join
from tempfile import TemporaryDirectory
from traceback import format_exc
from typing import List, Dict
from uuid import uuid4
from wsgiref.simple_server import WSGIServer

# noinspection PyProtectedMember
from cheroot.wsgi import PathInfoDispatcher as WSGIPathInfoDispatcher
from cheroot.wsgi import Server as WSGIServer
from flask import Flask, jsonify, request
# noinspection PyPackageRequirements
from google.cloud.storage import Bucket, Blob
from pytz import UTC

from dto import CertbotRequest
from providers import providers, DnsProvider
from utils import configure_logger, get_secret_value, \
    get_storage_client, upload_directory_to_gcs, run_subprocess

# noinspection PyPackageRequirements

app = Flask(__name__)


@app.route("/certs",
           endpoint="certs",
           methods=["POST"])
def renew_certificates():
    """
    Job submit endpoint
    """
    # noinspection PyBroadException
    try:
        req = CertbotRequest.from_request(request)
    except Exception:
        exception("Request parse error!")
        tb = format_exc()
        return jsonify({"error": tb}), 400
    # noinspection PyBroadException
    try:
        dry_run_upload(req)
    except Exception:
        exception("Dry run of upload failed!")
        tb = format_exc()
        return jsonify({"error": tb}), 500
    # noinspection PyBroadException
    try:
        result: Dict[str, str] = issue_certificate(req)
        return jsonify(result)
    except Exception:
        exception("Certificate issue failed!")
        tb = format_exc()
        return jsonify({"error": tb}), 500


def issue_certificate(req: CertbotRequest) -> Dict[str, str]:
    """
    Issues certificate
    """
    provider: DnsProvider = providers[req.provider]
    name_options: List[str] = provider.name_option.split()
    secret_path_option: str = provider.secret_path_option
    propagation_time_option: str = provider.propagation_time_option

    with TemporaryDirectory(prefix="certbot-") as d:
        certificates_dir: str = call_certbot(
            req, d, name_options,
            propagation_time_option,
            secret_path_option,
        )
        try:
            client = get_storage_client(req.project)
            bucket: Bucket = client.get_bucket(req.target_bucket)
            live_directory: str = join(req.target_bucket_path, "live")
            upload_directory_to_gcs(
                certificates_dir,
                bucket,
                live_directory
            )
            now = datetime.now(tz=UTC)
            timed_directory = join(
                req.target_bucket_path,
                now.strftime("%Y-%m-%d_%H-%M-%S_UTC"))
            upload_directory_to_gcs(
                certificates_dir,
                bucket,
                timed_directory
            )
        except Exception:
            raise ValueError("Can't upload issued certificates!")
    return {
        "live_gcs_path": f"gs://{bucket.name}/{live_directory}",
        "timed_gcs_path": f"gs://{bucket.name}/{timed_directory}"
    }


def call_certbot(
    req: CertbotRequest,
    temp_directory: str,
    name_options: List[str],
    propagation_time_option: str,
    secret_path_option: str,
) -> str:
    """
    Calls certbot. Returns directory with live certificates.
    """
    try:
        secret: str = get_secret_value(
            req.project, req.secret_id)
    except Exception:
        raise ValueError("Secret obtain filed!")

    config_dir: str = join(temp_directory, "config")
    makedirs(config_dir)
    logs_dir: str = join(temp_directory, "logs")
    makedirs(logs_dir)
    workspace_dir: str = join(temp_directory, "workspace")
    makedirs(workspace_dir)
    secret_location = join(temp_directory, "secret.file")
    with open(secret_location, "w", encoding="utf-8") as f:
        f.write(secret)
    uuid = str(uuid4())
    certificates_dir = join(config_dir, "live", f"cert-{uuid}")

    command = [
        "certbot",
        "--noninteractive",
        f"--config-dir={config_dir}",
        f"--work-dir={workspace_dir}",
        f"--logs-dir={logs_dir}",
        "--force-renewal",
        "--agree-tos",
        "--email",
        f"{req.email}",
        "--manual-public-ip-logging-ok",
        "certonly",
        *name_options,
        secret_path_option,
        secret_location,
        propagation_time_option,
        str(req.propagation_seconds),
        "--cert-name",
        f"cert-{uuid}",
        *[e for v in [["-d", i] for i in req.domains] for e in v]
    ]
    info(f"Issue command: '{' '.join(command)}'")
    timeout = max(2 * req.propagation_seconds, 10)
    try:
        code = run_subprocess(
            command,
            logger=getLogger("certbot"),
            timeout=timeout,
            shell=False,
            stdin=None,
            close_fds=True,
        )
        if code:
            raise ValueError("Certbot command failed! Check logs!")
    except TimeoutError:
        raise TimeoutError(f"Certbot command haven't finished "
                           f"in {timeout} seconds!")
    return certificates_dir


def dry_run_upload(req: CertbotRequest) -> None:
    """
    Dry runs upload with uploading an empty file to
    logs directory under specified path
    """
    client = get_storage_client(req.project)
    bucket: Bucket = client.get_bucket(req.target_bucket)
    now = datetime.now(tz=UTC)
    gcs_path: str = join(req.target_bucket_path, "logs",
                         now.strftime("%Y-%m-%d_%H-%M-%S_UTC"))
    info(f"Uploading log file to {gcs_path}")
    blob: Blob = bucket.blob(gcs_path)
    blob.upload_from_string(data="")
    info(f"Upload of log file has completed")


def init_server() -> WSGIServer:
    """
    Init server
    """
    port: int = 8080
    # noinspection HttpUrlsUsage
    info("App is about to start, visit http://{}:{}"
         .format("0.0.0.0", port))
    d = WSGIPathInfoDispatcher({"/": app})
    return WSGIServer(("0.0.0.0", port), d,
                      numthreads=10,
                      request_queue_size=50)


if __name__ == "__main__":
    configure_logger()
    server = init_server()
    # noinspection PyBroadException
    try:
        server.start()
    except KeyboardInterrupt:
        info("Server stopped")
    except BaseException:
        exception("Server stopped")
    finally:
        server.stop()
