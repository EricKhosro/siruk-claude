# shellcheck shell=bash
# Shared helpers for the Siruk admin API scripts. Sourced, not executed.
#
# Env overrides:
#   SIRUK_API         base url (default: demo)
#   SIRUK_TOKEN       JWT inline (takes precedence over the token file)
#   SIRUK_TOKEN_FILE  path to the token file (default: <repo>/.siruk-token)

SIRUK_API="${SIRUK_API:-https://demo-api.siruk.am/api/admin}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="${SIRUK_TOKEN_FILE:-$ROOT/.siruk-token}"
CACHE="$ROOT/.siruk-cache"

die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*" >&2; }

siruk_token() {
  if [[ -n ${SIRUK_TOKEN:-} ]]; then printf '%s' "$SIRUK_TOKEN"; return; fi
  [[ -f $TOKEN_FILE ]] || die "no token found at $TOKEN_FILE — see scripts/README.md"
  tr -d '[:space:]' < "$TOKEN_FILE"
}

# api METHOD PATH [PAYLOAD_FILE|-]   → JSON body on stdout, "HTTP <code>" on stderr.
# Exits non-zero on >=400 and dumps the error body to stderr.
api() {
  local method=$1 path=$2 data=${3:-} out code body tok
  # resolve the token first: die() inside $( ) would only kill the subshell,
  # and an empty Bearer header comes back as a confusing 401
  tok=$(siruk_token) || exit 1
  local -a args=(-sS -X "$method"
                 -H "Authorization: Bearer $tok"
                 -H 'Accept: application/json'
                 -w '\n%{http_code}')
  [[ -n $data ]] && args+=(-H 'Content-Type: application/json' --data-binary @"$data")

  out=$(curl "${args[@]}" "${SIRUK_API}${path}") || die "curl failed: $method $path"
  code=${out##*$'\n'}
  body=${out%$'\n'*}
  note "HTTP $code  $method $path"
  if (( code >= 400 )); then
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

# One-line-per-variant summary, reads a product GET body on stdin.
variant_table() {
  jq -r '.data // .
         | "product \(.id)  \(.name)  [categories \(.category_ids|tostring)  brand \(.brand_id)]",
           (.variants[] | "  variant \(.id // "NEW")  \(.name // "-")  sku=\(.sku)  \(.price) AMD  stock=\(.stock)  default=\(.is_default)  attrs=\((.attribute_value_ids // {})|tostring)")'
}

mkdir -p "$CACHE"
