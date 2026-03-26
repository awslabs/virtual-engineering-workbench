from enum import IntEnum, StrEnum

from pydantic import BaseModel, Field


class ConnectionOption(StrEnum):
    """
    Available connection options.
    """

    ADB = "ADB"
    BROWSER_IDE = "Browser IDE"
    NICE_DCV = "NICE DCV"
    QUIC = "QUIC"
    RDP = "RDP"
    SSH = "SSH"
    WEBRTC = "WebRTC"

    @staticmethod
    def list():
        return list(map(lambda p: p.value, ConnectionOption))


class Port(IntEnum):
    ADB = 6520
    BROWSER_IDE = 9443
    NICE_DCV = 8443
    QUIC = 8444
    RDP = 3389
    SSH = 22
    WEBRTC_STREAMING_START = 15550
    WEBRTC_STREAMING_END = 15599


class Protocol(StrEnum):
    TCP = "tcp"
    UDP = "udp"


class SecurityGroupRule(BaseModel):
    from_port: int = Field(..., title="from_port")
    to_port: int = Field(..., title="to_port")
    protocol: Protocol = Field(..., title="protocol")

    @property
    def port(self) -> int:
        return self.from_port


def _single_port_rule(port: Port, protocol: Protocol) -> SecurityGroupRule:
    return SecurityGroupRule(from_port=port.value, to_port=port.value, protocol=protocol)


def _range_rule(from_port: Port, to_port: Port, protocol: Protocol) -> SecurityGroupRule:
    return SecurityGroupRule(from_port=from_port.value, to_port=to_port.value, protocol=protocol)


CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP = {
    ConnectionOption.ADB: [
        _single_port_rule(Port.ADB, Protocol.TCP),
    ],
    ConnectionOption.BROWSER_IDE: [
        _single_port_rule(Port.BROWSER_IDE, Protocol.TCP),
    ],
    ConnectionOption.NICE_DCV: [
        _single_port_rule(Port.NICE_DCV, Protocol.TCP),
    ],
    ConnectionOption.QUIC: [
        _single_port_rule(Port.QUIC, Protocol.UDP),
    ],
    ConnectionOption.RDP: [
        _single_port_rule(Port.RDP, Protocol.TCP),
    ],
    ConnectionOption.SSH: [
        _single_port_rule(Port.SSH, Protocol.TCP),
    ],
    ConnectionOption.WEBRTC: [
        _range_rule(Port.WEBRTC_STREAMING_START, Port.WEBRTC_STREAMING_END, Protocol.TCP),
        _range_rule(Port.WEBRTC_STREAMING_START, Port.WEBRTC_STREAMING_END, Protocol.UDP),
    ],
}
