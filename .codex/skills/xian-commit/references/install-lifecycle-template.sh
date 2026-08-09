#!/bin/sh
# Skill package install lifecycle template.
# Copy this file to install.sh in another skill project and fill the CONFIG block.
# Runtime SKILL.md should not reference this script; this is only package lifecycle.

set -u

MODE="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# === CONFIG: fill for the target skill package ===
SKILL_ID="__SKILL_ID__"
SKILL_LABEL="__SKILL_LABEL__"
PROMPT_FILES="__PROMPT_FILES__"
REFERENCE_FILES="__REFERENCE_FILES__"
POLICY_EXAMPLE_FILE="__POLICY_EXAMPLE_FILE__"
HOOK_FILES="__HOOK_FILES__"
# === END CONFIG ===

SKILL_SRC="$SCRIPT_DIR/SKILL.md"
PROMPTS_SRC="$SCRIPT_DIR/prompts"
REFERENCES_SRC="$SCRIPT_DIR/references"
POLICY_SRC="$SCRIPT_DIR/$POLICY_EXAMPLE_FILE"
HOOKS_SRC="$SCRIPT_DIR/hooks"

case "$MODE" in
    all|update|skill|hooks|status|verify|uninstall) ;;
    -h|--help)
        cat <<EOF
$SKILL_LABEL install

Usage:
  sh install.sh          # install all resources(default)
  sh install.sh update   # update installed resources(same as all)
  sh install.sh skill    # install only .codex skill assets and policy
  sh install.sh hooks    # install only .git/hooks
  sh install.sh status   # show installed resource status without writing
  sh install.sh verify   # verify installed resources in current repo
  sh install.sh uninstall # remove managed resources
EOF
        exit 0
        ;;
    *)
        echo "$SKILL_LABEL install: unknown mode '$MODE'." >&2
        exit 1
        ;;
esac

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
if [ -z "$GIT_DIR" ]; then
    echo "$SKILL_LABEL install: current directory is not a git repository." >&2
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
HOOKS_DST=$(cd "$GIT_DIR" && pwd)/hooks
SKILL_DST="$REPO_ROOT/.codex/skills/$SKILL_ID"
POLICY_DST="$REPO_ROOT/.$SKILL_ID"

copy_list() {
    src_dir="$1"
    dst_dir="$2"
    files="$3"
    [ -z "$files" ] && return 0
    mkdir -p "$dst_dir"
    for name in $files; do
        [ "$name" = "__PROMPT_FILES__" ] && continue
        [ "$name" = "__REFERENCE_FILES__" ] && continue
        if [ -f "$src_dir/$name" ]; then
            cp "$src_dir/$name" "$dst_dir/$name"
        fi
    done
}

install_skill() {
    [ -f "$SKILL_SRC" ] || { echo "missing SKILL.md" >&2; exit 1; }
    mkdir -p "$SKILL_DST" "$POLICY_DST"
    cp "$SKILL_SRC" "$SKILL_DST/SKILL.md"
    copy_list "$PROMPTS_SRC" "$SKILL_DST/prompts" "$PROMPT_FILES"
    copy_list "$REFERENCES_SRC" "$SKILL_DST/references" "$REFERENCE_FILES"

    if [ -f "$POLICY_SRC" ]; then
        cp "$POLICY_SRC" "$POLICY_DST/policy.example.conf"
        if [ ! -f "$POLICY_DST/config" ]; then
            cp "$POLICY_SRC" "$POLICY_DST/config"
            policy_status="created .$SKILL_ID/config"
        else
            policy_status="kept existing .$SKILL_ID/config"
        fi
    else
        policy_status="no policy example"
    fi

    echo "$SKILL_LABEL: installed skill assets"
    echo "  skill: .codex/skills/$SKILL_ID/SKILL.md"
    echo "  policy: $policy_status"
}

install_hooks() {
    [ -d "$HOOKS_SRC" ] || return 0
    mkdir -p "$HOOKS_DST"
    for hook_name in $HOOK_FILES; do
        [ "$hook_name" = "__HOOK_FILES__" ] && continue
        hook_src="$HOOKS_SRC/$hook_name"
        hook_dst="$HOOKS_DST/$hook_name"
        [ -f "$hook_src" ] || continue
        if [ -f "$hook_dst" ] && ! diff -q "$hook_src" "$hook_dst" >/dev/null 2>&1; then
            cp "$hook_dst" "$hook_dst.pre-$SKILL_ID.bak"
        fi
        cp "$hook_src" "$hook_dst"
        chmod +x "$hook_dst"
        echo "  hook: $hook_name"
    done
}

status_file() {
    label="$1"
    src="$2"
    dst="$3"
    if [ ! -f "$dst" ]; then
        echo "  missing: $label"
    elif [ -f "$src" ] && diff -q "$src" "$dst" >/dev/null 2>&1; then
        echo "  current: $label"
    elif [ -f "$src" ]; then
        echo "  differs: $label"
    else
        echo "  present: $label"
    fi
}

status_install() {
    echo "$SKILL_LABEL: install status($REPO_ROOT)"
    status_file "skill" "$SKILL_SRC" "$SKILL_DST/SKILL.md"
    for name in $PROMPT_FILES; do
        [ "$name" = "__PROMPT_FILES__" ] && continue
        status_file "prompt $name" "$PROMPTS_SRC/$name" "$SKILL_DST/prompts/$name"
    done
    for name in $REFERENCE_FILES; do
        [ "$name" = "__REFERENCE_FILES__" ] && continue
        status_file "reference $name" "$REFERENCES_SRC/$name" "$SKILL_DST/references/$name"
    done
    status_file "policy config" "" "$POLICY_DST/config"
    for hook_name in $HOOK_FILES; do
        [ "$hook_name" = "__HOOK_FILES__" ] && continue
        status_file "hook $hook_name" "$HOOKS_SRC/$hook_name" "$HOOKS_DST/$hook_name"
    done
}

verify_install() {
    status_install
    [ -f "$SKILL_DST/SKILL.md" ] || exit 1
    if [ -n "$HOOK_FILES" ] && [ "$HOOK_FILES" != "__HOOK_FILES__" ]; then
        for hook_name in $HOOK_FILES; do
            [ -x "$HOOKS_DST/$hook_name" ] || exit 1
        done
    fi
    echo "$SKILL_LABEL verify: ok"
}

uninstall_resources() {
    rm -rf "$SKILL_DST"
    rm -f "$POLICY_DST/policy.example.conf"
    rmdir "$POLICY_DST" 2>/dev/null || true
    for hook_name in $HOOK_FILES; do
        [ "$hook_name" = "__HOOK_FILES__" ] && continue
        hook_src="$HOOKS_SRC/$hook_name"
        hook_dst="$HOOKS_DST/$hook_name"
        if [ -f "$hook_src" ] && [ -f "$hook_dst" ] && diff -q "$hook_src" "$hook_dst" >/dev/null 2>&1; then
            rm -f "$hook_dst"
        fi
    done
    echo "$SKILL_LABEL uninstall: removed managed resources"
}

case "$MODE" in
    all|update) install_skill; install_hooks ;;
    skill) install_skill ;;
    hooks) install_hooks ;;
    status) status_install ;;
    verify) verify_install ;;
    uninstall) uninstall_resources ;;
esac
