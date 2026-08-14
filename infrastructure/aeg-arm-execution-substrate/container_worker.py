#!/usr/bin/env python3
"""Trusted in-container worker for the AEG arm execution substrate."""

import argparse
import base64
import binascii
import difflib
import hashlib
import io
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath


ROOT = Path("/workspace")
TASK = ROOT / "task"
ARM = ROOT / "arm.json"
ALLOWED_ENV = {
    "HOME": "/nonexistent",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
PROTECTED_NAMES = {"ISSUE.md", "arm.json", "human.patch", "test_hidden.py"}
MAX_WORKER_OUTPUT = 262144
BASELINE = Path("/tmp/aeg-baseline")


class WorkerError(RuntimeError):
    pass


def emit(value):
    rendered = json.dumps(value, sort_keys=True)
    if len(rendered.encode()) > MAX_WORKER_OUTPUT:
        raise WorkerError("worker output exceeds limit")
    print(rendered)


def load_arm():
    with ARM.open(encoding="utf-8") as handle:
        return json.load(handle)


def import_bundle(encoded, max_bytes):
    try:
        archive_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise WorkerError("container bundle encoding is invalid") from None
    if ROOT.exists() and any(ROOT.iterdir()):
        raise WorkerError("workspace is not empty before bundle import")
    ROOT.mkdir(parents=True, exist_ok=True)
    seen = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise WorkerError("container bundle path is invalid")
            if relative.parts[0] not in {"arm.json", "task"}:
                raise WorkerError("container bundle has an unexpected top-level entry")
            if relative.parts[0] == "arm.json" and len(relative.parts) != 1:
                raise WorkerError("arm envelope path is invalid")
            if member.name in seen or member.issym() or member.islnk() or member.isdev():
                raise WorkerError("container bundle entry type is prohibited")
            if not member.isdir() and not member.isfile():
                raise WorkerError("container bundle entry is not regular")
            seen.add(member.name)
            total += member.size if member.isfile() else 0
            if total > max_bytes:
                raise WorkerError("container bundle exceeds workspace limit")
            destination = ROOT.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True, mode=0o755)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            source = archive.extractfile(member)
            if source is None:
                raise WorkerError("container bundle file has no payload")
            with destination.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            destination.chmod(0o644)
    if {path.name for path in ROOT.iterdir()} != {"arm.json", "task"} or not ARM.is_file() or not TASK.is_dir():
        raise WorkerError("container bundle entries differ from the allowlist")
    return {"files": sum(1 for path in TASK.rglob("*") if path.is_file()), "bytes": total}


def relative_path(value, allow_directory=False):
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or ".git" in candidate.parts:
        raise WorkerError("path is outside the task allowlist")
    task_root = TASK.resolve(strict=True)
    target = task_root / candidate
    try:
        resolved = target.resolve(strict=True)
    except (FileNotFoundError, RuntimeError):
        raise WorkerError("path does not exist") from None
    if resolved != task_root and task_root not in resolved.parents:
        raise WorkerError("path escapes the task workspace")
    current = task_root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise WorkerError("symlink paths are prohibited")
    if resolved.is_dir() and not allow_directory:
        raise WorkerError("path is not a regular file")
    return resolved


def protected(path):
    relative = path.resolve(strict=True).relative_to(TASK.resolve(strict=True)).as_posix()
    name = Path(relative).name
    return name in PROTECTED_NAMES or name.startswith("test") or "/test" in relative


def inspect_path(value, limit):
    target = relative_path(value, allow_directory=True)
    if target.is_dir():
        entries = []
        for child in sorted(target.iterdir(), key=lambda item: item.name):
            if child.name == ".git" or child.is_symlink():
                continue
            entries.append({"name": child.name, "type": "directory" if child.is_dir() else "file"})
        return {"path": target.relative_to(TASK.resolve()).as_posix() or ".", "entries": entries}
    if target.stat().st_size > limit:
        raise WorkerError("file exceeds inspection limit")
    return {
        "path": target.relative_to(TASK.resolve()).as_posix(),
        "content": target.read_text(encoding="utf-8", errors="replace"),
    }


