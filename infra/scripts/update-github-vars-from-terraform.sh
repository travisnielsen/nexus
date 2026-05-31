#!/usr/bin/env bash
set -euo pipefail

# Synchronize selected Terraform outputs to GitHub repository variables.

usage() {
  cat <<'EOF'
Usage: update-github-vars-from-terraform.sh [--dry-run] --repo <owner/repo>

Options:
  --dry-run         Show planned changes without mutating GitHub variables.
  --repo            GitHub repository in owner/name format.
  --terraform-dir   Terraform working directory (default: current directory).
EOF
}

DRY_RUN=false
REPO=""
TF_DIR="."

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

tf_output_raw() {
  local output_name="$1"
  terraform output -raw "$output_name" 2>/dev/null || echo ""
}

build_output_map() {
  # Base mappings required by deployment workflows.
  OUTPUT_MAP["AZURE_SUBSCRIPTION_ID"]="$(tf_output_raw azure_subscription_id)"
  OUTPUT_MAP["AZURE_RESOURCE_GROUP"]="$(tf_output_raw resource_group_name)"
  OUTPUT_MAP["AZURE_CONTAINER_REGISTRY"]="$(tf_output_raw container_registry_name)"
  OUTPUT_MAP["AZURE_API_CONTAINER_APP_NAME"]="$(tf_output_raw api_container_app_name)"
  OUTPUT_MAP["AZURE_FRONTEND_CONTAINER_APP_NAME"]="$(tf_output_raw frontend_container_app_name)"
  OUTPUT_MAP["AZURE_MCP_CONTAINER_APP_NAME"]="$(tf_output_raw mcp_container_app_name)"
  OUTPUT_MAP["AZURE_A2A_CONTAINER_APP_NAME"]="$(tf_output_raw a2a_container_app_name)"

  # Foundry migration and frontend deployment support values.
  OUTPUT_MAP["AGENT_API_BASE_URL"]="$(tf_output_raw api_url)"
  OUTPUT_MAP["FOUNDRY_PROJECT_ENDPOINT"]="$(tf_output_raw foundry_project_endpoint)"

  local required_keys=(
    AZURE_SUBSCRIPTION_ID
    AZURE_RESOURCE_GROUP
    AZURE_CONTAINER_REGISTRY
    AZURE_API_CONTAINER_APP_NAME
    AZURE_FRONTEND_CONTAINER_APP_NAME
    AZURE_MCP_CONTAINER_APP_NAME
    AZURE_A2A_CONTAINER_APP_NAME
    AGENT_API_BASE_URL
    FOUNDRY_PROJECT_ENDPOINT
  )

  for key in "${required_keys[@]}"; do
    if [[ -z "${OUTPUT_MAP[$key]}" ]]; then
      echo "Missing required Terraform output for mapping key: $key" >&2
      return 1
    fi
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --terraform-dir)
      TF_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$REPO" ]]; then
  echo "Missing required --repo argument" >&2
  usage
  exit 1
fi

require_cmd terraform
require_cmd gh

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run 'gh auth login' first." >&2
  exit 1
fi

if [[ ! -d "$TF_DIR" ]]; then
  echo "Terraform directory does not exist: $TF_DIR" >&2
  exit 1
fi

pushd "$TF_DIR" >/dev/null
declare -A OUTPUT_MAP
declare -A CURRENT_MAP
declare -a ADDED
declare -a CHANGED
declare -a UNCHANGED
declare -a FAILED

if ! build_output_map; then
  popd >/dev/null
  echo "Failed to build output mapping. Ensure required Terraform outputs exist." >&2
  exit 1
fi

popd >/dev/null

for key in "${!OUTPUT_MAP[@]}"; do
  current_value_raw="$(gh api "/repos/$REPO/actions/variables/$key" --jq '.value' 2>/dev/null || true)"
  CURRENT_MAP["$key"]="$current_value_raw"

  if [[ -z "$current_value_raw" ]]; then
    ADDED+=("$key")
  elif [[ "$current_value_raw" == "${OUTPUT_MAP[$key]}" ]]; then
    UNCHANGED+=("$key")
  else
    CHANGED+=("$key")
  fi
done

echo "Repository: $REPO"
echo "Dry run: $DRY_RUN"
echo
echo "Planned sync summary"

# Safely compute array lengths with default 0 if arrays are empty
set +u
added_count=${#ADDED[@]:-0}
changed_count=${#CHANGED[@]:-0}
unchanged_count=${#UNCHANGED[@]:-0}
set -u

echo "  Added: $added_count"
echo "  Changed: $changed_count"
echo "  Unchanged: $unchanged_count"
echo

# Output change details safely
set +u
for key in "${ADDED[@]:-}"; do
  [[ -n "$key" ]] && echo "  + $key=${OUTPUT_MAP[$key]}"
done

for key in "${CHANGED[@]:-}"; do
  [[ -n "$key" ]] && echo "  ~ $key: '${CURRENT_MAP[$key]}' -> '${OUTPUT_MAP[$key]}'"
done

for key in "${UNCHANGED[@]:-}"; do
  [[ -n "$key" ]] && echo "  = $key"
done
set -u

if [[ "$DRY_RUN" == "true" ]]; then
  echo
  echo "Dry-run complete. No GitHub variables were modified."
  exit 0
fi

for key in "${!OUTPUT_MAP[@]}"; do
  if gh api "/repos/$REPO/actions/variables/$key" >/dev/null 2>&1; then
    if ! gh api --method PATCH "/repos/$REPO/actions/variables/$key" -f name="$key" -f value="${OUTPUT_MAP[$key]}" >/dev/null; then
      FAILED+=("$key")
    fi
  else
    if ! gh api --method POST "/repos/$REPO/actions/variables" -f name="$key" -f value="${OUTPUT_MAP[$key]}" >/dev/null; then
      FAILED+=("$key")
    fi
  fi
done

set +u
if [[ ${#FAILED[@]:-0} -gt 0 ]]; then
  echo
  echo "Failed to update ${#FAILED[@]} variable(s): ${FAILED[*]}" >&2
  set -u
  exit 1
fi
set -u

echo
echo "Variable sync complete."
