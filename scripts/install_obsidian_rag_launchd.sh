#!/usr/bin/env bash
set -euo pipefail

readonly LABEL="com.hongstr.obsidian_rag"
readonly PLIST_TEMPLATE="launchd/com.hongstr.obsidian_rag.plist"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

export PATH="${DEFAULT_PATH}"

main() {
  local repo_root uid launch_agents_dir log_dir plist_src plist_dest out_log err_log

  repo_root="$(git rev-parse --show-toplevel)"
  cd "${repo_root}"

  uid="$(id -u)"
  launch_agents_dir="${HOME}/Library/LaunchAgents"
  log_dir="${HOME}/Library/Logs/hongstr"
  plist_src="${repo_root}/${PLIST_TEMPLATE}"
  plist_dest="${launch_agents_dir}/${LABEL}.plist"
  out_log="${log_dir}/obsidian_rag.out.log"
  err_log="${log_dir}/obsidian_rag.err.log"

  mkdir -p "${launch_agents_dir}" "${log_dir}"
  touch "${out_log}" "${err_log}"

  sed \
    -e "s|__REPO_ROOT__|${repo_root}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "${plist_src}" > "${plist_dest}"

  plutil -lint "${plist_dest}"

  launchctl bootout "gui/${uid}/${LABEL}" >/dev/null 2>&1 || true
  launchctl bootout "gui/${uid}" "${plist_dest}" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/${uid}" "${plist_dest}"
  launchctl kickstart -k "gui/${uid}/${LABEL}"

  echo "install_obsidian_rag_launchd: installed ${plist_dest}"
  launchctl print "gui/${uid}/${LABEL}"
  echo
  echo "== tail ${out_log} =="
  tail -n 50 "${out_log}" || true
  echo
  echo "== tail ${err_log} =="
  tail -n 50 "${err_log}" || true
}

main "$@"
