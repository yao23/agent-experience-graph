# Source and license

- Fixture source: AEG dependency-free transfer task
- Repository license: MIT No Attribution
- Related verified public source: https://github.com/tornadoweb/tornado
- Related buggy commit: `6a5a0bfa370b6c0d3dbbf9589a560a98202d2baa`
- Related fixed commit: `4677c54cc18bbfbdf0f4dadf11610fab6203fd63`
- Related upstream license: Apache-2.0
- Verified experience: `trace-2026-08-03-tr-04-tornado-nodelay`

This is a synthetic transfer task, not copied upstream code. It preserves the
same three-layer ownership shape while changing the domain from WebSocket
TCP_NODELAY to channel keepalive. The golden repair is not included in either
agent workspace.
