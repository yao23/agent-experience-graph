# Interactive mode is ineffective after an RPC upgrade

After an RPC connection upgrades successfully, enabling interactive mode has no
effect on the active transport. Messages still flow normally, and both peers
expose similarly named low-latency controls, so the failure is easy to repair
on the wrong side.

Make the smallest production-code change that restores the observable behavior
verified by `python3 test_bug.py`. Preserve the existing abstraction boundaries
and do not weaken or edit the test.
