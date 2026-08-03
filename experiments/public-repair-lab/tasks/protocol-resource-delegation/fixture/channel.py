from abc import ABC, abstractmethod


class Channel:
    def __init__(self, protocol):
        self.protocol = protocol
        self.socket = None

    def set_keepalive(self, enabled):
        assert self.socket is not None
        self.socket.set_keepalive(enabled)


class ChannelProtocol(ABC):
    @abstractmethod
    def send(self, payload):
        raise NotImplementedError


class TcpChannelProtocol(ChannelProtocol):
    def __init__(self, stream):
        self.stream = stream

    def send(self, payload):
        self.stream.send(payload)
