"""Create/verify a host-owned catalog of already inspected retained runtime assets.

Does not download, execute providers, change global configuration, or install packages.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import stat
from pathlib import Path
import time

EXCLUSIONS = [".git"]

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def ref(path):
    return {"path": Path(path).resolve().as_posix(), "sha256": digest(path)}

def enumerate_files(root, scopes, exclusions=None):
    root = Path(root)
    exclusions = EXCLUSIONS if exclusions is None else exclusions
    if exclusions not in ([".git"], [".git", "Lib/site-packages"]):
        raise ValueError("Unsupported exclusion")
    result = {}
    for scope in scopes:
        relative = Path(scope)
        if relative.is_absolute() or ".." in relative.parts or ":" in scope or "\\" in scope:
            raise ValueError("Unsafe managed path")
        start = root / relative
        if not start.exists():
            raise ValueError(f"Missing managed path: {scope}")
        pending = [start]
        while pending:
            path = pending.pop()
            if path.relative_to(root).as_posix() == "Lib/site-packages" and "Lib/site-packages" in exclusions:
                continue
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
                raise ValueError(f"Linked runtime asset: {path}")
            if stat.S_ISDIR(info.st_mode):
                if path.name not in EXCLUSIONS:
                    with os.scandir(path) as entries:
                        pending.extend(Path(entry.path) for entry in entries)
            elif stat.S_ISREG(info.st_mode):
                name = path.relative_to(root).as_posix()
                key = name.casefold()
                if key in result:
                    raise ValueError(f"Overlapping/colliding runtime asset: {name}")
                result[key] = {"path": name}
    entries = sorted(result.values(), key=lambda x: x["path"].casefold())
    # A small bounded batch avoids both serial filesystem latency and unbounded futures.
    with ThreadPoolExecutor(max_workers=4) as executor:
        for offset in range(0, len(entries), 128):
            batch = entries[offset:offset + 128]
            hashes = executor.map(digest, (root / entry["path"] for entry in batch))
            for entry, value in zip(batch, hashes):
                entry["sha256"] = value
    return entries

def write_inventory(path, root, scopes, runtime_id, exclusions=None):
    exclusions = EXCLUSIONS if exclusions is None else exclusions
    data = {"schema_version": 1, "runtime_id": runtime_id, "root": Path(root).as_posix(),
            "managed_paths": scopes, "exclusions": exclusions, "files": enumerate_files(root, scopes, exclusions)}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data

def verify_inventory(reference, runtime_id, *, interpreter=False):
    if digest(reference["path"]) != reference["sha256"]:
        raise ValueError("Inventory hash mismatch")
    data = json.loads(Path(reference["path"]).read_text())
    expected = [".git", "Lib/site-packages"] if interpreter else EXCLUSIONS
    if data["runtime_id"] != runtime_id or data["exclusions"] != expected:
        raise ValueError("Inventory identity mismatch")
    if enumerate_files(data["root"], data["managed_paths"], data["exclusions"]) != data["files"]:
        raise ValueError("Runtime inventory drift or unlisted assets")
    return len(data["files"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "verify"])
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()
    source = Path(args.workflow).resolve()
    runtime = source / ".claude/runtime/provider-tools"
    install = runtime / "runtime-profiles/gauntlet-tools-v1"
    metadata = runtime / "install-metadata/gauntlet-tools-v1"
    metadata.mkdir(parents=True, exist_ok=True)
    catalog_path = metadata / "runtime-catalog.json"
    runtime_id = "gauntlet-tools-win32-20261010-v1"
    started = time.monotonic()
    if args.command == "prepare":
        scopes = ["rea-source", "serena-source", "serena-venv", "serena-home/language_servers/static/TypeScriptLanguageServer/ts-lsp", "runtime-profiles/gauntlet-tools-v1"]
        write_inventory(metadata / "inventory.json", runtime, scopes, runtime_id)
        python_base = Path("C:/Users/Bandi/AppData/Local/Programs/Python/Python314")
        # -I and the inventoried pyvenv.cfg (include-system-site-packages=false)
        # make the base install's unrelated site-packages unreachable.
        write_inventory(metadata / "python-inventory.json", python_base, ["."], runtime_id, [".git", "Lib/site-packages"])
        native_codex = Path("C:/Users/Bandi/AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe")
        generation = source / ".claude/runtime/provider-candidate/provider-generations/gauntlet-20261010-v4/generation.json"
        data = {"schema_version": 1, "runtime_id": runtime_id, "platform": "local:win32",
                "provider_generation": {"generation_id": "gauntlet-20261010-v4", "metadata_sha256": digest(generation)},
                "codex": {"version": "0.162.1", "executable": ref(native_codex)},
                "inventory": ref(metadata / "inventory.json"),
                "providers": {
                    "rea": {"profile": "rea-javascript-v1", "source_ref": "bddddccdee3129d0b1b11e32b751be2b6d501c23", "version": "6.3.0", "node": ref("C:/Program Files/nodejs/node.exe"), "entrypoint": ref(runtime / "rea-source/scripts/rea.mjs")},
                    "serena": {"profile": "serena-readonly-v1", "source_ref": "1de556f71569f3acfc0743e526dd60aca40a545e", "version": "2.0.0.dev0", "python": ref(runtime / "serena-venv/Scripts/python.exe"), "launcher": ref(install / "serena_readonly_launcher.py"), "context": ref(install / "serena-readonly.yml"), "home_root": (runtime / "project-state").as_posix(), "interpreter_inventory": ref(metadata / "python-inventory.json")},
                    "context7": {"profile": "context7-public-v1", "source_ref": "522c4db4fa2e1e31f1b320f09fa8c8fab376987a", "endpoint": "https://mcp.context7.com/mcp", "auth": "anonymous"}}}
        catalog_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    data = json.loads(catalog_path.read_text())
    counts = [verify_inventory(data["inventory"], data["runtime_id"]), verify_inventory(data["providers"]["serena"]["interpreter_inventory"], data["runtime_id"], interpreter=True)]
    for obj in [data["codex"]["executable"], data["providers"]["rea"]["node"], data["providers"]["rea"]["entrypoint"], *[data["providers"]["serena"][k] for k in ("python", "launcher", "context")]]:
        if digest(obj["path"]) != obj["sha256"]:
            raise ValueError("Executable/profile drift")
    print(json.dumps({"status": "PASS", "catalog": ref(catalog_path), "asset_counts": counts, "elapsed_seconds": round(time.monotonic()-started, 3)}))

if __name__ == "__main__":
    main()
