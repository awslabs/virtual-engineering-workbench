#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:?Usage: build.sh <target-triple>}"
BIN_NAME="vew"

case "${TARGET}" in
  *apple-darwin*) cargo zigbuild --release --target "${TARGET}" ;;
  *)              cargo build --release --target "${TARGET}" ;;
esac

mkdir -p dist

case "${TARGET}" in
  *windows*)
    ARCHIVE="dist/${BIN_NAME}-${TARGET}.zip"
    (cd "target/${TARGET}/release" && zip "../../../${ARCHIVE}" "${BIN_NAME}.exe")
    ;;
  *)
    ARCHIVE="dist/${BIN_NAME}-${TARGET}.tar.gz"
    tar -czf "${ARCHIVE}" -C "target/${TARGET}/release" "${BIN_NAME}"
    ;;
esac

sha256sum "${ARCHIVE}" > "${ARCHIVE}.sha256"
echo "Built: ${ARCHIVE}"
