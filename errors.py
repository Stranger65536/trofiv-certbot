# coding=utf-8
"""
Business logic exceptions
"""
from typing import Union, List


class ManagedException(Exception):
    """
    Base class for business exceptions
    """


class SecretFetchError(ManagedException):
    """
    Intended to be thrown when there is a problem with
    DNS provider secrets fetch
    """
    pass


class CertbotError(ManagedException):
    """
    Intended to be thrown when there is a problem with
    certbot binary execution
    """
    cmd: Union[str, List[str]]
    timeout: float
    output: str

    def __init__(
        self,
        cmd: Union[str, List[str]],
        timeout: float,
        output: str,
        *args: object,
    ) -> None:
        super().__init__(*args)
        self.cmd = cmd
        self.timeout = timeout
        self.output = output


class GCSError(ManagedException):
    """
    Intended to be thrown when there is a problem with GCS
    """
    bucket_name: str

    def __init__(
        self,
        bucket_name: str,
        *args: object
    ) -> None:
        super().__init__(*args)
        self.bucket_name = bucket_name


class GCSUploadError(GCSError):
    """
    Intended to be thrown when there is a problem with uploading
    data to GCS
    """
    source_path: str
    bucket_path: str

    def __init__(
        self, source_path: str,
        bucket_name: str,
        bucket_path: str,
        *args: object
    ) -> None:
        super().__init__(bucket_name, *args)
        self.source_path = source_path
        self.bucket_path = bucket_path


class CertbotTimeoutError(CertbotError):
    """
    Intended to be thrown when certbot command hangs
    """

    def __init__(
        self,
        cmd: Union[str, List[str]],
        timeout: float,
        output: str,
        *args: object,
    ) -> None:
        super().__init__(cmd=cmd, timeout=timeout, output=output, *args)
