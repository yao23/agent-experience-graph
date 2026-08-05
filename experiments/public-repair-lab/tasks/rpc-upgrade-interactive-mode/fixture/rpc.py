from abc import ABC, abstractmethod


class RpcClientConnection:
    """Client-side connection retained for outbound RPC controls."""

    def __init__(self, protocol):
        self.protocol = protocol

    def set_interactive(self, enabled):
        # Interactive mode used to be applied here before the upgrade split.
        self._interactive = enabled


class UpgradeProtocol(ABC):
    @abstractmethod
    def send_frame(self, payload):
        raise NotImplementedError


class FramedUpgradeProtocol(UpgradeProtocol):
    def __init__(self, stream):
        self.stream = stream

    def send_frame(self, payload):
        self.stream.send(payload)


class _UpgradeHandler:
    """Server-side owner of an accepted upgraded connection."""

    def __init__(self, connection):
        self.connection = connection
        self.stream = None

    def set_interactive(self, enabled):
        if self.stream is not None:
            self.stream.set_interactive(enabled)


class RpcGateway:
    def __init__(self, protocol):
        self._handler = _UpgradeHandler(protocol)

    def enable_interactive_mode(self):
        self._handler.set_interactive(True)
