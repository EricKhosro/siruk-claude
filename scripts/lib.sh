# shellcheck shell=bash
# Shared helpers for the Siruk admin API scripts. Sourced, not executed.
#
# Env overrides:
#   SIRUK_API         base url (default: demo)
#   SIRUK_TOKEN       JWT inline (takes precedence over the token file)
#   SIRUK_TOKEN_FILE  path to the token file (default: <repo>/.siruk-token)
#   SIRUK_CONFIG      pacing/retry config file (default: <repo>/config.json)
#   SIRUK_NO_PACE=1   skip all pacing for this command (single ad-hoc calls)
#
# Pacing and retry knobs live in config.json — see that file and scripts/README.md.

SIRUK_API="${SIRUK_API:-https://demo-api.siruk.am/api/admin}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="${SIRUK_TOKEN_FILE:-$ROOT/.siruk-token}"
CONFIG_FILE="${SIRUK_CONFIG:-$ROOT/config.json}"
CACHE="$ROOT/.siruk-cache"

die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*" >&2; }

siruk_token() {
  if [[ -n ${SIRUK_TOKEN:-} ]]; then printf '%s' "$SIRUK_TOKEN"; return; fi
  [[ -f $TOKEN_FILE ]] || die "no token found at $TOKEN_FILE — see scripts/README.md"
  tr -d '[:space:]' < "$TOKEN_FILE"
}

# ---------------------------------------------------------------- config ----
# Defaults live here so the scripts still run if config.json is missing or
# partial; the file is deep-merged over them.
_CFG_DEFAULTS='{
  "request": {"delay_seconds":0.6,"jitter_seconds":0.3,"chunk_size":15,
              "chunk_pause_seconds":5,"idle_reset_seconds":120,
              "timeout_seconds":60,"connect_timeout_seconds":15},
  "retry":   {"attempts":4,"backoff_seconds":2,"backoff_factor":2,
              "max_backoff_seconds":30,
              "retry_on_status":[408,425,429,500,502,503,504],
              "retry_on_network_error":true},
  "media":   {"delay_seconds":2,"jitter_seconds":0.5,"chunk_size":5,
              "chunk_pause_seconds":15,"max_pixels":2000,
              "verify":{"enabled":true,"wait_seconds":2,"attempts":3,
                        "delete_broken":true,"retry_upload":true,
                        "upload_attempts":2}},
  "product": {"pause_seconds":3}
}'

