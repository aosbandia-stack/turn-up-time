# Retained external tool runtime

The host attachment adapter consumes the promoted `capabilities/runtime-catalog.json`.
The catalog binds the exact provider generation ID and metadata SHA256, Codex 0.162.1
executable, provider profiles, full installed runtime inventory, and base Python inventory.
It contains no credentials and accepts no worker-authored commands or endpoints.

`scripts/tool_runtime_catalog.py prepare --workflow <checkout>` records already reviewed
local runtimes. It does not download or activate tools. `verify` rehashes all declared
assets and fails on changed, missing, linked, colliding, or unlisted files. Native launch
and promotion independently validate the strict schemas and the same inventories.
Inventory scopes are exact relative paths. Only `.git` directories are excluded from
the tool payload; Python bytecode is fully inventoried. The base interpreter inventory
covers its entire root and excludes exactly `Lib/site-packages`, which is unreachable
because the inventoried venv configuration disables system site packages and the host
launches Python with `-I -B`. New parent files, including `Lib/sitecustomize.py` and root
zip/DLL files, are still detected. Project state, logs, download caches and unrelated runtimes are
outside the declared scopes. Never execute unlisted files from those state directories.

The retained runtime ID is `gauntlet-tools-win32-20261010-v1`. Its payload stays under
the approved workflow checkout's `.claude/runtime/provider-tools`; do not move or delete
it while any promoted catalog references it. Existing Windows virtual environments are
not relocatable by copying. Keep previous catalogs and payloads for rollback. The base
Python installation and system Node/Codex remain host prerequisites: an upgrade may
invalidate the old catalog, which must fail closed until a newly reviewed inventory is
qualified. Retention of a catalog does not promise that upgraded external interpreters
remain usable.

REA exposes only `analyze_javascript_application` and `inspect_analysis_view` during
DISCOVERY. Serena exposes only overview, symbol lookup, and caller lookup in DISCOVERY,
BUILD, and CLOSEOUT. Context7 exposes only library resolution and documentation queries
in DISCOVERY and BUILD, against `https://mcp.context7.com/mcp`, anonymously. The controller
authenticates the exact task role; the adapter intersects selected capabilities with
these existing registry stages. No new role permissions are invented.

The installed Serena launcher receives only an authenticated project root, installed
context and fixed state root. It creates a unique external home/project state directory,
forces read-only mode and the three tools, disables UI and project activation commands,
and uses the pinned installed TypeScript server through its supported `ls_base_cmd`
setting. Project-owned `.serena` configuration is ignored. TypeScript/JavaScript is the
qualified language scope; another language needs separate dependency qualification.

Standalone smoke, configured availability and actual Bandia worker use are distinct.
Only worker transcript invocation, useful output and independently checked consumption
can establish application. Context7's inspected Playwright 1.59.0 docs do not prove exact
1.59.1 coverage. 21st remains blocked until its supported official login completes.
