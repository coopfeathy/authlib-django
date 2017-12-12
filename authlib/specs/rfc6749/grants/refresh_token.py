"""
    authlib.specs.rfc6749.grants.refresh_token
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A special grant endpoint for refresh_token grant_type. Refreshing an
    Access Token per `Section 6`_.

    .. _`Section 6`: https://tools.ietf.org/html/rfc6749#section-6

    :copyright: (c) 2017 by Hsiaoming Yang.
    :license: LGPLv3, see LICENSE for more details.
"""

from .base import BaseGrant
from ..errors import (
    InvalidRequestError,
    UnauthorizedClientError,
    InvalidClientError,
)


class RefreshTokenGrant(BaseGrant):
    GRANT_TYPE = 'refresh_token'

    def __init__(self, uri, params, headers, client_model, token_generator):
        super(RefreshTokenGrant, self).__init__(
            uri, params, headers, client_model, token_generator)
        self._authenticated_client = None
        self._authenticated_token = None

    @staticmethod
    def check_token_endpoint(params):
        return params.get('grant_type') == RefreshTokenGrant.GRANT_TYPE

    def validate_access_token_request(self):
        """If the authorization server issued a refresh token to the client, the
        client makes a refresh request to the token endpoint by adding the
        following parameters using the "application/x-www-form-urlencoded"
        format per Appendix B with a character encoding of UTF-8 in the HTTP
        request entity-body, per Section 6:

        grant_type
             REQUIRED.  Value MUST be set to "refresh_token".

        refresh_token
             REQUIRED.  The refresh token issued to the client.

        scope
             OPTIONAL.  The scope of the access request as described by
             Section 3.3.  The requested scope MUST NOT include any scope
             not originally granted by the resource owner, and if omitted is
             treated as equal to the scope originally granted by the
             resource owner.


        For example, the client makes the following HTTP request using
        transport-layer security (with extra line breaks for display purposes
        only):

        .. code-block:: http

            POST /token HTTP/1.1
            Host: server.example.com
            Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
            Content-Type: application/x-www-form-urlencoded

            grant_type=refresh_token&refresh_token=tGzv3JOkF0XG5Qx2TlKWIA
        """

        # require client authentication for confidential clients or for any
        # client that was issued client credentials (or with other
        # authentication requirements)
        client = self.authenticate_client()
        self._authenticated_client = client

        refresh_token = self.params.get('refresh_token')
        if refresh_token is None:
            raise InvalidRequestError(
                'Missing "refresh_token" in request.',
                uri=self.uri,
            )
        scope = self.params.get('scope')
        token = self.authenticate_token(refresh_token, scope)
        self._authenticated_token = token

    def create_access_token_response(self):
        """If valid and authorized, the authorization server issues an access
        token as described in Section 5.1.  If the request failed
        verification or is invalid, the authorization server returns an error
        response as described in Section 5.2.
        """
        token = self.token_generator(
            self._authenticated_client, self.GRANT_TYPE,
            expires_in=self._authenticated_token.expires_in,
            scope=self.params.get('scope'),
        )
        self.create_access_token(token, self._authenticated_token)
        return 200, token, self.TOKEN_RESPONSE_HEADER

    def authenticate_client(self):
        client_params = self.parse_basic_auth_header()
        if not client_params:
            raise UnauthorizedClientError(uri=self.uri)

        client_id, client_secret = client_params
        client = self.get_and_validate_client(client_id)

        if not client.check_grant_type(self.GRANT_TYPE):
            raise UnauthorizedClientError(uri=self.uri)

        # authenticate the client if client authentication is included
        if client_secret != client.client_secret:
            raise InvalidClientError(uri=self.uri)

        return client

    def authenticate_token(self, refresh_token, scope=None):
        """
        :param refresh_token: The refresh token issued to the client
        :param scope:  The scope of the access request
        :return: token
        """
        raise NotImplementedError()

    def create_access_token(self, token, access_token):
        """
        :param token: A new generated token to replace the original token.
        :param access_token: The original token granted by resource owner.
        """
        raise NotImplementedError()
