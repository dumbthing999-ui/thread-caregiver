from urllib.parse import parse_qs, urlencode, urlparse
from app.hosted import HostedHandler


class handler(HostedHandler):
    def _handle(self, write):
        # Vercel rewrites the request path; carry the original route explicitly.
        query = parse_qs(urlparse(self.path).query, keep_blank_values=True)
        route = query.pop('__thread_path', [''])[0]
        self.path = '/' + route.lstrip('/')
        if query:
            self.path += '?' + urlencode(query, doseq=True)
        return super()._handle(write)
