#!/usr/bin/env bash
# Build the exact arguments for `docker buildx imagetools create`.
# Two digest files must become two complete image@sha256 references.
# IMAGETOOLS_CAPTURE, when set, records those arguments and does not publish.
set -euo pipefail

: "${IMAGE:?IMAGE is required}"
digest_dir="${DIGEST_DIR:-.}"

if [[ ! -d "$digest_dir" ]]; then
  echo "digest directory does not exist: $digest_dir" >&2
  exit 1
fi

shopt -s nullglob
sources=()
for digest_file in "$digest_dir"/*; do
  if [[ ! -f "$digest_file" ]]; then
    continue
  fi
  digest_name="$(basename "$digest_file")"
  digest_name="${digest_name%$'\r'}"
  sources+=("${IMAGE}@sha256:${digest_name}")
done

if [[ "${#sources[@]}" -ne 2 ]]; then
  echo "expected 2 architecture digests, found ${#sources[@]}" >&2
  exit 1
fi

if [[ -z "${DOCKER_METADATA_OUTPUT_JSON:-}" ]]; then
  echo "DOCKER_METADATA_OUTPUT_JSON is required" >&2
  exit 1
fi

py=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import json' >/dev/null 2>&1; then
    py="$candidate"
    break
  fi
done
if [[ -z "$py" ]]; then
  echo "python is required to read image tags" >&2
  exit 1
fi

tags_file="$(mktemp)"
tags_err="$(mktemp)"
if ! "$py" -c 'import json, os
data = json.loads(os.environ["DOCKER_METADATA_OUTPUT_JSON"])
tags = data.get("tags") or []
if not isinstance(tags, list):
    raise SystemExit("metadata tags must be a list")
for tag in tags:
    print(tag)' >"$tags_file" 2>"$tags_err"; then
  echo "failed to read image tags from DOCKER_METADATA_OUTPUT_JSON" >&2
  cat "$tags_err" >&2
  rm -f "$tags_file" "$tags_err"
  exit 1
fi
rm -f "$tags_err"

tag_args=()
while IFS= read -r tag || [[ -n "$tag" ]]; do
  tag="${tag%$'\r'}"
  if [[ -z "$tag" ]]; then
    continue
  fi
  tag_args+=(-t "$tag")
done <"$tags_file"
rm -f "$tags_file"

if [[ "${#tag_args[@]}" -eq 0 ]]; then
  echo "metadata did not include any image tags" >&2
  exit 1
fi

if [[ -n "${IMAGETOOLS_CAPTURE:-}" ]]; then
  printf '%s\n' "${tag_args[@]}" "${sources[@]}" >"$IMAGETOOLS_CAPTURE"
  exit 0
fi

docker buildx imagetools create "${tag_args[@]}" "${sources[@]}"
