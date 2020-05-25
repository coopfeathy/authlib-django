from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey, Ed25519PrivateKey
)
from authlib.jose.rfc7515 import JWSAlgorithm
from ._key_cryptography import OKPKey


class EdDSAAlgorithm(JWSAlgorithm):
    name = 'EdDSA'
    description = 'Edwards-curve Digital Signature Algorithm for JWS'
    private_key_cls = Ed25519PrivateKey
    public_key_cls = Ed25519PublicKey

    def prepare_key(self, raw_data):
        return OKPKey.from_raw(raw_data)

    def sign(self, msg, key):
        op_key = key.get_operation_key('sign')
        return op_key.sign(msg)

    def verify(self, msg, sig, key):
        op_key = key.get_operation_key('verify')
        try:
            op_key.verify(sig, msg)
            return True
        except InvalidSignature:
            return False
