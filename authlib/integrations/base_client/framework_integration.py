import json
import time


class FrameworkIntegration(object):
    expires_in = 3600

    def __init__(self, name, cache=None):
        self.name = name
        self.cache = cache

    def _get_cache_data(self, key):
        value = self.cache.get(key)
        if not value:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None

    def _clear_session_state(self, request):
        now = time.time()
        for key in dict(request.session):
            if '_authlib_' in key:
                # TODO: remove in future
                request.session.pop(key)
            elif key.startswith('_state_'):
                value = request.session[key]
                exp = value.get('exp')
                if not exp or exp < now:
                    request.session.pop(key)

    def get_state_data(self, request, state):
        key = f'_state_{self.name}_{state}'
        if self.cache:
            value = self._get_cache_data(key)
        else:
            value = request.session.get(key)
        if value:
            return value.get('data')
        return None

    def set_state_data(self, request, state, data):
        key = f'_state_{self.name}_{state}'
        if self.cache:
            self.cache.set(key, {'data': data}, self.expires_in)
        else:
            now = time.time()
            request.session[key] = {'data': data, 'exp': now + self.expires_in}

    def clear_state_data(self, request, state):
        key = f'_state_{self.name}_{state}'
        if self.cache:
            self.cache.delete(key)
        else:
            request.session.pop(key, None)
            self._clear_session_state(request)

    def update_token(self, token, refresh_token=None, access_token=None):
        raise NotImplementedError()

    @staticmethod
    def load_config(oauth, name, params):
        raise NotImplementedError()
