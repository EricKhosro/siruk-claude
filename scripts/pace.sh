#!/usr/bin/env bash
# Wait the configured amount, or show the effective pacing config.
#
#   scripts/pace.sh product     # the breather between two CSV rows in an import
#   scripts/pace.sh api         # one API-request slot (rarely needed by hand)
#   scripts/pace.sh media       # one upload slot
#   scripts/pace.sh show        # print the settings the scripts are running with
#
# Knobs live in config.json (or $SIRUK_CONFIG).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case ${1:-product} in
  show)
    printf 'config file      %s%s\n' "$CONFIG_FILE" "$([[ -f $CONFIG_FILE ]] || printf ' (missing — using built-in defaults)')"
    printf 'api base         %s\n'   "$SIRUK_API"
    printf '\nrequest   delay %ss  jitter %ss  chunk %s/%ss  idle-reset %ss  timeout %ss (connect %ss)\n' \
      "$CFG_REQ_DELAY" "$CFG_REQ_JITTER" "$CFG_REQ_CHUNK" "$CFG_REQ_CHUNK_PAUSE" \
      "$CFG_REQ_IDLE_RESET" "$CFG_REQ_TIMEOUT" "$CFG_REQ_CONNECT_TIMEOUT"
    printf 'retry     %s attempts  backoff %ss x%s (max %ss)  on: %s  network-errors %s\n' \
      "$CFG_RETRY_ATTEMPTS" "$CFG_RETRY_BACKOFF" "$CFG_RETRY_FACTOR" "$CFG_RETRY_MAX_BACKOFF" \
      "$CFG_RETRY_STATUS" "$CFG_RETRY_NET"
    printf 'media     delay %ss  jitter %ss  chunk %s/%ss  max %spx\n' \
      "$CFG_MEDIA_DELAY" "$CFG_MEDIA_JITTER" "$CFG_MEDIA_CHUNK" "$CFG_MEDIA_CHUNK_PAUSE" "$CFG_MEDIA_MAX_PX"
    printf 'media check   %s  wait %ss  %s attempts  delete-broken %s  re-upload %s (%s uploads)\n' \
      "$CFG_MEDIA_VERIFY" "$CFG_MEDIA_VERIFY_WAIT" "$CFG_MEDIA_VERIFY_TRIES" \
      "$CFG_MEDIA_DELETE_BROKEN" "$CFG_MEDIA_RETRY_UPLOAD" "$CFG_MEDIA_UPLOAD_TRIES"
    printf 'product   pause %ss between rows\n' "$CFG_PRODUCT_PAUSE"
    [[ ${SIRUK_NO_PACE:-} != 1 ]] || printf '\n⚠ SIRUK_NO_PACE=1 — all pacing disabled for this shell\n'
    ;;
  api|media|product) pace "$1" ;;
  *) die "usage: $0 [product|api|media|show]" ;;
esac