_cfg_load() {
  local file_json='{}' line key val
  if [[ -f $CONFIG_FILE ]]; then
    if ! file_json=$(jq -c . "$CONFIG_FILE" 2>/dev/null); then
      note "⚠ $CONFIG_FILE is not valid JSON — falling back to built-in defaults"
      file_json='{}'
    fi
  fi
  # One jq call emits "NAME<TAB>value" lines; no eval, values are checked below.
  while IFS=$'\t' read -r key val; do
    [[ -n $key ]] || continue
    case $key in
      REQ_DELAY)           CFG_REQ_DELAY=$val ;;
      REQ_JITTER)          CFG_REQ_JITTER=$val ;;
      REQ_CHUNK)           CFG_REQ_CHUNK=$val ;;
      REQ_CHUNK_PAUSE)     CFG_REQ_CHUNK_PAUSE=$val ;;
      REQ_IDLE_RESET)      CFG_REQ_IDLE_RESET=$val ;;
      REQ_TIMEOUT)         CFG_REQ_TIMEOUT=$val ;;
      REQ_CONNECT_TIMEOUT) CFG_REQ_CONNECT_TIMEOUT=$val ;;
      RETRY_ATTEMPTS)      CFG_RETRY_ATTEMPTS=$val ;;
      RETRY_BACKOFF)       CFG_RETRY_BACKOFF=$val ;;
      RETRY_FACTOR)        CFG_RETRY_FACTOR=$val ;;
      RETRY_MAX_BACKOFF)   CFG_RETRY_MAX_BACKOFF=$val ;;
      RETRY_STATUS)        CFG_RETRY_STATUS=$val ;;
      RETRY_NET)           CFG_RETRY_NET=$val ;;
      MEDIA_DELAY)         CFG_MEDIA_DELAY=$val ;;
      MEDIA_JITTER)        CFG_MEDIA_JITTER=$val ;;
      MEDIA_CHUNK)         CFG_MEDIA_CHUNK=$val ;;
      MEDIA_CHUNK_PAUSE)   CFG_MEDIA_CHUNK_PAUSE=$val ;;
      MEDIA_MAX_PX)        CFG_MEDIA_MAX_PX=$val ;;
      MEDIA_VERIFY)        CFG_MEDIA_VERIFY=$val ;;
      MEDIA_VERIFY_WAIT)   CFG_MEDIA_VERIFY_WAIT=$val ;;
      MEDIA_VERIFY_TRIES)  CFG_MEDIA_VERIFY_TRIES=$val ;;
      MEDIA_DELETE_BROKEN) CFG_MEDIA_DELETE_BROKEN=$val ;;
      MEDIA_RETRY_UPLOAD)  CFG_MEDIA_RETRY_UPLOAD=$val ;;
      MEDIA_UPLOAD_TRIES)  CFG_MEDIA_UPLOAD_TRIES=$val ;;
      PRODUCT_PAUSE)       CFG_PRODUCT_PAUSE=$val ;;
    esac
  done < <(jq -rn --argjson d "$_CFG_DEFAULTS" --argjson f "$file_json" '
    ($d * $f) as $c
    | def num($v; $fallback): if ($v | type) == "number" and $v >= 0 then $v else $fallback end;
      def yn($v; $fallback):  if ($v | type) == "boolean" then $v else $fallback end;
      [ ["REQ_DELAY",           num($c.request.delay_seconds; 0.6)],
        ["REQ_JITTER",          num($c.request.jitter_seconds; 0)],
        ["REQ_CHUNK",           num($c.request.chunk_size; 0)],
        ["REQ_CHUNK_PAUSE",     num($c.request.chunk_pause_seconds; 0)],
        ["REQ_IDLE_RESET",      num($c.request.idle_reset_seconds; 120)],
        ["REQ_TIMEOUT",         num($c.request.timeout_seconds; 60)],
        ["REQ_CONNECT_TIMEOUT", num($c.request.connect_timeout_seconds; 15)],
        ["RETRY_ATTEMPTS",      num($c.retry.attempts; 1)],
        ["RETRY_BACKOFF",       num($c.retry.backoff_seconds; 2)],
        ["RETRY_FACTOR",        num($c.retry.backoff_factor; 2)],
        ["RETRY_MAX_BACKOFF",   num($c.retry.max_backoff_seconds; 30)],
        ["RETRY_STATUS",        (($c.retry.retry_on_status // []) | map(select(type=="number")|tostring) | join(" "))],
        ["RETRY_NET",           yn($c.retry.retry_on_network_error; true)],
        ["MEDIA_DELAY",         num($c.media.delay_seconds; 2)],
        ["MEDIA_JITTER",        num($c.media.jitter_seconds; 0)],
        ["MEDIA_CHUNK",         num($c.media.chunk_size; 0)],
        ["MEDIA_CHUNK_PAUSE",   num($c.media.chunk_pause_seconds; 0)],
        ["MEDIA_MAX_PX",        num($c.media.max_pixels; 2000)],
        ["MEDIA_VERIFY",        yn($c.media.verify.enabled; true)],
        ["MEDIA_VERIFY_WAIT",   num($c.media.verify.wait_seconds; 2)],
        ["MEDIA_VERIFY_TRIES",  num($c.media.verify.attempts; 3)],
        ["MEDIA_DELETE_BROKEN", yn($c.media.verify.delete_broken; true)],
        ["MEDIA_RETRY_UPLOAD",  yn($c.media.verify.retry_upload; true)],
        ["MEDIA_UPLOAD_TRIES",  num($c.media.verify.upload_attempts; 2)],
        ["PRODUCT_PAUSE",       num($c.product.pause_seconds; 0)] ]
      | .[] | "\(.[0])\t\(.[1])"')

  # Env wins over the file (one-off overrides without editing config.json).
  CFG_REQ_DELAY=${SIRUK_DELAY:-$CFG_REQ_DELAY}
  CFG_REQ_CHUNK=${SIRUK_CHUNK_SIZE:-$CFG_REQ_CHUNK}
  CFG_REQ_CHUNK_PAUSE=${SIRUK_CHUNK_PAUSE:-$CFG_REQ_CHUNK_PAUSE}
  CFG_MEDIA_DELAY=${SIRUK_MEDIA_DELAY:-$CFG_MEDIA_DELAY}
  CFG_RETRY_ATTEMPTS=${SIRUK_RETRIES:-$CFG_RETRY_ATTEMPTS}
  CFG_MEDIA_MAX_PX=${MAX_PX:-$CFG_MEDIA_MAX_PX}

  if [[ ${SIRUK_NO_PACE:-} == 1 ]]; then
    CFG_REQ_DELAY=0;   CFG_REQ_JITTER=0;   CFG_REQ_CHUNK=0
    CFG_MEDIA_DELAY=0; CFG_MEDIA_JITTER=0; CFG_MEDIA_CHUNK=0
    CFG_PRODUCT_PAUSE=0
  fi
}

# ---------------------------------------------------------------- pacing ----
_now_ms()   { perl -e 'use Time::HiRes qw(time); printf "%.0f", time()*1000'; }
_to_ms()    { awk -v s="${1:-0}" 'BEGIN{ if (s < 0) s = 0; printf "%.0f", s*1000 }'; }
_ms_sleep() {
  local s
  s=$(awk -v m="${1:-0}" 'BEGIN{ if (m <= 0) print 0; else printf "%.3f", m/1000 }')
  [[ $s == 0 ]] || sleep "$s"
  return 0
}

# pace <channel>   channel: api | media | product
#
# Waits so that consecutive requests are at least <delay> apart, adds jitter,
# and pauses for <chunk_pause> after every <chunk_size> requests. The counter
# and last-request time live in .siruk-cache/.pace-<channel>, so pacing holds
# across separate script invocations (an import run is one script per row), and
# resets itself after request.idle_reset_seconds of quiet.
pace() {
  local ch=${1:-api} delay jitter chunk pause state last count now wait_ms jit_ms
  case $ch in
    media)   delay=$CFG_MEDIA_DELAY; jitter=$CFG_MEDIA_JITTER
             chunk=$CFG_MEDIA_CHUNK; pause=$CFG_MEDIA_CHUNK_PAUSE ;;
    product) _ms_sleep "$(_to_ms "$CFG_PRODUCT_PAUSE")"; return 0 ;;
    *)       delay=$CFG_REQ_DELAY;   jitter=$CFG_REQ_JITTER
             chunk=$CFG_REQ_CHUNK;   pause=$CFG_REQ_CHUNK_PAUSE ;;
  esac

  state="$CACHE/.pace-$ch"
  last=0; count=0
  if [[ -f $state ]]; then read -r last count < "$state" || true; fi
  [[ $last =~ ^[0-9]+$ ]] || last=0
  [[ $count =~ ^[0-9]+$ ]] || count=0

  now=$(_now_ms)
  # a long quiet gap means a new run started — forget the old chunk counter
  (( now - last > $(_to_ms "$CFG_REQ_IDLE_RESET") )) && count=0
  count=$((count + 1))

  wait_ms=$(( last + $(_to_ms "$delay") - now ))
  (( wait_ms < 0 )) && wait_ms=0
  jit_ms=$(_to_ms "$jitter")
  (( jit_ms > 0 )) && wait_ms=$(( wait_ms + RANDOM % jit_ms ))

  if (( $(_to_ms "$chunk") > 0 )) && (( count > ${chunk%.*} )); then
    wait_ms=$(( wait_ms + $(_to_ms "$pause") ))
    count=1
    note "… chunk of ${chunk%.*} $ch requests done — pausing ${pause}s"
  fi

  _ms_sleep "$wait_ms"
  printf '%s %s\n' "$(_now_ms)" "$count" > "$state"
}

