import json
from authlib.oauth2.rfc6749 import grants, errors
from authlib.common.urls import urlparse, url_decode
from django.test import override_settings
from .models import User, Client
from .models import CodeGrantMixin, generate_authorization_code
from .oauth2_server import TestCase


class AuthorizationCodeGrant(CodeGrantMixin, grants.AuthorizationCodeGrant):
    def create_authorization_code(self, client, grant_user, request):
        return generate_authorization_code(client, grant_user, request)



class AuthorizationCodeTest(TestCase):
    def create_server(self):
        server = super(AuthorizationCodeTest, self).create_server()
        server.register_grant(AuthorizationCodeGrant)
        return server

    def prepare_data(self, response_type='code', grant_type='authorization_code', scope=''):
        user = User(username='foo')
        user.save()
        client = Client(
            user_id=user.pk,
            client_id='client',
            client_secret='secret',
            response_type=response_type,
            grant_type=grant_type,
            scope=scope,
            token_endpoint_auth_method='client_secret_basic',
            default_redirect_uri='https://a.b',
        )
        client.save()

    def test_validate_consent_request_client(self):
        server = self.create_server()
        url = '/authorize?response_type=code'
        request = self.factory.get(url)
        self.assertRaises(
            errors.InvalidClientError,
            server.validate_consent_request,
            request
        )

        url = '/authorize?response_type=code&client_id=client'
        request = self.factory.get(url)
        self.assertRaises(
            errors.InvalidClientError,
            server.validate_consent_request,
            request
        )

        self.prepare_data(response_type='')
        self.assertRaises(
            errors.UnauthorizedClientError,
            server.validate_consent_request,
            request
        )

    def test_validate_consent_request_redirect_uri(self):
        server = self.create_server()
        self.prepare_data()

        base_url = '/authorize?response_type=code&client_id=client'
        url = base_url + '&redirect_uri=https%3A%2F%2Fa.c'
        request = self.factory.get(url)
        self.assertRaises(
            errors.InvalidRequestError,
            server.validate_consent_request,
            request
        )

        url = base_url + '&redirect_uri=https%3A%2F%2Fa.b'
        request = self.factory.get(url)
        grant = server.validate_consent_request(request)
        self.assertIsInstance(grant, AuthorizationCodeGrant)

    def test_validate_consent_request_scope(self):
        server = self.create_server()
        server.metadata = {'scopes_supported': ['profile']}

        self.prepare_data()
        base_url = '/authorize?response_type=code&client_id=client'
        url = base_url + '&scope=invalid'
        request = self.factory.get(url)
        self.assertRaises(
            errors.InvalidScopeError,
            server.validate_consent_request,
            request
        )

    def test_create_authorization_response(self):
        server = self.create_server()
        self.prepare_data()
        data = {'response_type': 'code', 'client_id': 'client'}
        request = self.factory.post('/authorize', data=data)
        server.validate_consent_request(request)

        resp = server.create_authorization_response(request)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('error=access_denied', resp['Location'])

        grant_user = User.objects.get(username='foo')
        resp = server.create_authorization_response(request, grant_user=grant_user)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('code=', resp['Location'])

    def test_create_token_response_invalid(self):
        server = self.create_server()
        self.prepare_data()

        # case: no auth
        request = self.factory.post('/oauth/token', data={'grant_type': 'authorization_code'})
        resp = server.create_token_response(request)
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.content)
        self.assertEqual(data['error'], 'invalid_client')

        auth_header = self.create_basic_auth('client', 'secret')

        # case: no code
        request = self.factory.post(
            '/oauth/token',
            data={'grant_type': 'authorization_code'},
            HTTP_AUTHORIZATION=auth_header,
        )
        resp = server.create_token_response(request)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertEqual(data['error'], 'invalid_request')

        # case: invalid code
        request = self.factory.post(
            '/oauth/token',
            data={'grant_type': 'authorization_code', 'code': 'invalid'},
            HTTP_AUTHORIZATION=auth_header,
        )
        resp = server.create_token_response(request)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertEqual(data['error'], 'invalid_request')

    def test_create_token_response_success(self):
        self.prepare_data()
        data = self.get_token_response()
        self.assertIn('access_token', data)
        self.assertNotIn('refresh_token', data)

    @override_settings(
        AUTHLIB_OAUTH2_PROVIDER={'refresh_token_generator': True})
    def test_create_token_response_with_refresh_token(self):
        self.prepare_data(grant_type='authorization_code\nrefresh_token')
        data = self.get_token_response()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

    def get_token_response(self):
        server = self.create_server()
        data = {'response_type': 'code', 'client_id': 'client'}
        request = self.factory.post('/authorize', data=data)
        grant_user = User.objects.get(username='foo')
        resp = server.create_authorization_response(request, grant_user=grant_user)
        self.assertEqual(resp.status_code, 302)

        params = dict(url_decode(urlparse.urlparse(resp['Location']).query))
        code = params['code']

        request = self.factory.post(
            '/oauth/token',
            data={'grant_type': 'authorization_code', 'code': code},
            HTTP_AUTHORIZATION=self.create_basic_auth('client', 'secret'),
        )
        resp = server.create_token_response(request)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        return data
