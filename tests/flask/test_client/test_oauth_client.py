import mock
from unittest import TestCase
from flask import Flask, session
from authlib.integrations.flask_client import OAuth, OAuthError
from authlib.integrations.flask_client import FlaskRemoteApp
from tests.flask.cache import SimpleCache
from tests.client_base import (
    mock_send_value,
    get_bearer_token
)


class FlaskOAuthTest(TestCase):
    def test_register_remote_app(self):
        app = Flask(__name__)
        oauth = OAuth(app)
        self.assertRaises(AttributeError, lambda: oauth.dev)

        oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
        )
        self.assertEqual(oauth.dev.name, 'dev')
        self.assertEqual(oauth.dev.client_id, 'dev')

    def test_register_conf_from_app(self):
        app = Flask(__name__)
        app.config.update({
            'DEV_CLIENT_ID': 'dev',
            'DEV_CLIENT_SECRET': 'dev',
        })
        oauth = OAuth(app)
        oauth.register('dev')
        self.assertEqual(oauth.dev.client_id, 'dev')

    def test_register_with_overwrite(self):
        app = Flask(__name__)
        app.config.update({
            'DEV_CLIENT_ID': 'dev-1',
            'DEV_CLIENT_SECRET': 'dev',
            'DEV_ACCESS_TOKEN_PARAMS': {'foo': 'foo-1'}
        })
        oauth = OAuth(app)
        oauth.register(
            'dev', overwrite=True,
            client_id='dev',
            access_token_params={'foo': 'foo'}
        )
        self.assertEqual(oauth.dev.client_id, 'dev-1')
        self.assertEqual(oauth.dev.client_secret, 'dev')
        self.assertEqual(oauth.dev.access_token_params['foo'], 'foo-1')

    def test_init_app_later(self):
        app = Flask(__name__)
        app.config.update({
            'DEV_CLIENT_ID': 'dev',
            'DEV_CLIENT_SECRET': 'dev',
        })
        oauth = OAuth()
        remote = oauth.register('dev')
        self.assertRaises(RuntimeError, lambda: oauth.dev.client_id)
        oauth.init_app(app)
        self.assertEqual(oauth.dev.client_id, 'dev')
        self.assertEqual(remote.client_id, 'dev')

        self.assertIsNone(oauth.cache)
        self.assertIsNone(oauth.fetch_token)
        self.assertIsNone(oauth.update_token)

    def test_init_app_params(self):
        app = Flask(__name__)
        oauth = OAuth()
        oauth.init_app(app, SimpleCache())
        self.assertIsNotNone(oauth.cache)
        self.assertIsNone(oauth.update_token)

        oauth.init_app(app, update_token=lambda o: o)
        self.assertIsNotNone(oauth.update_token)

    def test_create_client(self):
        app = Flask(__name__)
        oauth = OAuth(app)
        self.assertIsNone(oauth.create_client('dev'))
        oauth.register('dev', client_id='dev')
        self.assertIsNotNone(oauth.create_client('dev'))

    def test_register_oauth1_remote_app(self):
        app = Flask(__name__)
        oauth = OAuth(app)
        oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            request_token_url='https://i.b/reqeust-token',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )
        self.assertEqual(oauth.dev.name, 'dev')
        self.assertEqual(oauth.dev.client_id, 'dev')

    def test_oauth1_authorize(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app, cache=SimpleCache())
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            request_token_url='https://i.b/reqeust-token',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )

        with app.test_request_context():
            with mock.patch('requests.sessions.Session.send') as send:
                send.return_value = mock_send_value('oauth_token=foo&oauth_verifier=baz')
                resp = client.authorize_redirect('https://b.com/bar')
                self.assertEqual(resp.status_code, 302)
                url = resp.headers.get('Location')
                self.assertIn('oauth_token=foo', url)
                self.assertIsNotNone(session.get('_dev_authlib_req_token_'))

            with mock.patch('requests.sessions.Session.send') as send:
                send.return_value = mock_send_value('oauth_token=a&oauth_token_secret=b')
                token = client.authorize_access_token()
                self.assertEqual(token['oauth_token'], 'a')

    def test_register_oauth2_remote_app(self):
        app = Flask(__name__)
        oauth = OAuth(app)
        oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            refresh_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize',
            update_token=lambda name: 'hi'
        )
        self.assertEqual(oauth.dev.name, 'dev')
        session = oauth.dev._get_oauth_client()
        self.assertIsNotNone(session.update_token)

    def test_oauth2_authorize(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )

        with app.test_request_context():
            resp = client.authorize_redirect('https://b.com/bar')
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get('Location')
            self.assertIn('state=', url)
            state = session['_dev_authlib_state_']
            self.assertIsNotNone(state)

        with app.test_request_context(path='/?code=a&state={}'.format(state)):
            # session is cleared in tests
            session['_dev_authlib_state_'] = state

            with mock.patch('requests.sessions.Session.send') as send:
                send.return_value = mock_send_value(get_bearer_token())
                token = client.authorize_access_token()
                self.assertEqual(token['access_token'], 'a')

        with app.test_request_context():
            self.assertEqual(client.token, None)

    def test_oauth2_authorize_via_custom_client(self):
        class CustomRemoteApp(FlaskRemoteApp):
            OAUTH_APP_CONFIG = {'authorize_url': 'https://i.b/custom'}

        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            client_cls=CustomRemoteApp,
        )
        with app.test_request_context():
            resp = client.authorize_redirect('https://b.com/bar')
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get('Location')
            self.assertTrue(url.startswith('https://i.b/custom?'))

    def test_oauth2_authorize_with_metadata(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
        )
        self.assertRaises(RuntimeError, client.create_authorization_url)

        client = oauth.register(
            'dev2',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            server_metadata_url='https://i.b/.well-known/openid-configuration'
        )
        with mock.patch('requests.sessions.Session.send') as send:
            send.return_value = mock_send_value({
                'authorization_endpoint': 'https://i.b/authorize'
            })

            with app.test_request_context():
                resp = client.authorize_redirect('https://b.com/bar')
                self.assertEqual(resp.status_code, 302)

    def test_oauth2_authorize_code_challenge(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize',
            client_kwargs={'code_challenge_method': 'S256'},
        )

        with app.test_request_context():
            resp = client.authorize_redirect('https://b.com/bar')
            self.assertEqual(resp.status_code, 302)
            url = resp.headers.get('Location')
            self.assertIn('code_challenge=', url)
            self.assertIn('code_challenge_method=S256', url)
            state = session['_dev_authlib_state_']
            self.assertIsNotNone(state)
            verifier = session['_dev_authlib_code_verifier_']
            self.assertIsNotNone(verifier)

        def fake_send(sess, req, **kwargs):
            self.assertIn('code_verifier={}'.format(verifier), req.body)
            return mock_send_value(get_bearer_token())

        path = '/?code=a&state={}'.format(state)
        with app.test_request_context(path=path):
            # session is cleared in tests
            session['_dev_authlib_state_'] = state
            session['_dev_authlib_code_verifier_'] = verifier

            with mock.patch('requests.sessions.Session.send', fake_send):
                token = client.authorize_access_token()
                self.assertEqual(token['access_token'], 'a')

    def test_openid_authorize(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize',
            client_kwargs={'scope': 'openid profile'},
        )

        with app.test_request_context():
            resp = client.authorize_redirect('https://b.com/bar')
            self.assertEqual(resp.status_code, 302)
            nonce = session['_dev_authlib_nonce_']
            self.assertIsNotNone(nonce)
            url = resp.headers.get('Location')
            self.assertIn('nonce={}'.format(nonce), url)

    def test_oauth2_access_token_with_post(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )
        payload = {'code': 'a', 'state': 'b'}
        with app.test_request_context(data=payload, method='POST'):
            session['_dev_authlib_state_'] = 'b'
            with mock.patch('requests.sessions.Session.send') as send:
                send.return_value = mock_send_value(get_bearer_token())
                token = client.authorize_access_token()
                self.assertEqual(token['access_token'], 'a')

    def test_access_token_with_fetch_token(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth()

        token = get_bearer_token()
        oauth.init_app(app, fetch_token=lambda name: token)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )

        def fake_send(sess, req, **kwargs):
            auth = req.headers['Authorization']
            self.assertEqual(auth, 'Bearer {}'.format(token['access_token']))
            resp = mock.MagicMock()
            resp.text = 'hi'
            resp.status_code = 200
            return resp

        with app.test_request_context():
            with mock.patch('requests.sessions.Session.send', fake_send):
                resp = client.get('/api/user')
                self.assertEqual(resp.text, 'hi')

                # trigger ctx.authlib_client_oauth_token
                resp = client.get('/api/user')
                self.assertEqual(resp.text, 'hi')

    def test_request_with_refresh_token(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth()

        expired_token = {
            'token_type': 'Bearer',
            'access_token': 'expired-a',
            'refresh_token': 'expired-b',
            'expires_in': '3600',
            'expires_at': 1566465749,
        }
        oauth.init_app(app, fetch_token=lambda name: expired_token)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            refresh_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )

        def fake_send(sess, req, **kwargs):
            if req.url == 'https://i.b/token':
                auth = req.headers['Authorization']
                self.assertIn('Basic', auth)
                resp = mock.MagicMock()
                resp.json = get_bearer_token
                resp.status_code = 200
                return resp

            resp = mock.MagicMock()
            resp.text = 'hi'
            resp.status_code = 200
            return resp

        with app.test_request_context():
            with mock.patch('requests.sessions.Session.send', fake_send):
                resp = client.get('/api/user', token=expired_token)
                self.assertEqual(resp.text, 'hi')

    def test_request_without_token(self):
        app = Flask(__name__)
        app.secret_key = '!'
        oauth = OAuth(app)
        client = oauth.register(
            'dev',
            client_id='dev',
            client_secret='dev',
            api_base_url='https://i.b/api',
            access_token_url='https://i.b/token',
            authorize_url='https://i.b/authorize'
        )

        def fake_send(sess, req, **kwargs):
            auth = req.headers.get('Authorization')
            self.assertIsNone(auth)
            resp = mock.MagicMock()
            resp.text = 'hi'
            resp.status_code = 200
            return resp

        with app.test_request_context():
            with mock.patch('requests.sessions.Session.send', fake_send):
                resp = client.get('/api/user', withhold_token=True)
                self.assertEqual(resp.text, 'hi')
                self.assertRaises(OAuthError, client.get, 'https://i.b/api/user')
