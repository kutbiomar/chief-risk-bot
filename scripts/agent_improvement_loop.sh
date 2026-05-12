#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INTERVAL_SECONDS="${AGENT_LOOP_INTERVAL_SECONDS:-600}"
TOKEN_THRESHOLD="${AGENT_CONTEXT_TOKEN_THRESHOLD:-200000}"
PROMPT_FILE="${AGENT_LOOP_PROMPT_FILE:-admin/status/IMPROVEMENT_LOOP_PROMPT.md}"
LOCK_DIR="${AGENT_LOOP_LOCK_DIR:-$ROOT_DIR/.agent-improvement-loop.lock}"
RUN_ONCE=0

usage() {
  cat <<'USAGE'
Usage: scripts/agent_improvement_loop.sh [--once]

Runs the configured improvement agent every 10 minutes by default, skipping a
tick when another run is already active.

Required:
  AGENT_LOOP_COMMAND
    Shell command that runs one agent task. The improvement prompt is passed on
    stdin, for example:
      AGENT_LOOP_COMMAND='cursor-agent run --autonomous'

Optional:
  AGENT_LOOP_INTERVAL_SECONDS       Default: 600
  AGENT_LOOP_PROMPT_FILE            Default: admin/status/IMPROVEMENT_LOOP_PROMPT.md
  AGENT_LOOP_LOCK_DIR               Default: .agent-improvement-loop.lock
  AGENT_CONTEXT_TOKENS_COMMAND      Command that prints current context tokens
  AGENT_CONTEXT_CLEAR_COMMAND       Command that clears/compacts context
  AGENT_CONTEXT_TOKEN_THRESHOLD     Default: 200000

Context clearing depends on the surrounding agent runtime exposing a command or
API. This script only calls the configured hooks.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --once)
      RUN_ONCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

release_lock() {
  rm -rf "$LOCK_DIR"
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$LOCK_DIR/started_at"
    trap release_lock EXIT INT TERM
    return 0
  fi

  local existing_pid=""
  if [[ -f "$LOCK_DIR/pid" ]]; then
    existing_pid="$(tr -cd '0-9' < "$LOCK_DIR/pid")"
  fi

  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    log "Skipping tick; improvement task already running as pid $existing_pid."
    return 1
  fi

  log "Removing stale improvement-loop lock."
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR"
  printf '%s\n' "$$" > "$LOCK_DIR/pid"
  printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$LOCK_DIR/started_at"
  trap release_lock EXIT INT TERM
  return 0
}

maybe_clear_context() {
  if [[ -z "${AGENT_CONTEXT_TOKENS_COMMAND:-}" || -z "${AGENT_CONTEXT_CLEAR_COMMAND:-}" ]]; then
    return 0
  fi

  local raw_tokens
  if ! raw_tokens="$(bash -lc "$AGENT_CONTEXT_TOKENS_COMMAND" 2>/dev/null)"; then
    log "Context token command failed; skipping context clear check."
    return 0
  fi

  local tokens
  tokens="$(printf '%s' "$raw_tokens" | tr -cd '0-9')"
  if [[ -z "$tokens" ]]; then
    log "Context token command did not return a number; skipping context clear check."
    return 0
  fi

  if (( tokens > TOKEN_THRESHOLD )); then
    log "Context is ${tokens} tokens, above ${TOKEN_THRESHOLD}; running context clear command."
    bash -lc "$AGENT_CONTEXT_CLEAR_COMMAND"
  fi
}

run_iteration() {
  if [[ -z "${AGENT_LOOP_COMMAND:-}" ]]; then
    log "AGENT_LOOP_COMMAND is not set; cannot run an improvement task."
    return 64
  fi
  if [[ ! -f "$PROMPT_FILE" ]]; then
    log "Prompt file not found: $PROMPT_FILE"
    return 66
  fi

  if ! acquire_lock; then
    return 0
  fi

  local status=0
  log "Starting improvement task."
  if ! bash -lc "$AGENT_LOOP_COMMAND" < "$PROMPT_FILE"; then
    status=$?
    log "Improvement task failed with exit code $status."
  else
    log "Improvement task completed."
  fi

  maybe_clear_context
  release_lock
  trap - EXIT INT TERM
  return "$status"
}

if (( RUN_ONCE )); then
  run_iteration
  exit $?
fi

log "Starting improvement loop with ${INTERVAL_SECONDS}s interval."
while true; do
  run_iteration || true
  sleep "$INTERVAL_SECONDS"
done
