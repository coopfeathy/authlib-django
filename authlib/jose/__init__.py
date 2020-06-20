"""
    authlib.jose
    ~~~~~~~~~~~~

    JOSE implementation in Authlib. Tracking the status of JOSE specs at
    https://tools.ietf.org/wg/jose/
"""
from .drafts import JWE_ENC_ALGORITHMS as DRAFT_JWE_ENC_ALGORITHMS
from .rfc7515 import (
    JsonWebSignature, JWSAlgorithm, JWSHeader, JWSObject,
)
from .rfc7516 import (
    JsonWebEncryption, JWEAlgorithm, JWEEncAlgorithm, JWEZipAlgorithm,
)
from .rfc7517 import Key, KeySet
from .rfc7518 import (
    register_jws_rfc7518,
    JWE_ALGORITHMS,
    JWE_ALG_ALGORITHMS,
    JWE_ENC_ALGORITHMS,
    JWE_ZIP_ALGORITHMS,
    ECDHAlgorithm,
    OctKey,
    RSAKey,
    ECKey,
)
from .rfc7519 import JsonWebToken, BaseClaims, JWTClaims
from .rfc8037 import OKPKey, register_jws_rfc8037
from .errors import JoseError
from .jwk import JsonWebKey

# register algorithms
register_jws_rfc7518()
register_jws_rfc8037()

# attach algorithms
ECDHAlgorithm.ALLOWED_KEY_CLS = (ECKey, OKPKey)

JWE_ENC_ALGORITHMS.extend(DRAFT_JWE_ENC_ALGORITHMS)
JWE_ALGORITHMS.extend(DRAFT_JWE_ENC_ALGORITHMS)
JsonWebEncryption.JWE_AVAILABLE_ALGORITHMS = {alg.name: alg for alg in JWE_ALGORITHMS}

# register supported keys
JsonWebKey.JWK_KEY_CLS = {
    OctKey.kty: OctKey,
    RSAKey.kty: RSAKey,
    ECKey.kty: ECKey,
    OKPKey.kty: OKPKey,
}

# compatible constants
JWS_ALGORITHMS = JsonWebSignature.ALGORITHMS_REGISTRY.keys()

# compatible imports
JWS = JsonWebSignature
JWE = JsonWebEncryption
JWK = JsonWebKey
JWT = JsonWebToken

jwt = JsonWebToken()


__all__ = [
    'JoseError',

    'JWS', 'JsonWebSignature', 'JWSAlgorithm', 'JWSHeader', 'JWSObject',
    'JWE', 'JsonWebEncryption', 'JWEAlgorithm', 'JWEEncAlgorithm', 'JWEZipAlgorithm',

    'JWK', 'JsonWebKey', 'Key', 'KeySet',

    'JWS_ALGORITHMS',
    'JWE_ALGORITHMS',
    'JWE_ALG_ALGORITHMS',
    'JWE_ENC_ALGORITHMS',
    'JWE_ZIP_ALGORITHMS',

    'OctKey', 'RSAKey', 'ECKey', 'OKPKey',

    'JWT', 'JsonWebToken', 'BaseClaims', 'JWTClaims',
    'jwt',
]
