"""Dependency-free extract of Scrapy's pre-fix CookieJar adapter boundary."""


def to_native_str(value, encoding="utf-8", errors="strict"):
    if isinstance(value, bytes):
        return value.decode(encoding, errors)
    return str(value)


class Headers:
    def __init__(self, values):
        self._values = values

    def get(self, name, default=None):
        values = self._values.get(name)
        return values[0] if values else default

    def getlist(self, name):
        return self._values.get(name, [])

    def items(self):
        return self._values.items()


class WrappedRequest:
    def __init__(self, headers):
        self.headers = headers

    def get_header(self, name, default=None):
        return to_native_str(self.headers.get(name, default))

    def header_items(self):
        return [
            (to_native_str(key), [to_native_str(value) for value in values])
            for key, values in self.headers.items()
        ]


class WrappedResponse:
    def __init__(self, headers):
        self.headers = headers

    def get_all(self, name, default=None):
        return [to_native_str(value) for value in self.headers.getlist(name)]
