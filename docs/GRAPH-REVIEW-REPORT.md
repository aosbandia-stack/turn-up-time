# LangGraph release validation report

## Verdict

**GREEN — the v1.0.0 LangGraph runtime candidate passed all required repository, runtime, graph,
Windows installation, and cold-review workflows before merge.**

The validated PR head was `dd8a449e3082556018eebff948ae59950e1fa49b`. Its Git tree was
`b59c91441fd2c63969f5bf3ac4349254ef971061`. The signed squash commit on `main`,
`752521b58f8cdbc958f092c5fd3affdb0a4bef26`, contains that same Git tree, so the merged runtime source
is byte-for-byte the candidate that passed the checks below.

## Required workflows

| Workflow | Run | Verdict | Coverage |
|---|---:|---|---|
| Validate workflow | [#260](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708587) | GREEN | Repository contracts, seeded failures, deterministic cold review, capability and project CLIs, PowerShell 5.1 parsing, routing, destructive-command guard, install/uninstall safety |
| Cold graph review | [#6](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708602) | GREEN | Fresh graph-specific structural and behavioral checks |
| Validate graph runtime | [#41](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708593) | GREEN | Linux runtime suite and generated artifacts; Windows graph-enabled installation, installed-runtime verification, preservation checks, and uninstall |

## Linux graph-runtime evidence

The graph-runtime job completed all of the following successfully:

- installed the pinned runtime and development dependencies;
- compiled `runtime/src` and `runtime/tests`;
- ran the complete runtime test suite;
- validated the executable topology;
- regenerated Mermaid and JSON topology artifacts;
- validated the generated JSON against the workflow-graph schema;
- confirmed the committed generated artifacts were current.

## Windows evidence

Windows PowerShell 5.1 completed all of the following successfully:

- parsed every PowerShell file;
- exercised the dry-run installer without creating a manifest;
- installed with `-EnableGraphRuntime` using Python 3.12;
- created and recorded the isolated runtime virtual environment;
- validated the installed topology through the installed wrapper;
- preserved unrelated hooks, permission deny rules, and the existing notification hook;
- preserved a singular Turn Up Time router registration;
- removed the owned runtime and manifest during a clean uninstall.

## Corrective findings closed

The final repair closed the defects found in the incomplete pre-release branch:

- added missing package, state, event, topology, ledger, and validation modules;
- made `topology.py` the sole executable stage-and-edge authority;
- added atomic ledger transitions and idempotent append-only events;
- added human-gate and evidence-delta enforcement;
- added checkpoint/ledger drift rejection;
- added deterministic topology rendering and committed generated artifacts;
- implemented `-EnableGraphRuntime` and runtime ownership recording;
- implemented hash-safe graph runtime removal and restoration;
- corrected release-stage prerequisite ordering;
- corrected the deterministic reviewer’s schema inventory;
- pinned `aiosqlite` below the incompatible 0.22 line;
- corrected the Windows Python-version probe for PowerShell 5.1 native-command quoting.

## Public-core boundary

The reviewed tree contains the reusable Turn Up Time core. Company-specific providers, Taggy logic,
private evidence, credentials, user-specific Windows paths, and internal company domains were not
added to the public repository.

## Limits

- This report covers technical correctness and release mechanics, not business ROI.
- The remaining operational proof is a real Tier C pilot with cycle-time, repair, cost, and finding
  measurements.
- The cold reviews were deterministic programs. They are not an independent Claude-model judgment.
  No fresh external-model review was run during this corrective release, and no such claim is made.
