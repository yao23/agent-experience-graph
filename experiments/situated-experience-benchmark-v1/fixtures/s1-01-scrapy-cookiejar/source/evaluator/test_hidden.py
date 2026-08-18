import unittest

from cookie_adapter import Headers, WrappedRequest


class SourceMigrationHiddenTest(unittest.TestCase):
    def test_all_request_header_conversions_are_tolerant(self):
        wrapped = WrappedRequest(
            Headers({b"Other\xa3": [b"ignore\xa3me"], "Accept": [b"text/plain"]})
        )
        self.assertEqual(wrapped.get_header("Accept"), "text/plain")
        self.assertEqual(
            wrapped.header_items(),
            [("Other�", ["ignore�me"]), ("Accept", ["text/plain"])],
        )


if __name__ == "__main__":
    unittest.main()
