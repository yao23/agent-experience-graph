import unittest

from cookie_adapter import Request, WrappedRequest


class CookieJarPython3ContractTest(unittest.TestCase):
    def test_python3_cookiejar_reads_full_url_as_attribute(self):
        wrapped = WrappedRequest(Request("https://www.example.com/path"))
        self.assertEqual(wrapped.full_url, "https://www.example.com/path")


if __name__ == "__main__":
    unittest.main()
