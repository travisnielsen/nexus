#!/usr/bin/env bash
# Monorepo development environment setup for Nexus.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DEFAULT_PYTHON_VERSION="3.12"
PYTHON_VERSION="${1:-$DEFAULT_PYTHON_VERSION}"

log() {
  local level="$1"
  local color="$2"
  local message="$3"
  echo -e "${color}$(date '+%Y-%m-%d %H:%M:%S') [${level}]${NC} ${message}"
}

info() { log "INF" "$BLUE" "$1"; }
success() { log "SUC" "$GREEN" "$1"; }
warn() { log "WRN" "$YELLOW" "$1"; }
error() { log "ERR" "$RED" "$1"; }

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

print_banner() {
  echo -e "${CYAN}"
  cat <<'EOF'
 _   _                       
| \ | | _____  ___   _ ___   
|  \| |/ _ \ \/ / | | / __|  
| |\  |  __/>  <| |_| \__ \  
|_| \_|\___/_/\_\\__,_|___/  
EOF
  echo -e "${NC}"
  echo -e "${BLUE}Nexus Monorepo Development Setup${NC}"
  echo ""
}

check_prerequisites() {
  info "Checking prerequisites..."

  if ! command_exists uv; then
    error "uv is required but not installed"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
  fi

  success "uv found: $(uv --version)"

  if command_exists node; then
    success "node found: $(node --version)"
  else
    warn "node is not installed; frontend dependencies will be skipped"
  fi
}

install_python_versions() {
  info "Installing Python versions for local dev workflows..."
  uv python install 3.11 3.12 3.13 >/dev/null
  success "Python versions installed (3.11, 3.12, 3.13)"
}

setup_python_project() {
  local project_dir="$1"
  local project_name="$2"

  info "Syncing ${project_name} dependencies..."
  (cd "$project_dir" && uv sync --dev)
  success "${project_name} dependencies ready"
}

setup_frontend() {
  if ! command_exists node; then
    return
  fi

  info "Installing frontend dependencies..."
  (cd src/frontend && npm install)
  success "frontend dependencies ready"
}

setup_git_hooks() {
  if [[ -d ".githooks" ]] && git rev-parse --git-dir >/dev/null 2>&1; then
    chmod +x .githooks/* 2>/dev/null || true
    git config core.hooksPath .githooks
    success "git hooks configured"
  fi
}

main() {
  print_banner
  check_prerequisites
  install_python_versions

  setup_python_project "src/backend/api" "api"
  setup_python_project "src/backend/mcp" "mcp"
  setup_python_project "src/backend/agent-a2a" "agent-a2a"
  setup_frontend
  setup_git_hooks

  echo ""
  success "================================================"
  success "Development environment setup complete"
  success "================================================"
  echo ""
  echo -e "  Default Python: ${GREEN}${PYTHON_VERSION}${NC}"
  echo -e "  Run all checks: ${CYAN}uv run --project . poe check${NC}"
  echo -e "  Start app:       ${CYAN}npm run dev${NC}"
}

main "$@"
