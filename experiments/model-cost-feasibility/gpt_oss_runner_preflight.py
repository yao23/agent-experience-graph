#!/usr/bin/env python3
"""Measure runner capacity without downloading or running model or benchmark data."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


MODEL_DOWNLOAD_BYTES = 13_800_000_000
MIN_MEMORY_BYTES = 16_000_000_000
MIN_DISK_BYTES = MODEL_DOWNLOAD_BYTES * 2 + 2_000_000_000
PROBE_BYTES = 256 * 1024 * 1024


def command(*args):
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    return {"exitCode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def disk_probe(root):
    target = Path(root) / "aeg-gpt-oss-disk-probe.bin"
    chunk = b"\0" * (4 * 1024 * 1024)
    started = time.monotonic()
    with target.open("wb", buffering=0) as handle:
        for _ in range(PROBE_BYTES // len(chunk)):
            handle.write(chunk)
        os.fsync(handle.fileno())
    write_seconds = time.monotonic() - started
    started = time.monotonic()
    with target.open("rb", buffering=0) as handle:
        while handle.read(len(chunk)):
            pass
    read_seconds = time.monotonic() - started
    target.unlink()
    return {
        "probeBytes": PROBE_BYTES,
        "readBytesPerSecond": round(PROBE_BYTES / read_seconds),
        "readSeconds": round(read_seconds, 4),
        "writeBytesPerSecond": round(PROBE_BYTES / write_seconds),
        "writeSeconds": round(write_seconds, 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    disk = shutil.disk_usage(Path.cwd())
    xcode = command("xcode-select", "-p")
    metal = command("xcrun", "-f", "metal")
    throughput = disk_probe(tempfile.gettempdir())
    compatible = (
        platform.system() == "Darwin"
        and platform.machine() == "arm64"
        and tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 12)
        and xcode["exitCode"] == 0
        and metal["exitCode"] == 0
    )
    enough_memory = memory >= MIN_MEMORY_BYTES
    enough_disk = disk.free >= MIN_DISK_BYTES
    cold_load_floor = MODEL_DOWNLOAD_BYTES / throughput["readBytesPerSecond"]
    result = {
        "benchmarkDataAccessed": False,
        "modelDataDownloaded": False,
        "runner": {
            "system": platform.system(),
            "machine": platform.machine(),
            "release": platform.release(),
            "python": platform.python_version(),
            "memoryBytes": memory,
            "diskFreeBytes": disk.free,
            "xcodeSelect": xcode,
            "metalCompiler": metal,
            "diskProbe": throughput,
        },
        "gptOss20b": {
            "officialMinimumMemoryBytes": MIN_MEMORY_BYTES,
            "officialMetalDownloadBytes": MODEL_DOWNLOAD_BYTES,
            "requiredWorkingDiskBytes": MIN_DISK_BYTES,
            "runtimeCompatible": compatible,
            "enoughMemory": enough_memory,
            "enoughDisk": enough_disk,
            "estimatedColdLoadFloorSeconds": round(cold_load_floor, 2),
            "estimatedThirtyArmDownloadBytes": MODEL_DOWNLOAD_BYTES * 30,
            "estimatedThirtyArmColdLoadFloorSeconds": round(cold_load_floor * 30, 2),
            "initializationAndInferenceEstimate": "not measurable because the runner fails capacity gates; model download prohibited",
            "feasibleOnThisRunner": compatible and enough_memory and enough_disk,
        },
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
