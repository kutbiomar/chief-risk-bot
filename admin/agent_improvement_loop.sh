#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INTERVAL_SECONDS="${AGENT_LOOP_INTERVAL_SECONDS:-600}"
MAX_RUNTIME_SECONDS="${AGENT_LOOP_MAX_RUNTIME_SECONDS:-259200}"
TOKEN_THRESHOLD="${AGENT_CONTEXT_TOKEN_THRESHOLD:-200000}"
PROMPT_FILE="${AGENT_LOOP_PROMPT_FILE:-admin/status/IMPROVEMENT_LOOP_PROMPT.md}"
LOCK_DIR="${AGENT_LOOP_LOCK_DIR:-$ROOT_DIR/.agent-improvement-loop.lock}"
REMOTE_NAME="${AGENT_LOOP_REMOTE:-origin}"
BASE_BRANCH="${AGENT_LOOP_BASE_BRANCH:-main}"
MERGE_TO_MAIN="${AGENT_LOOP_MERGE_TO_MAIN:-1}"
RUN_ONCE=0

usage() {
  cat <<'USAGE'
Usage: admin/agent_improvement_loop.sh [--once]

Runs the configured improvement agent every 10 minutes by default, skipping a
tick when another run is already active. Long-running loops expire after 3 days
by default and must then be started again from scratch.

Required:
  AGENT_LOOP_COMMAND
    Shell command that runs one agent task. The improvement prompt is passed on
    stdin, for example:
      AGENT_LOOP_COMMAND='cursor-agent run --autonomous'

Optional:
  AGENT_LOOP_INTERVAL_SECONDS       Default: 600
  AGENT_LOOP_MAX_RUNTIME_SECONDS    Default: 259200 (3 days)
  AGENT_LOOP_MERGE_TO_MAIN          Default: 1; push branch, merge to main, push main after success
  AGENT_LOOP_REMOTE                 Default: origin
  AGENT_LOOP_BASE_BRANCH            Default: main
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

push_and_merge_to_main() {
  if [[ "$MERGE_TO_MAIN" == "0" ]]; then
    log "Skipping branch push/main merge because AGENT_LOOP_MERGE_TO_MAIN=0."
    return 0
  fi

  local current_branch
  current_branch="$(git branch --show-current)"
  if [[ -z "$current_branch" ]]; then
    log "Cannot push and merge from a detached HEAD."
    return 70
  fi

  if [[ -n "$(git status --porcelain)" ]]; then
    log "Worktree is not clean after the agent task; refusing to push or merge."
    git status --short >&2
    return 71
  fi

  log "Pushing ${current_branch} to ${REMOTE_NAME}."
  git push -u "$REMOTE_NAME" "$current_branch"

  if [[ "$current_branch" == "$BASE_BRANCH" ]]; then
    log "Already on ${BASE_BRANCH}; pushed branch without merge."
    return 0
  fi

  log "Merging ${current_branch} into ${BASE_BRANCH}."
  git fetch "$REMOTE_NAME" "$BASE_BRANCH"
  git checkout "$BASE_BRANCH"
  if ! git pull "$REMOTE_NAME" "$BASE_BRANCH"; then
    git checkout "$current_branch"
    return 72
  fi
  if ! git merge --no-edit "$current_branch"; then
    git merge --abort || true
    git checkout "$current_branch"
    return 73
  fi
  if ! git push -u "$REMOTE_NAME" "$BASE_BRANCH"; then
    git checkout "$current_branch"
    return 74
  fi
  git checkout "$current_branch"
  log "Merged ${current_branch} into ${BASE_BRANCH} and pushed ${BASE_BRANCH}."
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
    if ! push_and_merge_to_main; then
      status=$?
      log "Post-task push/merge failed with exit code $status."
    fi
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

START_EPOCH="$(date +%s)"
EXPIRES_EPOCH=$((START_EPOCH + MAX_RUNTIME_SECONDS))

log "Starting improvement loop with ${INTERVAL_SECONDS}s interval; expires after ${MAX_RUNTIME_SECONDS}s."
while true; do
  now="$(date +%s)"
  if (( now >= EXPIRES_EPOCH )); then
    log "Improvement loop expired; start a fresh invocation to continue."
    exit 0
  fi

  run_iteration || true

  now="$(date +%s)"
  remaining=$((EXPIRES_EPOCH - now))
  if (( remaining <= 0 )); then
    log "Improvement loop expired; start a fresh invocation to continue."
    exit 0
  fi
  if (( remaining < INTERVAL_SECONDS )); then
    sleep "$remaining"
  else
    sleep "$INTERVAL_SECONDS"
  fi
done
