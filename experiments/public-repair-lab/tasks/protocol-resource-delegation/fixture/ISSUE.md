# Keepalive control fails after stream ownership migration

`Channel.set_keepalive()` is a public control, but it still reaches for a
direct socket reference that no longer exists. The active stream is owned by
the channel's protocol object.

Make the smallest production-code change that passes `python3 test_bug.py`.
Preserve the abstraction boundary and do not weaken or edit the test.
