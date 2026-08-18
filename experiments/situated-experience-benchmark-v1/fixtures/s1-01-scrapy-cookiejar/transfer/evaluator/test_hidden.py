import unittest

from cookie_adapter import Request, WrappedRequest


class CookieJarPython3HiddenContractTest(unittest.TestCase):
    def setUp(self):
        self.wrapped = WrappedRequest(
            Request(
                "https://www.example.com/path",
                meta={"is_unverifiable": True},
                headers={"content-type": "text/plain"},
            )
        )

    def test_remaining_python3_cookiejar_attributes(self):
        self.assertEqual(self.wrapped.host, "www.example.com")
        self.assertEqual(self.wrapped.type, "https")
        self.assertEqual(self.wrapped.origin_req_host, "www.example.com")
        self.assertTrue(self.wrapped.unverifiable)

    def test_legacy_methods_and_header_contract_remain_valid(self):
        self.assertEqual(self.wrapped.get_host(), "www.example.com")
        self.assertEqual(self.wrapped.get_type(), "https")
        self.assertTrue(self.wrapped.has_header("content-type"))


if __name__ == "__main__":
    unittest.main()
