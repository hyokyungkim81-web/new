#!/usr/bin/env bash
# Copies the shared folders into each scene test project (HyperFrames resolves
# paths from a project's own root and does not follow symlinks).
set -euo pipefail
cd "$(dirname "$0")"
for t in t*/; do
  for d in assets compositions; do
    rm -rf "$t$d" && cp -R "../$d" "$t$d"
  done
done
