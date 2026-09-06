#!/usr/bin/env bash
set -euo pipefail

readonly SOURCE_REVISION="999efa64e9ba016efc9d3327df4b70e1fc79b804"
readonly SOURCE_REF="refs/heads/main"
readonly SOURCE_REPOSITORY="https://github.com/yao23/agent-experience-graph"
readonly ORIGINAL_NON_MAINLINE_COMMIT="4f1d26e80a4fba7460cfb2523905fb08619bd08d"
readonly IMAGE_TAG="aeg-runtime-canary:${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
readonly CONTROL_ROOT="${GITHUB_WORKSPACE}/control"
readonly SOURCE_ROOT="${GITHUB_WORKSPACE}/source"
readonly CANARY_ROOT="${RUNNER_TEMP}/aeg-runtime-canary-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
readonly OUTPUT_ROOT="${CANARY_ROOT}/output"
readonly SENTINEL_PATH="${CANARY_ROOT}/outside-sentinel.txt"
readonly CONTAINER_NAME="aeg-runtime-canary-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"

cleanup() {
  docker rm --force "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker image rm --force "${IMAGE_TAG}" >/dev/null 2>&1 || true
  rm -rf "${CANARY_ROOT}"
}
trap cleanup EXIT

mkdir -p "${OUTPUT_ROOT}"
printf '%s\n' 'synthetic-boundary-sentinel' >"${SENTINEL_PATH}"

test "$(git -C "${SOURCE_ROOT}" rev-parse HEAD)" = "${SOURCE_REVISION}"
git -C "${SOURCE_ROOT}" cat-file -e 'f985424fed493c52f9686bdd3feff33f28b2d400^{commit}'
git -C "${SOURCE_ROOT}" cat-file -e 'ee6ed853c1c8e93541d0b38ac5e46b4bdd9146c1^{commit}'
if git -C "${SOURCE_ROOT}" cat-file -e "${ORIGINAL_NON_MAINLINE_COMMIT}^{commit}" 2>/dev/null; then
  echo "original non-mainline commit was unexpectedly acquired" >&2
  exit 2
fi
if git -C "${SOURCE_ROOT}" config --get-regexp 'http\..*extraheader|credential\..*helper' >/dev/null 2>&1; then
  echo "checkout retained a credential-bearing Git configuration" >&2
  exit 2
fi

echo "DEPENDENCY_NETWORK_PHASE: build digest-pinned local image"
docker build --pull --no-cache --tag "${IMAGE_TAG}" "${CONTROL_ROOT}/runtime-canary"
echo "DEPENDENCY_NETWORK_PHASE_COMPLETE"

readonly RUNTIME_UID="$(id -u)"
readonly RUNTIME_GID="$(id -g)"
docker create \
  --name "${CONTAINER_NAME}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  --mount "type=bind,src=${CONTROL_ROOT}/runtime-canary,dst=/control,readonly" \
  --mount "type=bind,src=${SOURCE_ROOT},dst=/source,readonly" \
  --mount "type=bind,src=${OUTPUT_ROOT},dst=/work" \
  --user "${RUNTIME_UID}:${RUNTIME_GID}" \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 128 \
  --memory 1g \
  --cpus 2 \
  --entrypoint /usr/bin/env \
  "${IMAGE_TAG}" \
  -i \
  HOME=/tmp/aeg-home \
  PATH=/usr/local/bin:/usr/bin:/bin \
  PYTHONCOERCECLOCALE=0 \
  PYTHONDONTWRITEBYTECODE=1 \
  "CANARY_RUN_ID=${GITHUB_RUN_ID}" \
  "CONTROL_REVISION=${GITHUB_SHA}" \
  "RUNNER_ARCHITECTURE=${RUNNER_ARCH}" \
  "SENTINEL_PATH=${SENTINEL_PATH}" \
  "SOURCE_REF=${SOURCE_REF}" \
  "SOURCE_REPOSITORY=${SOURCE_REPOSITORY}" \
  "SOURCE_REVISION=${SOURCE_REVISION}" \
  python3 /control/run_canary.py

docker inspect "${CONTAINER_NAME}" >"${OUTPUT_ROOT}/container-inspect.json"
python3 "${CONTROL_ROOT}/runtime-canary/verify_container.py" \
  "${OUTPUT_ROOT}/container-inspect.json" \
  "${OUTPUT_ROOT}/container-policy.json"

set +e
timeout --signal=TERM --kill-after=30s 12m docker start --attach "${CONTAINER_NAME}"
readonly CANARY_EXIT=$?
set -e

readonly CONTAINER_EXIT="$(docker inspect --format '{{.State.ExitCode}}' "${CONTAINER_NAME}")"
test -f "${OUTPUT_ROOT}/canary-result.json"

echo "CONTAINER_POLICY_RESULT"
python3 -m json.tool "${OUTPUT_ROOT}/container-policy.json"
echo "CANARY_STRUCTURED_RESULT"
python3 -m json.tool "${OUTPUT_ROOT}/canary-result.json"
echo "container_exit_code=${CONTAINER_EXIT} outer_exit_code=${CANARY_EXIT}"

docker rm --force "${CONTAINER_NAME}" >/dev/null
if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  echo "container still exists after cleanup" >&2
  exit 2
fi
docker image rm --force "${IMAGE_TAG}" >/dev/null
if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
  echo "local canary image still exists after cleanup" >&2
  exit 2
fi
rm -f "${SENTINEL_PATH}"
test ! -e "${SENTINEL_PATH}"

{
  echo "## AEG runtime canary"
  echo
  echo "- Source: \`${SOURCE_REPOSITORY}@${SOURCE_REVISION}\`"
  echo "- Runner: \`ubuntu-24.04-arm\` (standard GitHub-hosted VM)"
  echo "- Container exit: \`${CONTAINER_EXIT}\`"
  echo "- Outer timeout exit: \`${CANARY_EXIT}\`"
  echo "- Container, local image, and synthetic sentinel removed before job exit"
  echo "- Full structured evidence is retained in this job log; no artifact or cache was created"
} >>"${GITHUB_STEP_SUMMARY}"

rm -rf "${CANARY_ROOT}"
test ! -e "${CANARY_ROOT}"
echo 'CLEANUP_RESULT {"container_removed":true,"image_removed":true,"synthetic_sentinel_removed":true,"temporary_root_removed":true}'

test "${CANARY_EXIT}" -eq "${CONTAINER_EXIT}"
exit "${CANARY_EXIT}"
