"""Trusted retained runtime profile; no project-owned Serena settings are loaded."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

TOOLS = ["get_symbols_overview", "find_symbol", "find_referencing_symbols"]

def plain_path(value, *, directory=True):
    path = Path(value)
    if not path.is_absolute() or str(path).startswith("\\\\"):
        raise ValueError("Absolute local path required")
    for part in [path, *path.parents]:
        if part.exists() and (part.is_symlink() or getattr(part, "is_junction", lambda: False)()):
            raise ValueError("Reparse paths are forbidden")
    if directory and not path.is_dir():
        raise ValueError("Existing directory required")
    return path.resolve()

def prepare(project, context, state_root):
    project = plain_path(project)
    context = plain_path(context, directory=False)
    runtime = Path(__file__).resolve().parents[2]
    if context != Path(__file__).with_name("serena-readonly.yml"):
        raise ValueError("Only the installed trusted context is accepted")
    state_root = plain_path(state_root)
    if state_root != runtime / "project-state":
        raise ValueError("Unexpected mutable state root")
    if project == state_root or state_root in project.parents or project in state_root.parents:
        raise ValueError("Project and runtime state must be separate")
    node = Path("C:/Program Files/nodejs/node.exe")
    server = runtime / "serena-home/language_servers/static/TypeScriptLanguageServer/ts-lsp/node_modules/typescript-language-server/lib/cli.mjs"
    if not node.is_file() or not server.is_file():
        raise ValueError("Qualified TypeScript runtime is unavailable; installation is not automatic")
    key = hashlib.sha256(str(project).casefold().encode()).hexdigest()[:16]
    home = Path(tempfile.mkdtemp(prefix=key + "-", dir=state_root))
    project_state = home / "project"
    project_state.mkdir()
    config = {"language_backend": "LSP", "agent_interface": "tools", "gui_log_window": False,
              "web_dashboard": False, "web_dashboard_open_on_launch": False,
              "project_serena_folder_location": str(project_state), "trusted_project_path_patterns": [],
              "fixed_tools": TOOLS, "projects": [],
              "ls_specific_settings": {"typescript": {"ls_base_cmd": [str(node), str(server)]}}}
    project_config = {"project_name": "bound-" + key, "languages": ["typescript"], "read_only": True,
                      "fixed_tools": TOOLS, "agent_interface": "tools", "project_activation_command": None,
                      "ignored_paths": ["**/node_modules/**", "**/.git/**"], "ignore_all_files_in_gitignore": True}
    (home / "serena_config.yml").write_text(json.dumps(config), encoding="utf-8")
    (project_state / "project.yml").write_text(json.dumps(project_config), encoding="utf-8")
    (home / "binding.json").write_text(json.dumps({"project": str(project), "read_only": True, "tools": TOOLS}), encoding="utf-8")
    return project, context, home

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--state-root", required=True)
    args = parser.parse_args()
    project, context, home = prepare(args.project, args.context, args.state_root)
    for key in ["PYTHONPATH", "PYTHONSTARTUP", "NODE_OPTIONS", "NODE_PATH"]:
        os.environ.pop(key, None)
    os.environ.update(SERENA_HOME=str(home), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    from serena.cli import top_level
    top_level(args=["start-mcp-server", "--project", str(project), "--context", str(context),
                    "--mode", "planning", "--agent-interface", "tools", "--enable-web-dashboard", "false",
                    "--open-web-dashboard", "false", "--enable-gui-log-window", "false", "--log-level", "WARNING"])

if __name__ == "__main__":
    main()
