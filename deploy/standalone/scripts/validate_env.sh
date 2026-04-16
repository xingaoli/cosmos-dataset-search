#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

set -euo pipefail

LOG_PREFIX="[validate-env]"
ROOT_DIR="$(dirname "${BASH_SOURCE[0]}")/.."
ENV_FILE="${ROOT_DIR}/.env"
ENV_TEMPLATE="${ROOT_DIR}/.env.example"

log_info() {
  local message="$1"
  printf '%s[INFO] %s\n' "$LOG_PREFIX" "$message"
}

log_warn() {
  local message="$1"
  printf '%s[WARN] %s\n' "$LOG_PREFIX" "$message"
}

log_error() {
  local message="$1"
  printf '%s[ERROR] %s\n' "$LOG_PREFIX" "$message" >&2
}

fail() {
  local message="$1"
  log_error "$message"
  exit 1
}

mask_secret() {
  local value="$1"
  local length
  length=${#value}

  if (( length <= 8 )); then
    printf '********'
    return
  fi

  local prefix suffix
  prefix=${value:0:4}
  suffix=${value:length-4:4}
  printf '%s****%s' "$prefix" "$suffix"
}

check_required() {
  local var_name="$1"
  local value
  value=${!var_name-}

  if [[ -z "${value:-}" ]]; then
    fail "${var_name} is not set. Populate it in your .env file before continuing."
  fi
}

check_not_placeholder() {
  local var_name="$1"
  local placeholder="$2"
  local value
  value=${!var_name-}

  if [[ "$value" == "$placeholder" ]]; then
    fail "${var_name} is still set to the placeholder value (${placeholder}). Update it in your .env file."
  fi
}

check_directory_exists() {
  local var_name="$1"
  local value
  value=${!var_name-}

  if [[ ! -d "$value" ]]; then
    fail "${var_name} points to '${value}', but that directory does not exist. Create it or update the value."
  fi

  if [[ ! -r "$value" ]]; then
    fail "${var_name} points to '${value}', but it is not readable. Fix the permissions."
  fi

  if [[ ! -w "$value" ]]; then
    log_warn "${var_name} points to '${value}', but it is not writable."
  fi
}

check_integer() {
  local var_name="$1"
  local min_value="$2"
  local value
  value=${!var_name-}

  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    fail "${var_name} must be an integer. Current value: '${value}'."
  fi

  if (( value < min_value )); then
    fail "${var_name} must be greater than or equal to ${min_value}. Current value: ${value}."
  fi
}

check_log_level() {
  local var_name="$1"
  local allowed_values="$2"
  local value
  value=${!var_name-}

  if [[ -n "$value" ]]; then
    local match=false
    local level
    for level in $allowed_values; do
      if [[ "$value" == "$level" ]]; then
        match=true
        break
      fi
    done

    if [[ "$match" == false ]]; then
      fail "${var_name} must be one of ${allowed_values}. Current value: '${value}'."
    fi
  fi
}

check_cuda_devices() {
  local var_name="$1"
  local value
  value=${!var_name-}

  if [[ -z "$value" ]]; then
    fail "${var_name} is empty. Set it to the GPU device IDs that Milvus can use (e.g., 0 or 0,1)."
  fi

  if ! [[ "$value" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
    fail "${var_name} must be a comma-separated list of GPU indices (e.g., '0' or '0,1'). Current value: '${value}'."
  fi
}

check_uri() {
  local var_name="$1"
  local value
  value=${!var_name-}

  if ! [[ "$value" =~ ^https?:// ]]; then
    fail "${var_name} must start with http:// or https://. Current value: '${value}'."
  fi
}

check_docker_login() {
  local registry="$1"
  local docker_config="${HOME}/.docker/config.json"
  
  if [[ ! -f "$docker_config" ]]; then
    fail "Docker config not found at ${docker_config}. Run 'docker login ${registry}' first."
  fi
  
  # Check if registry is in docker config
  if ! grep -q "\"${registry}\"" "$docker_config" 2>/dev/null; then
    fail "Not logged in to ${registry}. Run 'docker login ${registry}' with your NGC API key."
  fi
  
  log_info "Docker authentication for ${registry} is configured."
}

log_info "Starting environment validation..."

if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${ENV_TEMPLATE}" ]]; then
    log_info "'.env' not found. Copying from template..."
    cp "${ENV_TEMPLATE}" "${ENV_FILE}"
    log_warn "Created a fresh .env from template. Please review and update placeholder values before re-running."
    exit 1
  else
    fail "'.env' file is missing and template '.env.example' not found at ${ROOT_DIR}."
  fi
fi

set -a
while IFS='=' read -r key value; do
  # Skip comments and empty lines
  [[ "$key" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$key" ]] && continue
  # Export valid KEY=VALUE pairs
  export "${key}=${value}"
done < <(grep -E '^[^#]' "${ENV_FILE}" | grep -E '^[A-Za-z_]=')
set +a

# Required values
check_required NVIDIA_API_KEY
check_required DATA_DIR
check_required AWS_ACCESS_KEY_ID
check_required AWS_SECRET_ACCESS_KEY
check_required COSMOS_EMBED_NIM_URI
check_required ALLOWED_PIPELINES

# Validate core values
check_not_placeholder NVIDIA_API_KEY "<your_api_key>"
check_not_placeholder DATA_DIR "/path/to/your/data"

log_info "NVIDIA_API_KEY detected: $(mask_secret "$NVIDIA_API_KEY")"
log_info "Data directory: ${DATA_DIR}"
log_warn "Note: DATA_DIR existence/permissions will be verified when containers mount it."

# Verify NGC docker login
check_docker_login "nvcr.io"

# Numeric validations
check_integer GUNICORN_PORT 1
check_integer GUNICORN_WORKERS 1
check_integer GUNICORN_TIMEOUT 30
check_integer MAX_DOCS_PER_UPLOAD 1
check_integer COSMOS_EMBED_GPUS 0
check_integer NIM_TRITON_LOG_VERBOSE 0

if (( NIM_TRITON_LOG_VERBOSE > 1 )); then
  log_warn "NIM_TRITON_LOG_VERBOSE is greater than 1. High verbosity can produce large logs."
fi

check_cuda_devices MILVUS_CUDA_VISIBLE_DEVICES

# URI validations
check_uri COSMOS_EMBED_NIM_URI

if [[ -n "${AWS_ENDPOINT_URL-}" ]]; then
  check_uri AWS_ENDPOINT_URL
fi

if [[ -n "${CDS_API_URL-}" ]]; then
  check_uri CDS_API_URL
fi

if [[ -n "${CDS_CDN_URL-}" ]]; then
  check_uri CDS_CDN_URL
fi

if [[ -n "${CDS_UI_URL-}" ]]; then
  check_uri CDS_UI_URL
fi

# Log level validations
check_log_level NIM_LOG_LEVEL "DEFAULT INFO WARNING ERROR"
check_log_level VISUAL_SEARCH_LOG_LEVEL "DEBUG INFO WARNING ERROR CRITICAL"

# AWS defaults (acceptable for LocalStack)
if [[ "$AWS_ACCESS_KEY_ID" == "test" && "$AWS_SECRET_ACCESS_KEY" == "test" ]]; then
  log_info "Using AWS test credentials (expected for LocalStack)."
fi

# Check and configure NIM cache directory
NIM_CACHE_DIR="${HOME}/.cache/nim"

if [[ ! -d "$NIM_CACHE_DIR" ]]; then
  log_info "NIM cache directory does not exist. Creating: ${NIM_CACHE_DIR}"
  mkdir -p "$NIM_CACHE_DIR"
  chmod 777 "$NIM_CACHE_DIR"
  log_info "Created NIM cache directory with 777 permissions."
else
  # Directory exists, check permissions
  CURRENT_PERMS=$(stat -c "%a" "$NIM_CACHE_DIR" 2>/dev/null || stat -f "%OLp" "$NIM_CACHE_DIR" 2>/dev/null)
  
  if [[ "$CURRENT_PERMS" != "777" ]]; then
    log_warn "NIM cache directory exists but has incorrect permissions (${CURRENT_PERMS}). Updating to 777."
    chmod 777 "$NIM_CACHE_DIR"
    log_info "Updated NIM cache directory permissions to 777."
  else
    log_info "NIM cache directory exists with correct permissions (777)."
  fi
fi

log_info "Environment validation completed successfully."


