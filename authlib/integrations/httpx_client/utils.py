from httpx import URL


HTTPX_CLIENT_KWARGS = [
    'headers', 'cookies', 'verify', 'cert', 'http_versions',
    'proxies', 'timeout', 'pool_limits', 'max_redirects',
    'base_url', 'dispatch', 'app', 'backend', 'trust_env',
]


def extract_client_kwargs(kwargs):
    client_kwargs = {}
    for k in HTTPX_CLIENT_KWARGS:
        if k in kwargs:
            client_kwargs[k] = kwargs.pop(k)
    return client_kwargs


async def auth_call(self, request, get_response, has_method=True):
    content = await request.read()

    if has_method:
        url, headers, body = self.prepare(
            request.method, str(request.url), request.headers, content)
    else:
        url, headers, body = self.prepare(
            str(request.url), request.headers, content)

    request.url = URL(url)
    request.headers.update(headers)
    if body:
        body = body.encode('utf-8')
        if body != content:
            request.is_streaming = False
            request.content = body
    return await get_response(request)