def run_registered(argv, timeout):
    arm = load_arm()
    registered = shlex.split(arm["public_test_command"])
    if argv not in (registered, ["python3", "--version"]):
        raise WorkerError("command is not allowlisted")
    result = subprocess.run(
        argv,
        cwd=TASK,
        env=dict(ALLOWED_ENV),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return {
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout[-65536:],
        "stderr": result.stderr[-65536:],
    }


def normalize_patch_path(header, prefix):
    value = header.split("\t", 1)[0].strip()
    if not value.startswith(prefix):
        raise WorkerError("patch header prefix is invalid")
    relative = value[len(prefix):]
    path = relative_path(relative)
    if protected(path):
        raise WorkerError("patch targets a protected input")
    return path


def apply_hunks(original, hunks):
    source = original.splitlines()
    trailing_newline = original.endswith("\n")
    output = []
    cursor = 0
    for old_start, lines in hunks:
        start = max(old_start - 1, 0)
        if start < cursor:
            raise WorkerError("patch hunks overlap")
        output.extend(source[cursor:start])
        cursor = start
        for line in lines:
            if not line:
                raise WorkerError("patch hunk line is empty")
            marker, value = line[0], line[1:]
            if marker == " ":
                if cursor >= len(source) or source[cursor] != value:
                    raise WorkerError("patch context does not match")
                output.append(source[cursor])
                cursor += 1
            elif marker == "-":
                if cursor >= len(source) or source[cursor] != value:
                    raise WorkerError("patch deletion does not match")
                cursor += 1
            elif marker == "+":
                output.append(value)
            elif marker == "\\":
                continue
            else:
                raise WorkerError("patch hunk marker is invalid")
    output.extend(source[cursor:])
    rendered = "\n".join(output)
    if trailing_newline:
        rendered += "\n"
    return rendered


def parse_and_apply_patch(patch_text, max_bytes):
    if not patch_text or len(patch_text.encode()) > max_bytes:
        raise WorkerError("patch is empty or exceeds limit")
    lines = patch_text.splitlines()
    index = 0
    changes = []
    changed_paths = set()
    while index < len(lines):
        if lines[index].startswith("diff --git "):
            index += 1
            if index < len(lines) and lines[index].startswith("index "):
                index += 1
            continue
        if not lines[index].startswith("--- "):
            raise WorkerError("only unified file patches are supported")
        old_path = normalize_patch_path(lines[index][4:], "a/")
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise WorkerError("patch is missing new-file header")
        new_path = normalize_patch_path(lines[index][4:], "b/")
        if old_path != new_path:
            raise WorkerError("renames and file creation are prohibited")
        if old_path in changed_paths:
            raise WorkerError("a file may appear only once per patch")
        changed_paths.add(old_path)
        index += 1
        hunks = []
        while index < len(lines) and not lines[index].startswith(("--- ", "diff --git ")):
            header = lines[index]
            if not header.startswith("@@ "):
                raise WorkerError("patch is missing hunk header")
            try:
                old_field = header.split("@@", 2)[1].strip().split()[0]
                old_start = int(old_field[1:].split(",", 1)[0])
            except (IndexError, ValueError):
                raise WorkerError("patch hunk header is invalid") from None
            index += 1
            hunk_lines = []
            while index < len(lines) and not lines[index].startswith(("@@ ", "--- ", "diff --git ")):
                hunk_lines.append(lines[index])
                index += 1
            hunks.append((old_start, hunk_lines))
        original = old_path.read_text(encoding="utf-8")
        rendered = apply_hunks(original, hunks)
        changes.append((old_path, rendered))
    if not changes:
        raise WorkerError("patch contains no file changes")
    for path, rendered in changes:
        path.write_text(rendered, encoding="utf-8")
    return [path.relative_to(TASK.resolve()).as_posix() for path, _ in changes]


def workspace_snapshot():
    digest = hashlib.sha256()
    files = []
    total = 0
    for path in sorted(TASK.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.is_symlink():
            continue
        relative = path.relative_to(TASK).as_posix()
        data = path.read_bytes()
        total += len(data)
        files.append(relative)
        digest.update(relative.encode() + b"\0" + data)
    return {"sha256": digest.hexdigest(), "files": files, "bytes": total}


def workspace_files(root):
    values = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.is_symlink():
            raise WorkerError("workspace symlinks are prohibited")
        if path.is_file():
            values[relative.as_posix()] = path
    return values


def create_baseline():
    if BASELINE.exists():
        raise WorkerError("workspace baseline already exists")
    BASELINE.mkdir(mode=0o700)
    for relative, source in workspace_files(TASK).items():
        destination = BASELINE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return {"files": len(workspace_files(BASELINE)), "sha256": workspace_snapshot()["sha256"]}


def export_workspace_patch(max_bytes):
    if not BASELINE.is_dir():
        raise WorkerError("workspace baseline is unavailable")
    before = workspace_files(BASELINE)
    after = workspace_files(TASK)
    if set(before) != set(after):
        raise WorkerError("file creation and deletion are prohibited")
    changed = []
    diffs = []
    for relative in sorted(before):
        if before[relative].read_bytes() == after[relative].read_bytes():
            continue
        target = after[relative]
        if protected(target):
            raise WorkerError("repair changed a protected input")
        try:
            original = before[relative].read_text(encoding="utf-8")
            repaired = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise WorkerError("binary changes are prohibited") from None
        lines = difflib.unified_diff(
            original.splitlines(),
            repaired.splitlines(),
            fromfile=f"a/{relative}",
            tofile=f"b/{relative}",
            lineterm="",
        )
        rendered = "\n".join(lines) + "\n"
        changed.append(relative)
        diffs.append(rendered)
    patch = "".join(diffs)
    if len(patch.encode()) > max_bytes:
        raise WorkerError("exported patch exceeds limit")
    return {"patch": patch, "files_changed": changed}


def inaccessible(path_text):
    path = Path(path_text)
    try:
        if path.is_dir():
            next(path.iterdir(), None)
        else:
            path.read_bytes()
    except (OSError, PermissionError):
        return True
    return not path.exists()


def canary_probe(forbidden_paths):
    attempts = []

    def add(identifier, passed, reason):
        attempts.append({"id": identifier, "passed": bool(passed), "reason": reason})

    controller_paths = [path for path in forbidden_paths if "controller" in path or "github" in path]
    other_paths = [path for path in forbidden_paths if "other" in path]
    add("controller_files", all(inaccessible(path) for path in controller_paths), "controller paths are absent from the container namespace")
    secret_names = {name for name in os.environ if any(term in name.upper() for term in ("OPENAI", "API_KEY", "TOKEN", "SECRET", "PASSWORD", "ACTIONS_", "GITHUB_"))}
    add("api_key", not any("OPENAI" in name.upper() or "API_KEY" in name.upper() for name in secret_names), "no model credential name is present")
    add("github_token", not any("GITHUB" in name.upper() or "ACTIONS_" in name.upper() for name in secret_names), "no GitHub or Actions credential name is present")
    add("environment_allowlist", os.environ == ALLOWED_ENV, "tool subprocess environment equals the four-name allowlist")
    add("other_arm", all(inaccessible(path) for path in other_paths), "another synthetic arm is absent from the container namespace")
    add("docker_socket", not Path("/var/run/docker.sock").exists(), "Docker socket is not mounted")
    tcp_failed = False
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=1):
            pass
    except OSError:
        tcp_failed = True
    add("network_tcp", tcp_failed, "network namespace has no external route")
    dns_failed = False
    try:
        socket.getaddrinfo("example.com", 443)
    except OSError:
        dns_failed = True
    add("network_dns", dns_failed, "DNS is unavailable in the networkless container")
    add("hidden_tests", not any(path.name == "test_hidden.py" for path in ROOT.rglob("*")), "hidden tests are absent")
    add("human_patch", not any(path.name == "human.patch" for path in ROOT.rglob("*")), "human patches are absent")
    cache_targets = [Path("/root/.cache"), Path("/home/runner"), TASK / ".cache", TASK / "prior-transcript.jsonl"]
    add("prior_cache_or_transcript", all(inaccessible(str(path)) for path in cache_targets), "prior cache and transcript locations are absent")
    conversation_targets = [TASK / "prior-model-conversation.json", TASK / ".conversation", Path("/tmp/prior-model-conversation.json")]
    add("prior_model_conversation", all(inaccessible(str(path)) for path in conversation_targets), "prior model conversation state is absent")
    symlink = TASK / "canary-controller-link"
    try:
        symlink.symlink_to("/github/workspace/controller-sentinel")
        symlink_failed = inaccessible(str(symlink))
    finally:
        try:
            symlink.unlink()
        except OSError:
            pass
    add("symlink_escape", symlink_failed, "absolute symlink resolves only inside the container namespace")
    add("absolute_path_escape", inaccessible("/github/workspace/controller-sentinel"), "host absolute paths are absent")
    add("proc_escape", inaccessible("/proc/1/root/github/workspace/controller-sentinel"), "PID 1 root is the container root, not the host")
    child = subprocess.run(
        ["/usr/bin/env"],
        env=dict(ALLOWED_ENV),
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    child_names = {line.split("=", 1)[0] for line in child.stdout.splitlines() if "=" in line}
    add("subprocess_inheritance", child_names == set(ALLOWED_ENV), "child processes inherit only the explicit allowlist")
    return attempts


def stress_pids(count):
    children = []
    blocked = False
    try:
        for _ in range(count):
            try:
                children.append(subprocess.Popen(["python3", "-c", "import time; time.sleep(10)"], env=dict(ALLOWED_ENV)))
            except OSError:
                blocked = True
                break
    finally:
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return {"requested": count, "started": len(children), "blocked": blocked}


def stress_disk(byte_count):
    target = TASK / "canary-disk-fill"
    written = 0
    blocked = False
    try:
        with target.open("wb") as handle:
            chunk = b"0" * 1048576
            while written < byte_count:
                amount = min(len(chunk), byte_count - written)
                handle.write(chunk[:amount])
                handle.flush()
                written += amount
            os.fsync(handle.fileno())
    except OSError:
        blocked = True
    finally:
        target.unlink(missing_ok=True)
    return {"requested": byte_count, "written": written, "blocked": blocked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("hold")
    bundle = sub.add_parser("import-bundle")
    bundle.add_argument("--max-bytes", required=True, type=int)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--path", required=True)
    inspect.add_argument("--limit", required=True, type=int)
    command = sub.add_parser("run")
    command.add_argument("--argv-json", required=True)
    command.add_argument("--timeout", required=True, type=int)
    visible = sub.add_parser("visible-test")
    visible.add_argument("--timeout", required=True, type=int)
    patch = sub.add_parser("apply-patch")
    patch.add_argument("--max-bytes", required=True, type=int)
    sub.add_parser("snapshot")
    sub.add_parser("baseline-create")
    export = sub.add_parser("export-patch")
    export.add_argument("--max-bytes", required=True, type=int)
    canary = sub.add_parser("canary-probe")
    canary.add_argument("--forbidden-json", required=True)
    pids = sub.add_parser("stress-pids")
    pids.add_argument("--count", type=int, required=True)
    memory = sub.add_parser("stress-memory")
    memory.add_argument("--bytes", type=int, required=True)
    disk = sub.add_parser("stress-disk")
    disk.add_argument("--bytes", type=int, required=True)
    sleeper = sub.add_parser("sleep")
    sleeper.add_argument("--seconds", type=float, required=True)
    args = parser.parse_args()

    if args.action == "hold":
        while True:
            time.sleep(60)
    if args.action == "import-bundle":
        result = import_bundle(sys.stdin.read(), args.max_bytes)
    elif args.action == "inspect":
        result = inspect_path(args.path, args.limit)
    elif args.action == "run":
        argv = json.loads(args.argv_json)
        if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
            raise WorkerError("command must be a string array")
        result = run_registered(argv, args.timeout)
    elif args.action == "visible-test":
        result = run_registered(shlex.split(load_arm()["public_test_command"]), args.timeout)
    elif args.action == "apply-patch":
        result = {"files_changed": parse_and_apply_patch(sys.stdin.read(), args.max_bytes)}
    elif args.action == "snapshot":
        result = workspace_snapshot()
    elif args.action == "baseline-create":
        result = create_baseline()
    elif args.action == "export-patch":
        result = export_workspace_patch(args.max_bytes)
    elif args.action == "canary-probe":
        forbidden = json.loads(args.forbidden_json)
        result = {"attempts": canary_probe(forbidden)}
    elif args.action == "stress-pids":
        result = stress_pids(args.count)
    elif args.action == "stress-memory":
        value = bytearray(args.bytes)
        result = {"allocated": len(value)}
    elif args.action == "stress-disk":
        result = stress_disk(args.bytes)
    elif args.action == "sleep":
        time.sleep(args.seconds)
        result = {"slept": args.seconds}
    else:
        raise WorkerError("unknown action")
    emit(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (WorkerError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"container worker error: {error}", file=sys.stderr)
        raise SystemExit(2)