# _retryable <curl-rc> <http-code> → 0 if this attempt is worth repeating
_retryable() {
  local rc=$1 code=$2 s
  if (( rc != 0 )); then [[ $CFG_RETRY_NET == true ]] && return 0 || return 1; fi
  for s in $CFG_RETRY_STATUS; do [[ $code == "$s" ]] && return 0; done
  return 1
}

# _backoff <attempt> → seconds to wait before attempt+1
_backoff() {
  awk -v b="$CFG_RETRY_BACKOFF" -v f="$CFG_RETRY_FACTOR" -v m="$CFG_RETRY_MAX_BACKOFF" -v a="$1" \
      'BEGIN{ w = b * (f ^ (a - 1)); if (w > m) w = m; if (w < 0) w = 0; printf "%.2f", w }'
}

# ------------------------------------------------------------------- api ----
# api METHOD PATH [PAYLOAD_FILE|-]   → JSON body on stdout, "HTTP <code>" on stderr.
# Paced and retried per config.json. Exits non-zero on a final >=400 and dumps
# the error body to stderr.
api() {
  local method=$1 path=$2 data=${3:-} out code body tok rc attempt=1 wait
  # resolve the token first: die() inside $( ) would only kill the subshell,
  # and an empty Bearer header comes back as a confusing 401
  tok=$(siruk_token) || exit 1
  local -a args=(-sS -X "$method"
                 -H "Authorization: Bearer $tok"
                 -H 'Accept: application/json'
                 --connect-timeout "$CFG_REQ_CONNECT_TIMEOUT"
                 --max-time "$CFG_REQ_TIMEOUT"
                 -w '\n%{http_code}')
  [[ -n $data ]] && args+=(-H 'Content-Type: application/json' --data-binary @"$data")
  # Content locale for READS (en|ru|hy). Writes carry "locale" in the body instead
  # (reference/admin-api.md → Translations); the header is harmless on a write.
  [[ -n ${SIRUK_LANG:-} ]] && args+=(-H "Content-Language: $SIRUK_LANG")

  while :; do
    pace api
    if out=$(curl "${args[@]}" "${SIRUK_API}${path}"); then rc=0; else rc=$?; fi
    if (( rc == 0 )); then
      code=${out##*$'\n'}; body=${out%$'\n'*}
    else
      code=000; body="curl exited $rc (network/timeout)"
    fi

    if _retryable "$rc" "$code" && (( attempt < ${CFG_RETRY_ATTEMPTS%.*} )); then
      wait=$(_backoff "$attempt")
      note "HTTP $code  $method $path — retrying in ${wait}s (attempt $attempt/${CFG_RETRY_ATTEMPTS%.*})"
      sleep "$wait"
      attempt=$((attempt + 1))
      continue
    fi
    break
  done

  note "HTTP $code  $method $path"
  if (( rc != 0 )) || (( code >= 400 )); then
    printf '%s\n' "$body" >&2
    (( code == 401 || code == 403 )) && note "→ token expired or WAF-blocked; refresh it (scripts/README.md)"
    exit 1
  fi
  printf '%s\n' "$body"
}

# api_json METHOD PATH <<< '{"json":"from stdin"}'
api_json() {
  local tmp; tmp=$(mktemp); cat > "$tmp"
  api "$1" "$2" "$tmp"; local rc=$?
  rm -f "$tmp"; return $rc
}

urlencode() { jq -rn --arg s "$1" '$s|@uri'; }

# ----------------------------------------------------------------- media ----
# media_url <id> → the storage url of a media record (empty if unknown)
media_url() { api GET "/medias/$1" 2>/dev/null | jq -r '.data.url // empty'; }

# url_status <url> → the HTTP status of a GET on a storage url (000 = no answer).
# Storage urls are plain files, not API calls: no Authorization header.
url_status() {
  local out
  pace api
  out=$(curl -sS -o /dev/null -L \
             --connect-timeout "$CFG_REQ_CONNECT_TIMEOUT" --max-time "$CFG_REQ_TIMEOUT" \
             -w '%{http_code}' "$1" 2>/dev/null) || out=000
  printf '%s' "${out:-000}"
}

# Every upload creates THREE media rows: the original, `<name>-adminThumbnail`
# and `<name>-<hash>` (the webp the storefront serves). `GET /medias/<id>.url`
# always returns the admin thumbnail, so the webp — the one a customer's browser
# actually requests, and the one reported broken on 2026-08-13 — needs probing
# by hand. Returns the HTTP status, or "n/a" when there is no webp row.
media_webp_status() {
  local id=$1 host fn sib
  host=${SIRUK_API%/api/admin}
  fn=$(api GET "/medias/$id" 2>/dev/null | jq -r '.data.filename // empty') || return 0
  [[ -n $fn ]] || { printf 'n/a'; return 0; }
  sib=$(api GET "/medias/$((id + 2))" 2>/dev/null | jq -r '.data.filename // empty') || sib=""
  # the webp row is the original's filename plus a hash suffix. A moved media
  # (POST /medias-move) drops the extension from its own filename, so the
  # sibling reads "<fn>.jpg-<hash>" then.
  case $sib in
    "$fn"-adminThumbnail|"$fn".*-adminThumbnail) printf 'n/a'; return 0 ;;   # thumbnail, not the webp
    "$fn"-*|"$fn".*-*) ;;                                                    # hashed sibling → the webp
    *) printf 'n/a'; return 0 ;;
  esac
  url_status "$host/storage/webp/$(urlencode "$sib").webp"
}

