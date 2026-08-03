import unittest

from channel import Channel, TcpChannelProtocol


class RecordingStream:
    def __init__(self):
        self.keepalive_calls = []

    def set_keepalive(self, enabled):
        self.keepalive_calls.append(enabled)

    def send(self, payload):
        pass


class KeepaliveDelegationTest(unittest.TestCase):
    def test_public_control_delegates_through_protocol(self):
        stream = RecordingStream()
        channel = Channel(TcpChannelProtocol(stream))

        channel.set_keepalive(True)

        self.assertEqual(stream.keepalive_calls, [True])


if __name__ == "__main__":
    unittest.main()
