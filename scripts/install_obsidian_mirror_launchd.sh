#!/usr/bin/env bash
set -euo pipefail

readonly LABEL="com.hongstr.obsidian_mirror"
readonly PLIST_TEMPLATE="launchd/com.hongstr.obsidian_mirror.plist"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

export PATH="${DEFAULT_PATH}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/install_obsidian_mirror_launchd.sh install
  bash scripts/install_obsidian_mirror_launchd.sh uninstall
  bash scripts/install_obsidian_mirror_launchd.sh reload
  bash scripts/install_obsidian_mirror_launchd.sh status
EOF
}

render_plist() {
  local repo_root="$1"
  local plist_src="$2"
  local plist_dest="$3"
  sed \
    -e "s|__REPO_ROOT__|${repo_root}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "${plist_src}" > "${plist_dest}"
  plutil -lint "${plist_dest}" >/dev/null
}

do_install() {
  local repo_root="$1"
  local uid="$2"
  local launch_agents_dir="$3"
  local plist_src="$4"
  local plist_dest="$5"
  local out_log="$6"
  local err_log="$7"

  mkdir -p "${launch_agents_dir}" "$(dirname "${out_log}")"
  touch "${out_log}" "${err_log}"
  render_plist "${repo_root}" "${plist_src}" "${plist_dest}"

  launchctl bootout "gui/${uid}/${LABEL}" >/dev/null 2>&1 || true
  launchctl bootout "gui/${uid}" "${plist_dest}" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/${uid}" "${plist_dest}"
  launchctl kickstart -k "gui/${uid}/${LABEL}"

  echo "install_obsidian_mirror_launchd: installed ${plist_dest}"
  launchctl print "gui/${uid}/${LABEL}" || true
  echo
  echo "== tail ${out_log} =="
  tail -n 80 "${out_log}" || true
  echo
  echo "== tail ${err_log} =="
  tail -n 80 "${err_log}" || true
}

do_uninstall() {
  local uid="$1"
  local plist_dest="$2"
  launchctl bootout "gui/${uid}/${LABEL}" >/dev/null 2>&1 || true
  launchctl bootout "gui/${uid}" "${plist_dest}" >/dev/null 2>&1 || true
  rm -f "${plist_dest}"
  echo "install_obsidian_mirror_launchd: removed ${plist_dest}"
}

do_status() {
  local uid="$1"
  launchctl print "gui/${uid}/${LABEL}" || true
}

main() {
  local action repo_root uid launch_agents_dir plist_src plist_dest out_log err_log
  action="${1:-install}"

  case "${action}" in
    install|uninstall|reload|status)
      ;;
    *)
      usage
      return 2
      ;;
  esac

  repo_root="$(git rev-parse --show-toplevel)"
  cd "${repo_root}"

  uid="$(id -u)"
  launch_agents_dir="${HOME}/Library/LaunchAgents"
  plist_src="${repo_root}/${PLIST_TEMPLATE}"
  plist_dest="${launch_agents_dir}/${LABEL}.plist"
  out_log="${repo_root}/_local/logs/launchd_obsidian_mirror.out.log"
  err_log="${repo_root}/_local/logs/launchd_obsidian_mirror.err.log"

  case "${action}" in
    install)
      do_install "${repo_root}" "${uid}" "${launch_agents_dir}" "${plist_src}" "${plist_dest}" "${out_log}" "${err_log}"
      ;;
    uninstall)
      do_uninstall "${uid}" "${plist_dest}"
      ;;
    reload)
      do_uninstall "${uid}" "${plist_dest}"
      do_install "${repo_root}" "${uid}" "${launch_agents_dir}" "${plist_src}" "${plist_dest}" "${out_log}" "${err_log}"
      ;;
    status)
      do_status "${uid}"
      ;;
  esac
}

main "$@"
