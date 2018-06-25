"""
    authlib.specs.rfc7515
    ~~~~~~~~~~~~~~~~~~~~~

    This module represents a direct implementation of
    JSON Web Signature (JWS).

    https://tools.ietf.org/html/rfc7515
"""

from .jws import JWS
from .models import JWSAlgorithm, JWSHeader
from .errors import *

__all__ = ['JWS', 'JWSAlgorithm', 'JWSHeader']
