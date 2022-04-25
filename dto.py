# coding=utf-8
"""
Request / response classes
"""
from dataclasses import dataclass
from typing import List, Optional, Type, Dict

from flask import Request
from marshmallow import Schema, fields, validate, post_load, \
    ValidationError, validates
from marshmallow.validate import OneOf

from providers import providers


def validation_errors(cls: Type) -> Dict[str, str]:
    """
    Populates validation messages with class info
    """
    name = cls.__name__
    return {
        "required": "Missing data for required field for class "
                    "{}".format(name),
        "null": "Field of may not be null for class "
                "{}".format(name),
        "validator_failed": "Invalid value for class "
                            "{}".format(name),
    }


@dataclass
class CertbotRequest(object):
    """
    Certbot request to issue SSL certificates
    """
    provider: str
    secret_id: str
    project: str
    domains: List[str]
    email: str
    target_bucket: str
    target_bucket_path: str
    propagation_seconds: Optional[int] = None

    @staticmethod
    def from_request(req: Request) -> "CertbotRequest":
        """
        Parses request
        """
        json = req.get_json(silent=True, force=True)
        if json is None:
            raise ValidationError("Request json is absent or invalid!")
        return CertbotRequestSchema().load(json)


class CertbotRequestSchema(Schema):
    """
    Validation schema for request
    """
    # noinspection PyTypeChecker
    provider = fields.Str(
        required=True,
        data_key="provider",
        validate=OneOf(sorted(set(providers.keys()))),
        error_messages=validation_errors(CertbotRequest))
    secret_id = fields.Str(
        required=True,
        data_key="secret_id",
        error_messages=validation_errors(CertbotRequest))
    project = fields.Str(
        required=True,
        data_key="project",
        error_messages=validation_errors(CertbotRequest))
    domains = fields.List(
        fields.Str(),
        required=True,
        data_key="domains",
        error_messages=validation_errors(CertbotRequest))
    propagation_seconds = fields.Int(
        required=False,
        validate=validate.Range(min=1,
                                error="Value must be greater than 0"),
        default=60,
        missing=60,
        data_key="propagation_seconds",
        error_messages=validation_errors(CertbotRequest))
    email = fields.Email(
        required=True,
        data_key="email",
        error_messages=validation_errors(CertbotRequest)
    )
    target_bucket = fields.Str(
        required=True,
        data_key="target_bucket",
        error_messages=validation_errors(CertbotRequest))
    target_bucket_path = fields.Str(
        required=True,
        data_key="target_bucket_path",
        error_messages=validation_errors(CertbotRequest))

    @validates('domains')
    def validate_length(self, value):
        """
        Validates domains list length
        """
        if len(value) < 1:
            raise ValidationError("Domains list can't be empty!")

    @validates('domains')
    def validate_unique_domains(self, value):
        """
        Validates domains list uniqueness
        """
        if len(set(value)) != len(value):
            raise ValidationError(
                "Domains list can't contain duplicates!")

    # noinspection PyUnusedLocal
    @post_load
    def make_entity(self, data, **kwargs):
        """
        Makes entity from object
        """
        return CertbotRequest(**data)
