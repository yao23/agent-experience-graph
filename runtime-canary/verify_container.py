#!/usr/bin/env python3
"""Verify the Docker container configuration before the canary is started."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inspect_json", type=Path)
    parser.add_argument("output_json", type=Path)
    arguments = parser.parse_args()
    inspected = json.loads(arguments.inspect_json.read_text(encoding="utf-8"))[0]
    host = inspected["HostConfig"]
    config = inspected["Config"]
    mounts = {item["Destination"]: item["RW"] for item in inspected["Mounts"]}
    runtime_user = str(config.get("User", ""))
    tmpfs_options = (host.get("Tmpfs") or {}).get("/tmp", "")
    checks = {
        "capabilities_dropped": sorted(host.get("CapDrop") or []) == ["ALL"],
        "cpu_limited": host.get("NanoCpus") == 2000000000,
        "entry_environment_cleared": config.get("Entrypoint") == ["/usr/bin/env"]
        and (config.get("Cmd") or [None])[0] == "-i",
        "memory_limited": host.get("Memory") == 1073741824,
        "mounts_exact": mounts == {"/control": False, "/source": False, "/work": True},
        "network_disabled": host.get("NetworkMode") == "none",
        "no_device_passthrough": not host.get("Devices"),
        "no_new_privileges": "no-new-privileges" in (host.get("SecurityOpt") or []),
        "not_privileged": host.get("Privileged") is False,
        "pids_limited": host.get("PidsLimit") == 128,
        "read_only_root": host.get("ReadonlyRootfs") is True,
        "runtime_user_non_root": re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", runtime_user)
        is not None,
        "temporary_filesystem_bounded": all(
            option in tmpfs_options.split(",")
            for option in ("noexec", "nosuid", "nodev", "size=64m")
        ),
    }
    result = {
        "checks": checks,
        "mounts": [{"destination": key, "read_write": mounts[key]} for key in sorted(mounts)],
        "passed": all(checks.values()),
    }
    arguments.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
