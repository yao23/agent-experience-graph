"""Dependency-free extract of Scrapy's Python 3 CookieJar request adapter."""

from urllib.parse import urlparse


class Request:
    def __init__(self, url, meta=None, headers=None):
        self.url = url
        self.meta = meta or {}
        self.headers = headers or {}


class WrappedRequest:
    def __init__(self, request):
        self.request = request

    def get_full_url(self):
        return self.request.url

    def get_host(self):
        return urlparse(self.request.url).netloc

    def get_type(self):
        return urlparse(self.request.url).scheme

    def is_unverifiable(self):
        return self.request.meta.get("is_unverifiable", False)

    @property
    def unverifiable(self):
        return self.is_unverifiable()

    def get_origin_req_host(self):
        return urlparse(self.request.url).hostname

    def has_header(self, name):
        return name in self.request.headers
