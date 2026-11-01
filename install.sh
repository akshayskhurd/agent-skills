#!/usr/bin/env bash
# Universal Zero-Dependency Installer for Agent Skills
# Compatible with: Claude Code, OpenCode, Codex, Pi, Google Antigravity / Gemini CLI, and Universal Agents
# Requires NO Python. Uses standard POSIX utilities (mkdir, cp, ln, rm).
set -euo pipefail

REPO_URL="https://github.com/akshayskhurd/agent-skills.git"
CACHE_DIR="${HOME}/.agent-skills-cache"

TARGET="auto"
MODE="copy"
SCOPE="global"
SKILLS="all"
ACTION="install"

show_help() {
  cat <<'EOF'
Universal Agent Skills Installer (Zero-Dependency)

Usage:
  ./install.sh [options]
  curl -fsSL https://raw.githubusercontent.com/akshayskhurd/agent-skills/main/install.sh | bash -s -- [options]

Options:
  -t, --target <harness>   Target harness: 'auto' (detect installed), 'all', or comma-separated
                           (claude, opencode, codex, pi, gemini, agents). Default: auto.
  -m, --mode <mode>        'copy' for standalone copy, 'symlink' for live git link. Default: copy.
  -s, --skills <skills>    Comma-separated list of skills, or 'all'. Default: all.
  -g, --global             Install to user home harness directory (default).
  -l, --local              Install to current directory / workspace (.agents/skills, .claude/skills, etc.).
      --symlink            Shortcut for --mode symlink.
      --status             Audit installed skills across all detected harnesses.
      --uninstall          Remove installed skills from target harnesses.
      --list               List available skills in this toolkit.
  -h, --help               Show this help message.

Supported Harnesses:
  • claude       -> Claude Code (~/.claude/skills or .claude/skills)
  • opencode     -> OpenCode (~/.opencode/skills or .opencode/skills)
  • codex        -> Codex / OpenAI (~/.codex/skills or .codex/skills)
  • pi           -> Pi Agent (~/.pi/skills or .pi/skills)
  • gemini       -> Antigravity / Gemini (~/.gemini/config/skills or .gemini/skills)
  • agents       -> Universal Agent standard (~/.agents/skills or .agents/skills)
EOF
}

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -m|--mode) MODE="$2"; shift 2 ;;
    -s|--skills) SKILLS="$2"; shift 2 ;;
    -g|--global) SCOPE="global"; shift ;;
    -l|--local) SCOPE="local"; shift ;;
    --symlink) MODE="symlink"; shift ;;
    --status) ACTION="status"; shift ;;
    --uninstall) ACTION="uninstall"; shift ;;
    --list) ACTION="list"; shift ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "Unknown option: $1" >&2; show_help; exit 1 ;;
  esac
done

# Resolve repo root directory (handles local execution or remote piped curl)
SCRIPT_SOURCE="${BASH_SOURCE[0]:-${0:-}}"
if [[ -n "${SCRIPT_SOURCE}" && -f "${SCRIPT_SOURCE}" ]]; then
  REPO_ROOT="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
else
  # Running via pipe (curl ... | bash)
  echo "📦 Fetching latest agent-skills toolkit..."
  if command -v git >/dev/null 2>&1; then
    if [[ -d "${CACHE_DIR}/.git" ]]; then
      git -C "${CACHE_DIR}" pull --quiet origin main 2>/dev/null || true
    else
      rm -rf "${CACHE_DIR}"
      git clone --depth 1 "${REPO_URL}" "${CACHE_DIR}" --quiet || {
        echo "Error: Failed to clone repository from ${REPO_URL}" >&2
        exit 1
      }
    fi
    REPO_ROOT="${CACHE_DIR}"
  else
    # Fallback to tarball if git is not installed
    mkdir -p "${CACHE_DIR}"
    curl -fsSL "https://github.com/akshayskhurd/agent-skills/archive/refs/heads/main.tar.gz" | tar -xz -C "${CACHE_DIR}" --strip-components=1 || {
      echo "Error: Failed to download repository tarball" >&2
      exit 1
    }
    REPO_ROOT="${CACHE_DIR}"
  fi
