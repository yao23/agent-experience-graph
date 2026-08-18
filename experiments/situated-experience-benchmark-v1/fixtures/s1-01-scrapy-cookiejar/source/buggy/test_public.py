import unittest

from cookie_adapter import Headers, WrappedResponse


class SourceMigrationTest(unittest.TestCase):
    def test_non_utf8_cookie_header_does_not_abort_parsing(self):
        wrapped = WrappedResponse(Headers({"Set-Cookie": [b"C1=in\xa3valid; path=/"]}))
        self.assertEqual(wrapped.get_all("Set-Cookie"), ["C1=in�valid; path=/"])


if __name__ == "__main__":
    unittest.main()
