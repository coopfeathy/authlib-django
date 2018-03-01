import logging
from .errors import InvalidClientError
from .util import extract_basic_authorization

log = logging.getLogger(__name__)


def authenticate_client_via_client_secret_basic(query_client, request):
    """Authenticate client by ``client_secret_basic`` method. The client
    uses HTTP Basic for authentication.
    """
    client_id, client_secret = extract_basic_authorization(request.headers)
    if client_id and client_secret:
        client = _validate_client(query_client, client_id, request.state)
        if client.check_token_endpoint_auth_method('client_secret_basic') \
                and client.check_client_secret(client_secret):
            log.debug(
                'Authenticate {} via "client_secret_basic" '
                'success'.format(client_id)
            )
            return client
    log.debug(
        'Authenticate {} via "client_secret_basic" '
        'failed'.format(client_id)
    )


def authenticate_client_via_client_secret_post(query_client, request):
    """Authenticate client by ``client_secret_post`` method. The client
    uses POST parameters for authentication.
    """
    data = dict(request.body_params)
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    if client_id and client_secret:
        client = _validate_client(query_client, client_id, request.state)
        if client.check_token_endpoint_auth_method('client_secret_post') \
                and client.check_client_secret(client_secret):
            log.debug(
                'Authenticate {} via "client_secret_post" '
                'success'.format(client_id)
            )
            return client
    log.debug(
        'Authenticate {} via "client_secret_post" '
        'failed'.format(client_id)
    )


def authenticate_client_via_none(query_client, request):
    """Authenticate public client by ``none`` method. The client
    does not have a client secret.
    """
    client_id = request.client_id
    if client_id and 'client_secret' not in request.data:
        client = _validate_client(query_client, client_id, request.state)
        if client.check_token_endpoint_auth_method('none') \
                and not client.has_client_secret():
            log.debug(
                'Authenticate {} via "none" '
                'success'.format(client_id)
            )
            return client
    log.debug(
        'Authenticate {} via "none" '
        'failed'.format(client_id)
    )


AUTHENTICATE_METHODS = {
    'none': authenticate_client_via_none,
    'client_secret_basic': authenticate_client_via_client_secret_basic,
    'client_secret_post': authenticate_client_via_client_secret_post,
}


def register_authenticate_method(name, func):
    """Extend authenticate client methods."""
    if name not in AUTHENTICATE_METHODS:
        AUTHENTICATE_METHODS[name] = func


def authenticate_client(query_client, request, methods):
    """Authenticate client with the given methods."""
    for method in methods:
        func = AUTHENTICATE_METHODS[method]
        client = func(query_client, request)
        if client:
            return client
    raise InvalidClientError(state=request.state)


def _validate_client(query_client, client_id, state=None):
    if client_id is None:
        raise InvalidClientError(state=state)

    client = query_client(client_id)
    if not client:
        raise InvalidClientError(state=state)

    return client
