# Bash completion for bin/agent.

_CODEX_AGENT_COMPLETION_ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
)"

_codex_agent_types() {
  local dir
  for dir in "${_CODEX_AGENT_COMPLETION_ROOT}"/agents/*; do
    [[ -d "${dir}" \
      && -f "${dir}/AGENTS.md" \
      && -f "${dir}/config.toml" \
      && -f "${dir}/compose.override.yaml" ]] || continue
    basename "${dir}"
  done
}

_codex_agent_instances() {
  local file
  for file in "${_CODEX_AGENT_COMPLETION_ROOT}"/instances/*/instance.env; do
    [[ -f "${file}" ]] || continue
    basename "$(dirname "${file}")"
  done
}

_codex_agent_complete() {
  local current command previous
  current="${COMP_WORDS[COMP_CWORD]}"
  command="${COMP_WORDS[1]:-}"
  previous="${COMP_WORDS[COMP_CWORD - 1]:-}"
  COMPREPLY=()

  if (( COMP_CWORD == 1 )); then
    mapfile -t COMPREPLY < <(
      compgen -W "create start attach shell logs stop down status list help" \
        -- "${current}"
    )
    return
  fi

  case "${command}" in
    create)
      case "${COMP_CWORD}" in
        2)
          mapfile -t COMPREPLY < <(
            compgen -W "$(_codex_agent_types)" -- "${current}"
          )
          ;;
        4)
          mapfile -t COMPREPLY < <(compgen -W "-e" -- "${current}")
          ;;
        5)
          if [[ "${previous}" == "-e" ]]; then
            compopt -o filenames 2>/dev/null || true
            if [[ -z "${current}" ]]; then
              COMPREPLY=(/)
            elif [[ "${current}" == /* ]]; then
              mapfile -t COMPREPLY < <(compgen -d -- "${current}")
            fi
          fi
          ;;
      esac
      ;;
    start|attach|shell|logs|stop|down|status)
      if (( COMP_CWORD == 2 )); then
        mapfile -t COMPREPLY < <(
          compgen -W "$(_codex_agent_instances)" -- "${current}"
        )
      fi
      ;;
  esac
}

complete -F _codex_agent_complete agent