fi

SKILLS_DIR="${REPO_ROOT}/skills"

if [[ ! -d "${SKILLS_DIR}" ]]; then
  echo "Error: Cannot find skills directory at ${SKILLS_DIR}" >&2
  exit 1
fi

# Discover available skills in source repo
AVAILABLE_SKILLS=()
for s in "${SKILLS_DIR}"/*; do
  if [[ -d "$s" && -f "$s/SKILL.md" ]]; then
    AVAILABLE_SKILLS+=("$(basename "$s")")
  fi
done

if [[ "${ACTION}" == "list" ]]; then
  echo "Available Agent Skills:"
  for s in "${AVAILABLE_SKILLS[@]}"; do
    echo "  • ${s}"
  done
  exit 0
fi

# Resolve which skills to process
SELECTED_SKILLS=()
if [[ "${SKILLS}" == "all" ]]; then
  SELECTED_SKILLS=("${AVAILABLE_SKILLS[@]}")
else
  OLD_IFS="$IFS"
  IFS=','
  for item in ${SKILLS}; do
    trimmed="$(echo "$item" | xargs)"
    if [[ -n "$trimmed" ]]; then
      SELECTED_SKILLS+=("$trimmed")
    fi
  done
  IFS="$OLD_IFS"
fi

# Harness directory resolver
get_harness_dir() {
  local harness="$1"
  local scope="$2"
  if [[ "$scope" == "global" ]]; then
    case "$harness" in
      claude) echo "${HOME}/.claude/skills" ;;
      opencode) echo "${HOME}/.opencode/skills" ;;
      codex) echo "${HOME}/.codex/skills" ;;
      pi) echo "${HOME}/.pi/skills" ;;
      gemini|antigravity) echo "${HOME}/.gemini/config/skills" ;;
      agents) echo "${HOME}/.agents/skills" ;;
      *) echo "" ;;
    esac
  else
    case "$harness" in
      claude) echo "$(pwd)/.claude/skills" ;;
      opencode) echo "$(pwd)/.opencode/skills" ;;
      codex) echo "$(pwd)/.codex/skills" ;;
      pi) echo "$(pwd)/.pi/skills" ;;
      gemini|antigravity) echo "$(pwd)/.agents/skills" ;;
      agents) echo "$(pwd)/.agents/skills" ;;
      *) echo "" ;;
    esac
  fi
}

# Auto-detect installed harnesses
detect_harnesses() {
  local detected=()
  if [[ -d "${HOME}/.claude" ]]; then detected+=("claude"); fi
  if [[ -d "${HOME}/.opencode" || -d "${HOME}/.config/opencode" ]]; then detected+=("opencode"); fi
  if [[ -d "${HOME}/.codex" ]]; then detected+=("codex"); fi
  if [[ -d "${HOME}/.pi" ]]; then detected+=("pi"); fi
  if [[ -d "${HOME}/.gemini" ]]; then detected+=("gemini"); fi
  if [[ ${#detected[@]} -eq 0 ]]; then
    detected+=("agents")
  fi
  echo "${detected[@]}"
}

# Determine targeted harnesses
RESOLVED_HARNESSES=()
if [[ "${TARGET}" == "all" ]]; then
  RESOLVED_HARNESSES=("claude" "opencode" "codex" "pi" "gemini" "agents")
elif [[ "${TARGET}" == "auto" ]]; then
  for h in $(detect_harnesses); do
    RESOLVED_HARNESSES+=("$h")
  done
  echo "⚡ Auto-detected harnesses: ${RESOLVED_HARNESSES[*]}"
else
  OLD_IFS="$IFS"
  IFS=','
  for item in ${TARGET}; do
    trimmed="$(echo "$item" | xargs)"
    if [[ -n "$trimmed" ]]; then
      RESOLVED_HARNESSES+=("$trimmed")
    fi
  done
  IFS="$OLD_IFS"
fi

# Execute Status Audit
if [[ "${ACTION}" == "status" ]]; then
  echo ""
  echo "================================================================"
  echo "📊 AGENT SKILLS HARNESS STATUS AUDIT"
  echo "================================================================"
  echo "Source Repository: ${REPO_ROOT}"
  echo "Available skills: ${AVAILABLE_SKILLS[*]}"
  echo ""

  for h in "${RESOLVED_HARNESSES[@]}"; do
    dest="$(get_harness_dir "$h" "$SCOPE")"
    echo "🔍 Harness: ${h} (${SCOPE})"
    echo "   Directory: ${dest}"
    if [[ -z "${dest}" || ! -d "${dest}" ]]; then
      echo "   Status: Directory does not exist (not provisioned)."
    else
      found=()
      for s in "${AVAILABLE_SKILLS[@]}"; do
        if [[ -L "${dest}/${s}" ]]; then
          found+=("${s} (symlinked)")
        elif [[ -d "${dest}/${s}" ]]; then
          found+=("${s}")
        fi
      done
      if [[ ${#found[@]} -gt 0 ]]; then
        echo "   Installed skills (${#found[@]}):"
        for item in "${found[@]}"; do
          echo "     ✓ ${item}"
        done
      else
        echo "   No skills currently installed."
      fi
    fi
    echo ""
  done
  exit 0
fi

# Execute Uninstall
if [[ "${ACTION}" == "uninstall" ]]; then
  for h in "${RESOLVED_HARNESSES[@]}"; do
    dest="$(get_harness_dir "$h" "$SCOPE")"
    if [[ -z "${dest}" || "${dest}" == "/" || ! -d "${dest}" ]]; then
      continue
    fi
    echo "🗑️  Uninstalling from ${h}: ${dest}"
    for s in "${SELECTED_SKILLS[@]}"; do
      target="${dest}/${s}"
      if [[ -L "${target}" || -d "${target}" || -f "${target}" ]]; then
        rm -rf "${target}"
        echo "  • Removed ${s}"
      fi
    done
  done
  echo "✨ Uninstallation complete."
  exit 0
fi

# Execute Install
for h in "${RESOLVED_HARNESSES[@]}"; do
  dest="$(get_harness_dir "$h" "$SCOPE")"
  if [[ -z "${dest}" || "${dest}" == "/" ]]; then
    echo "Error: Invalid destination directory resolved for harness '${h}'" >&2
    exit 1
  fi

  echo ""
  echo "📂 Deploying to ${h} (${SCOPE}) -> ${dest}"
  mkdir -p "${dest}"

  for s in "${SELECTED_SKILLS[@]}"; do
    src="${SKILLS_DIR}/${s}"
    target="${dest}/${s}"

    if [[ ! -d "${src}" ]]; then
      echo "  ⚠️ Skill '${s}' does not exist in repository. Skipping." >&2
      continue
    fi

    # Remove existing version before deploying
    rm -rf "${target}"

    if [[ "${MODE}" == "symlink" ]]; then
      abs_src="$(cd "${src}" && pwd)"
      ln -s "${abs_src}" "${target}"
      echo "  • Symlinked: ${s} -> ${target}"
    else
      cp -R "${src}" "${target}"
      echo "  • Installed: ${s}"
    fi
  done

  # When targeting Antigravity / Gemini globally, also provision plugin bundle
  if [[ ("${h}" == "gemini" || "${h}" == "antigravity") && "${SCOPE}" == "global" ]]; then
    plugin_bundle="${HOME}/.gemini/config/plugins/agent-skills"
    mkdir -p "${plugin_bundle}"
    cp "${REPO_ROOT}/plugin.json" "${plugin_bundle}/plugin.json" 2>/dev/null || true
    if [[ ! -e "${plugin_bundle}/skills" ]]; then
      ln -s "${dest}" "${plugin_bundle}/skills" 2>/dev/null || true
    fi
    echo "  • Antigravity Plugin bundle provisioned: ${plugin_bundle}"
  fi
done

echo ""
echo "✨ All selected skills successfully installed!"
echo "   Harnesses configured: ${RESOLVED_HARNESSES[*]}"
echo "   To audit status at any time, run: ./install.sh --status"
