import time
from .signature import (
    SIGNATURE_HMAC_SHA1,
    SIGNATURE_PLAINTEXT,
    SIGNATURE_RSA_SHA1,
)
from .signature import (
    verify_hmac_sha1,
    verify_plaintext,
    verify_rsa_sha1,
)
from .errors import (
    InvalidRequestError,
    MissingRequiredParameterError,
    UnsupportedSignatureMethodError,
    InvalidNonceError,
    InvalidSignatureError,
)


class BaseServer(object):
    SIGNATURE_METHODS = {
        SIGNATURE_HMAC_SHA1: verify_hmac_sha1,
        SIGNATURE_RSA_SHA1: verify_rsa_sha1,
        SIGNATURE_PLAINTEXT: verify_plaintext,
    }
    SUPPORTED_SIGNATURE_METHODS = [SIGNATURE_HMAC_SHA1]
    EXPIRY_TIME = 300

    @classmethod
    def register_signature_method(cls, name, verify):
        """Extend signature method verification.

        :param name: A string to represent signature method.
        :param verify: A function to verify signature.

        The ``verify`` method accept ``OAuth1Request`` as parameter::

            def verify_custom_method(request):
                # verify this request, return True or False
                return True

            Server.register_signature_method('custom-name', verify_custom_method)
        """
        cls.SIGNATURE_METHODS[name] = verify

    def __init__(self, client_model):
        self.client_model = client_model

    def validate_timestamp_and_nonce(self, request):
        """Validate ``oauth_timestamp`` and ``oauth_nonce`` in HTTP request.

        :param request: OAuth1Request instance
        """
        # The parameters MAY be omitted when using the "PLAINTEXT"
        # signature method
        if request.signature_method == SIGNATURE_PLAINTEXT:
            return False

        timestamp = request.oauth_params.get('oauth_timestamp')
        nonce = request.oauth_params.get('oauth_nonce')

        if not timestamp:
            raise MissingRequiredParameterError('oauth_timestamp')
        try:
            # The timestamp value MUST be a positive integer
            delta = time.time() - int(timestamp)
            if delta > self.EXPIRY_TIME:
                raise InvalidRequestError('Invalid "oauth_timestamp" value')
        except (ValueError, TypeError):
            raise InvalidRequestError('Invalid "oauth_timestamp" value')

        if not nonce:
            raise MissingRequiredParameterError('oauth_nonce')

        if self.exists_nonce(nonce, request):
            raise InvalidNonceError()

    def validate_oauth_signature(self, request):
        """Validate ``oauth_signature`` from HTTP request.

        :param request: OAuth1Request instance
        """
        method = request.signature_method
        if not method:
            raise MissingRequiredParameterError('oauth_signature_method')

        if method not in self.SUPPORTED_SIGNATURE_METHODS:
            raise UnsupportedSignatureMethodError()

        if not request.signature:
            raise MissingRequiredParameterError('oauth_signature')

        verify = self.SIGNATURE_METHODS.get(method)
        if not verify:
            raise UnsupportedSignatureMethodError()

        if not verify(request):
            raise InvalidSignatureError()

    def exists_nonce(self, nonce, request):
        """The nonce value MUST be unique across all requests with the same
        timestamp, client credentials, and token combinations.

        :param nonce: A string value of ``oauth_nonce``
        :param request: OAuth1Request instance
        :return: Boolean
        """
        raise NotImplementedError()
