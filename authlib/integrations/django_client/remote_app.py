from django.dispatch import Signal
from django.http import HttpResponseRedirect
from .._client import RemoteApp as _RemoteApp

__all__ = ['token_update', 'RemoteApp']


token_update = Signal(providing_args=['name', 'token', 'refresh_token', 'access_token'])


class RemoteApp(_RemoteApp):
    """A RemoteApp for Django framework."""
    def _send_token_update(self, token, refresh_token=None, access_token=None):
        super(RemoteApp, self)._send_token_update(
            token, refresh_token, access_token
        )

        token_update.send(
            sender=self.__class__,
            name=self.name,
            token=token,
            refresh_token=refresh_token,
            access_token=access_token,
        )

    def _generate_access_token_params(self, request):
        if self.request_token_url:
            return request.GET.dict()

        if request.method == 'GET':
            params = {
                'code': request.GET.get('code'),
                'state': request.GET.get('state'),
            }
        else:
            params = {
                'code': request.POST.get('code'),
                'state': request.POST.get('state'),
            }
        return params

    def authorize_redirect(self, request, redirect_uri=None, **kwargs):
        """Create a HTTP Redirect for Authorization Endpoint.

        :param request: HTTP request instance from Django view.
        :param redirect_uri: Callback or redirect URI for authorization.
        :param kwargs: Extra parameters to include.
        :return: A HTTP redirect response.
        """
        uri, state = self.create_authorization_url(
            redirect_uri, self.save_temporary_data(request), **kwargs)
        self.save_authorize_state(request, redirect_uri, state)
        return HttpResponseRedirect(uri)

    def authorize_access_token(self, request, **kwargs):
        """Fetch access token in one step.

        :param request: HTTP request instance from Django view.
        :return: A token dict.
        """
        params = self.retrieve_temporary_data(request)
        params.update(kwargs)
        return self.fetch_access_token(**params)
