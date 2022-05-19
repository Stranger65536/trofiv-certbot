# coding=utf-8
"""
Server entry point
"""
from logging import info, exception
from typing import Dict
from wsgiref.simple_server import WSGIServer

from cheroot.wsgi import PathInfoDispatcher as WSGIPathInfoDispatcher
from cheroot.wsgi import Server as WSGIServer
from flask import Flask, jsonify, request
from marshmallow import ValidationError

from dto import CertbotRequest
from errors import SecretFetchError, CertbotTimeoutError, CertbotError, \
    GCSUploadError
from service import dry_run_upload, issue_certificate
from utils import configure_logger

# noinspection PyPackageRequirements

app = Flask(__name__)


@app.route("/certs",
           endpoint="certs",
           methods=["POST"])
def renew_certificates():
    """
    Job submit endpoint
    """
    req = CertbotRequest.from_request(request)
    dry_run_upload(req)
    result: Dict[str, str] = issue_certificate(req)
    return jsonify({
        "success": True,
        "result": result
    })


@app.errorhandler(ValidationError)
def handle_api_error(error: ValidationError):
    """
    Handles api errors
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "Request is invalid",
            "errors": error.messages
        }
    }

    return jsonify(response), 400


@app.errorhandler(SecretFetchError)
def handle_secret_error(error: SecretFetchError):
    """
    Handles secret fetch errors
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "There is a problem with DNS provider "
                       "secret fetch error. Check logs for details.",
        }
    }

    return jsonify(response), 500


@app.errorhandler(GCSUploadError)
def handle_gcs_upload_error(error: GCSUploadError):
    """
    Handles errors related to GCS bucket uploads
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "There is a problem with file upload to GCS.",
            "source_path": error.source_path,
            "bucket": error.bucket_name,
            "bucket_path": error.bucket_path,
        }
    }

    return jsonify(response), 500


@app.errorhandler(CertbotTimeoutError)
def handle_certbot_timeout_error(error: CertbotTimeoutError):
    """
    Handles secret fetch errors
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "Certbot instance aborted by timeout",
            "command": error.cmd,
            "timeout": error.timeout,
            "output": error.output.split("\n")
        }
    }

    return jsonify(response), 500


@app.errorhandler(CertbotError)
def handle_certbot_error(error: CertbotError):
    """
    Handles secret fetch errors
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "Certbot instance failed",
            "command": error.cmd,
            "timeout": error.timeout,
            "output": error.output.split("\n")
        }
    }

    return jsonify(response), 500


@app.errorhandler(Exception)
def handle_error(error: Exception):
    """
    Handles generic errors
    """
    response = {
        "success": False,
        "error": {
            "type": error.__class__.__name__,
            "message": "Generic error happened. Check logs for details",
        }
    }

    return jsonify(response), 500


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
