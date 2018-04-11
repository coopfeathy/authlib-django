import logging
from requests import Session
from requests.auth import HTTPBasicAuth
from .errors import OAuthException
from ..common.security import generate_token
from ..common.urls import url_decode, add_params_to_qs
from ..specs.rfc6749.parameters import (
    prepare_grant_uri,
    prepare_token_request,
    parse_authorization_code_response,
    parse_implicit_response,
)
from ..specs.rfc6749 import OAuth2Token
from ..specs.rfc6749 import InsecureTransportError
from ..specs.rfc6750 import add_bearer_token
from ..specs.rfc7009 import prepare_revoke_token_request

__all__ = ['OAuth2Session', 'OAuth2ClientAuth']

log = logging.getLogger(__name__)
DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
}


class OAuth2Session(Session):
    """Construct a new OAuth 2 client requests session.

    :param client_id: Client ID, which you get from client registration.
    :param client_secret: Client Secret, which you get from registration.
    :param token_endpoint_auth_method: Client auth method for token endpoint.
    :param refresh_token_url: Refresh Token endpoint for auto refresh token.
    :param refresh_token_params: Extra parameters for refresh token endpoint.
    :param scope: Scope that you needed to access user resources.
    :param redirect_uri: Redirect URI you registered as callback.
    :param token: A dict of token attributes such as ``access_token``,
                  ``token_type`` and ``expires_at``.
    :param token_placement: The place to put token in HTTP request. Available
                            values: "header", "body", "uri".
    :param state: State string used to prevent CSRF. This will be given
                  when creating the authorization url and must be
                  supplied when parsing the authorization response.
    :param token_updater: A function for you to update token. It accept a
                          :class:`OAuth2Token` as parameter.
    """
    def __init__(self, client_id=None, client_secret=None,
                 token_endpoint_auth_method='client_secret_basic',
                 refresh_token_url=None, refresh_token_params=None,
                 scope=None, redirect_uri=None,
                 token=None, token_placement='header',
                 state=None, token_updater=None, **kwargs):
        super(OAuth2Session, self).__init__()

        self.client_id = client_id
        self._token = None
        self._client_auth = OAuth2ClientAuth(
            client_id, client_secret,
            auth_method=token_endpoint_auth_method)

        self.refresh_token_url = refresh_token_url
        self.refresh_token_params = refresh_token_params

        self.scope = scope
        self.redirect_uri = redirect_uri

        self.token = token
        self.token_placement = token_placement

        self.state = state
        self.token_updater = token_updater

        self._kwargs = kwargs

        self.compliance_hook = {
            'access_token_response': set(),
            'refresh_token_response': set(),
            'protected_request': set(),
            'revoke_token_request': set(),
        }

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, token):
        if isinstance(token, dict) and not isinstance(token, OAuth2Token):
            token = OAuth2Token(token)
        self._token = token

    def add_token(self, url, headers, data):
        if not self.token:
            raise RuntimeError('There is no "token"')

        token_type = self.token['token_type'].lower()
        if token_type == 'bearer':
            return add_bearer_token(
                self.token['access_token'],
                url, headers, data, self.token_placement)
        raise RuntimeError('Unsupported "token_type"')

    def authorization_url(self, url, state=None, **kwargs):
        """Generate an authorization URL.

        :param url: Authorization endpoint url, must be HTTPS.
        :param state: An optional state string for CSRF protection. If not
                      given it will be generated for you.
        :param kwargs: Extra parameters to include.
        :return: authorization_url, state
        """
        state = state or self.state
        if state is None:
            state = generate_token()

        response_type = self._kwargs.get('response_type', 'code')
        response_type = kwargs.pop('response_type', response_type)
        if 'redirect_uri' not in kwargs:
            kwargs['redirect_uri'] = self.redirect_uri
        if 'scope' not in kwargs:
            kwargs['scope'] = self.scope
        uri = prepare_grant_uri(
            url, client_id=self.client_id, response_type=response_type,
            state=state, **kwargs)
        return uri, state

    def fetch_access_token(
            self, url=None, code=None, authorization_response=None,
            body='', auth=None, username=None, password=None, method='POST',
            headers=None, timeout=None, verify=True, proxies=None, **kwargs):
        """Generic method for fetching an access token from the token endpoint.

        :param url: Access Token endpoint URL, if not configured,
                    ``authorization_response`` is used to extract token from
                    its fragment (implicit way).
        :param code: Authorization code (if any)
        :param authorization_response: Authorization response URL, the callback
                                       URL of the request back to you. We can
                                       extract authorization code from it.
        :param body: Optional application/x-www-form-urlencoded body to add the
                     include in the token request. Prefer kwargs over body.
        :param auth: An auth tuple or method as accepted by requests.
        :param username: Username of the resource owner for password grant.
        :param password: Password of the resource owner for password grant.
        :param method: The HTTP method used to make the request. Defaults
                       to POST, but may also be GET. Other methods should
                       be added as needed.
        :param headers: Dict to default request headers with.
        :param timeout: Timeout of the request in seconds.
        :param verify: Verify SSL certificate.
        :param proxies: Proxies to use with requests.
        :param kwargs: Extra parameters to include in the token request.
        :return: A :class:`OAuth2Token` object (a dict too).
        """
        if url is None and authorization_response:
            return self.token_from_fragment(authorization_response)

        InsecureTransportError.check(url)

        if code or authorization_response:
            body = self._prepare_authorization_code_body(
                code, authorization_response, body, **kwargs)
        elif username and password:
            body = prepare_token_request(
                'password', body,
                username=username, password=password,
                client_id=self.client_id, **kwargs)
        else:
            grant_type = kwargs.pop('grant_type', 'client_credentials')
            body = prepare_token_request(
                grant_type, body, client_id=self.client_id, **kwargs)

        if auth is None:
            auth = self._client_auth

        if headers is None:
            headers = DEFAULT_HEADERS

        if method.upper() == 'POST':
            resp = self.post(
                url, data=dict(url_decode(body)), timeout=timeout,
                headers=headers, auth=auth, verify=verify, proxies=proxies,
                withhold_token=True)
        else:
            resp = self.get(
                url, params=dict(url_decode(body)), timeout=timeout,
                headers=headers, auth=auth, verify=verify, proxies=proxies,
                withhold_token=True)

        for hook in self.compliance_hook['access_token_response']:
            resp = hook(resp)

        return self._parse_and_validate_token(resp.json())

    def fetch_token(self, url, **kwargs):
        """Alias for fetch_access_token. Compatible with requests-oauthlib."""
        return self.fetch_access_token(url, **kwargs)

    def token_from_fragment(self, authorization_response):
        params = parse_implicit_response(authorization_response, self.state)
        return self._parse_and_validate_token(params)

    def refresh_token(self, url, refresh_token=None, body='', auth=None,
                      headers=None, timeout=None, verify=True,
                      proxies=None, **kwargs):
        """Fetch a new access token using a refresh token.

        :param url: Refresh Token endpoint, must be HTTPS.
        :param refresh_token: The refresh_token to use.
        :param body: Optional application/x-www-form-urlencoded body to add the
                     include in the token request. Prefer kwargs over body.
        :param auth: An auth tuple or method as accepted by requests.
        :param headers: Dict to default request headers with.
        :param timeout: Timeout of the request in seconds.
        :param verify: Verify SSL certificate.
        :param proxies: Proxies to use with requests.
        :param kwargs: Extra parameters to include in the token request.
        :return: A :class:`OAuth2Token` object (a dict too).
        """
        refresh_token = refresh_token or self.token.get('refresh_token')
        if self.refresh_token_params is not None:
            kwargs.update(self.refresh_token_params)

        body = prepare_token_request(
            'refresh_token', body=body, scope=self.scope,
            refresh_token=refresh_token, **kwargs)

        if headers is None:
            headers = DEFAULT_HEADERS

        resp = self.post(
            url, data=dict(url_decode(body)), auth=auth, timeout=timeout,
            headers=headers, verify=verify, withhold_token=True,
            proxies=proxies)

        for hook in self.compliance_hook['refresh_token_response']:
            resp = hook(resp)

        self._parse_and_validate_token(resp.json())
        if 'refresh_token' not in self.token:
            self.token['refresh_token'] = refresh_token

        if callable(self.token_updater):
            self.token_updater(self.token)
        return self.token

    def revoke_token(self, url, token, token_type_hint=None,
                     body=None, auth=None, headers=None, timeout=None,
                     verify=True, proxies=None, **kwargs):
        """Revoke token method defined via `RFC7009`_.

        :param url: Revoke Token endpoint, must be HTTPS.
        :param token: The token to be revoked.
        :param token_type_hint: The type of the token that to be revoked.
                                It can be "access_token" or "refresh_token".
        :param body: Optional application/x-www-form-urlencoded body to add the
                     include in the token request. Prefer kwargs over body.
        :param auth: An auth tuple or method as accepted by requests.
        :param headers: Dict to default request headers with.
        :param timeout: Timeout of the request in seconds.
        :param verify: Verify SSL certificate.
        :param proxies: Proxies to use with requests.
        :param kwargs: Extra parameters to include in the token request.
        :return: A :class:`OAuth2Token` object (a dict too).

        .. _`RFC7009`: https://tools.ietf.org/html/rfc7009
        """
        if body is None:
            body = ''

        data, headers = prepare_revoke_token_request(
            token, token_type_hint, body, headers)

        for hook in self.compliance_hook['revoke_token_request']:
            url, headers, data = hook(url, headers, data)

        if auth is None:
            auth = self._client_auth

        return self.post(
            url, data=dict(url_decode(data)), timeout=timeout,
            headers=headers, auth=auth, verify=verify, proxies=proxies,
            withhold_token=True)

    def request(self, method, url, data=None, headers=None,
                withhold_token=False, auth=None, **kwargs):

        if self.token and not withhold_token:
            if self.token.is_expired():
                if not self.refresh_token_url:
                    raise OAuthException('Token is expired.')

                if auth is None:
                    auth = self._client_auth

                self.refresh_token(self.refresh_token_url, auth=auth, **kwargs)

            url, headers, data = self.add_token(url, headers, data)

            for hook in self.compliance_hook['protected_request']:
                url, headers, data = hook(url, headers, data)

        return super(OAuth2Session, self).request(
            method, url, headers=headers, data=data, auth=auth, **kwargs)

    def register_compliance_hook(self, hook_type, hook):
        """Register a hook for request/response tweaking.

        Available hooks are:

        * access_token_response: invoked before token parsing.
        * refresh_token_response: invoked before refresh token parsing.
        * protected_request: invoked before making a request.
        * revoke_token_request: invoked before revoking a token.
        """
        if hook_type not in self.compliance_hook:
            raise ValueError('Hook type %s is not in %s.',
                             hook_type, self.compliance_hook)
        self.compliance_hook[hook_type].add(hook)

    def _parse_and_validate_token(self, params):
        if 'error' not in params:
            self.token = params
            return self.token

        error = params['error']
        description = params.get('error_description', error)
        raise OAuthException(description, type=error)

    def _prepare_authorization_code_body(self, code, authorization_response,
                                         body, **kwargs):
        state = kwargs.pop('state', None)
        if not state:
            state = self.state

        if not code and authorization_response:
            params = parse_authorization_code_response(
                authorization_response,
                state=state
            )
            code = params['code']
        if 'redirect_uri' not in kwargs:
            kwargs['redirect_uri'] = self.redirect_uri
        return prepare_token_request(
            'authorization_code', body=body,
            client_id=self.client_id,
            code=code, state=state,
            **kwargs)


class OAuth2ClientAuth(HTTPBasicAuth):
    """Attaches OAuth Client Authentication to the given Request object.

    :param client_id: Client ID, which you get from client registration.
    :param client_secret: Client Secret, which you get from registration.
    :param auth_method: Client auth method for token endpoint. The supported
        methods for now:

        * client_secret_basic
        * client_secret_post
        * client_secret_none
    """
    def __init__(self, client_id, client_secret,
                 auth_method='client_secret_basic'):
        super(OAuth2ClientAuth, self).__init__(client_id, client_secret)
        self.auth_method = auth_method

    def __call__(self, req):
        if self.auth_method == 'client_secret_basic':
            return super(OAuth2ClientAuth, self).__call__(req)
        if self.auth_method == 'client_secret_post':
            req.body = add_params_to_qs(req.body or '', [
                ('client_id', self.username),
                ('client_secret', self.password or '')
            ])
        elif self.auth_method == 'client_secret_none':
            if req.method == 'GET':
                req.url = add_params_to_qs(req.url, [
                    ('client_id', self.username)
                ])
            elif req.method == 'POST':
                req.body = add_params_to_qs(req.body or '', [
                    ('client_id', self.username)
                ])
        return req
