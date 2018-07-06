import unittest
from authlib.specs.rfc7516 import JWE, errors
from authlib.specs.rfc7518 import JWE_ALGORITHMS, JWS_ALGORITHMS
from tests.util import read_file_path


class JWETest(unittest.TestCase):
    def test_register_invalid_algorithms(self):
        jwe = JWE(algorithms=[])
        self.assertRaises(
            ValueError,
            jwe.register_algorithm,
            JWS_ALGORITHMS[0]
        )

    def test_not_enough_segments(self):
        s = 'a.b.c'
        jwe = JWE(algorithms=JWE_ALGORITHMS)
        self.assertRaises(
            errors.DecodeError,
            jwe.deserialize_compact,
            s, None
        )

    def test_compact_rsa(self):
        jwe = JWE(algorithms=JWE_ALGORITHMS)
        s = jwe.serialize_compact(
            {'alg': 'RSA-OAEP', 'enc': 'A256GCM'},
            'hello',
            read_file_path('rsa_public.pem')
        )
        data = jwe.deserialize_compact(s, read_file_path('rsa_private.pem'))
        header, payload = data['header'], data['payload']
        self.assertEqual(payload, b'hello')
        self.assertEqual(header['alg'], 'RSA-OAEP')

    def test_with_zip_header(self):
        jwe = JWE(algorithms=JWE_ALGORITHMS)
        s = jwe.serialize_compact(
            {'alg': 'RSA-OAEP', 'enc': 'A128CBC-HS256', 'zip': 'DEF'},
            'hello',
            read_file_path('rsa_public.pem')
        )
        data = jwe.deserialize_compact(s, read_file_path('rsa_private.pem'))
        header, payload = data['header'], data['payload']
        self.assertEqual(payload, b'hello')
        self.assertEqual(header['alg'], 'RSA-OAEP')

    def test_rsa_alg(self):
        alg = _find_alg('RSA-OAEP')
        pub_key = alg.prepare_public_key(
            read_file_path('rsa_public.pem'))
        private_key = alg.prepare_private_key(
            read_file_path('rsa_private.pem'))
        cek = (
            b'\xb1\xa1\xf4\x80T\x8f\xe1s?\xb4\x03\xffk\x9a\xd4\xf6\x8a\x07'
            b'n[p."i/\x82\xcb.z\xea@\xfc'
        )
        ek = alg.wrap(cek, {}, pub_key)
        self.assertEqual(alg.unwrap(ek, {}, private_key), cek)

        invalid_ek = b'a' + ek[1:]
        self.assertRaises(ValueError, alg.unwrap, invalid_ek, {}, private_key)


def _find_alg(name):
    for alg in JWE_ALGORITHMS:
        if alg.name == name:
            return alg
