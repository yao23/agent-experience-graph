import unittest

from rpc import FramedUpgradeProtocol, RpcGateway


class RecordingStream:
    def __init__(self):
        self.interactive_calls = []

    def set_interactive(self, enabled):
        self.interactive_calls.append(enabled)

    def send(self, payload):
        pass


class InteractiveUpgradeTest(unittest.TestCase):
    def test_gateway_control_reaches_active_upgraded_stream(self):
        stream = RecordingStream()
        gateway = RpcGateway(FramedUpgradeProtocol(stream))

        gateway.enable_interactive_mode()

        self.assertEqual(stream.interactive_calls, [True])


if __name__ == "__main__":
    unittest.main()