# media_ok <id> → 0 if the record exists AND its file actually resolves.
# The demo server can hand back a media id whose file was never written — the
# record looks fine, every storage url 404s (found 2026-08-13, media 621).
media_ok() {
  local id=$1 url status try=1
  while :; do
    # a missing record makes api exit inside the substitution only
    url=$(media_url "$id") || url=""
    if [[ -n $url ]]; then
      status=$(url_status "$url")
      [[ $status == 200 ]] && return 0
    else
      status="no media record"
    fi
    (( try >= ${CFG_MEDIA_VERIFY_TRIES%.*} )) && break
    note "media $id not readable yet ($status) — re-checking in ${CFG_MEDIA_VERIFY_WAIT}s"
    sleep "$CFG_MEDIA_VERIFY_WAIT"
    try=$((try + 1))
  done
  note "⚠ media $id is broken: $status ${url:+($url)}"
  return 1
}

# One-line-per-variant summary, reads a product GET body on stdin.
# --- price sanity -----------------------------------------------------------
# Sale price is the most sensitive field in the catalogue (reference/pricing.md).
# A variant priced at or below its cost is almost always the wrong hafo row.
# price_guard <variants-json-array> ; exits non-zero unless ALLOW_BELOW_COST=1.
price_guard() {
  local bad
  bad=$(jq -r '
    # price is the pack price (sale_mode pack) or the per-kg price (weight, with a per-kg cost)
    def sale: (.price // 0);
    .[] | select((.cost_price // 0) > 0 and (sale) <= (.cost_price // 0))
        | "  sku=\(.sku)  sale=\(sale)  cost=\(.cost_price)"' <<<"$1")
  [[ -z $bad ]] && return 0
  note "⚠ sale price at or below cost — this is the wrong hafo row or an invented price:"
  printf '%s\n' "$bad" >&2
  if [[ ${ALLOW_BELOW_COST:-} == 1 ]]; then note "  ALLOW_BELOW_COST=1 set — writing anyway"; return 0; fi
  die "refusing to write (set ALLOW_BELOW_COST=1 only if the user explicitly approved this price)"
}

variant_table() {
  jq -r '.data // .
         | "product \(.id)  \(.name)  [categories \(.category_ids|tostring)  brand \(.brand_id)]",
           "  type \(.attribute_family_name // .attribute_family_id)",
           (.variants[] | "  variant \(.id // "NEW")  \(.name // "-")  sku=\(.sku)  \(.sale_mode // "-") \(.size_label // "no size")  \(.price) AMD  available=\(.available_quantity // .initial_stock // "-")  default=\(.is_default)  attrs=\((.attribute_values // {})|tostring)")'
}

mkdir -p "$CACHE"
_cfg_load
