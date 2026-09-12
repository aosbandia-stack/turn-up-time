# Security boundary

What Turn Up Time actually protects, what it only makes expensive, and what it
does not protect at all. Read this before enabling unattended execution.

This document exists because two mechanisms were being described in stronger
terms than they could support. Both are recorded below with the exact
reproduction, so nobody has to take the correction on trust.

## The one sentence that matters

**Turn Up Time is not an OS sandbox.** Every control here is an application-level
control. A process running under the owner's own OS account can edit the runtime,
the validators, the ledger, the journal and the trust file directly. Nothing in
this repository changes that, and no amount of signing changes it either.

What the controls do buy: a worker cannot *quietly* do those things. State moves
through a journal, evidence is content-addressed, and gates need a signature the
runtime cannot mint. An attacker must tamper with protected files rather than
simply ask the runtime nicely — and tampering is what an operator can detect,
back up against, and put file permissions in front of.

## Corrected claim 1 — the trust root

**Claimed:** "The controller reads `~/.claude/turn-up-time-trust.json` using its
own fixed home." **Was:** false.

`verify_approval` resolved the path with `Path.home()`, which expands `$HOME` on
POSIX and `%USERPROFILE%` on Windows. Any caller sets those on a child process.
Reproduced end to end: generate a keypair, write a trust file naming it
`"Owner"` with every gate, point `HOME` at its directory, and pass
`--approved-by "Owner"`. A forged `RELEASE` approval verified and returned
`"Owner"`. No protected file was modified. One environment variable defeated
every human gate.

**Now:** the account home is resolved from the POSIX password database
(`pwd.getpwuid(os.getuid()).pw_dir`) or the Windows process token
(`SHGetKnownFolderPath(FOLDERID_Profile)`). Neither is settable by an
environment variable. `TURN_UP_TIME_TRUST_FILE` may name an explicit path so the
trust file can live somewhere protected, but the runtime refuses it when the
file's permissions grant write to the account running the controller.

**Limits, stated plainly.** The writability probe reads mode bits and ownership
rather than calling `os.access`, because `os.access` honours the superuser
bypass and reports every file as writable to root — which would have made the
check a no-op exactly where the stakes are highest. Even so: an account that can
`chmod` the file can make it writable, edit it, and restore the mode. Under a
single OS account this is a speed bump and an audit signal, not a boundary. On
Windows the probe reflects the read-only attribute and does not consult ACLs.

Regression tests: `runtime/tests/test_trust_root.py`.

## Corrected claim 2 — code identity

`workspace.build_identity()` enumerates the tree with
`git ls-files --cached --others --exclude-standard`. That flag honours
`.git/info/exclude`, and `.git/` is never enumerated.

Reproduced: plant a file, observe the identity change, append its name to
`.git/info/exclude`, observe the identity return to the **byte-identical**
baseline while the file remains on disk and executable. The same trick hides a
git worktree nested inside the repository root, which otherwise makes
`build_identity` fail closed.

**Therefore: treat `build_identity` as a correctness mechanism, not a tamper
detector.** It reliably answers "is this the same tree I recorded?" for a
cooperating operator — catching a stale receipt, an uncommitted edit, a
mismatched build. It does not answer "has a hostile process hidden code here?",
and binding it into an approval does not make it answer that.

This is not currently fixed. Fixing it means either refusing to run when
`.git/info/exclude` is non-empty, or enumerating independently of git's exclude
machinery. Both have costs, and neither closes the same-account problem beneath
it.

## Workspace isolation

A git worktree is **not** a security boundary. It is a way to keep concurrent
work from colliding and to keep the main checkout's code identity stable. A
worker with a shell can leave its worktree by absolute path.

Worktrees must be created **outside** `repo_root`. Inside, they make
`build_identity` raise `unsupported code entry`, which blocks every approval
request and every transition into `INTEGRATION`, `CLOSEOUT` and `RELEASE`. A
clean worktree outside the repository at the same `HEAD` produces a
byte-identical identity and leaves the main checkout's identity untouched.

## Credentials

Local workers run under the same OS account as the controller. A sibling
process's environment is readable through `/proc/<pid>/environ` on Linux where
`ptrace_scope` does not prevent it. A per-provider credential allowlist reduces
what is **passed** to a worker; it creates no isolation between workers, and a
worker that wants another worker's environment can generally read it.

Do not mount production credentials into a coding worker. Where a provider's
authentication is host-managed rather than an environment variable, per-worker
credential scoping is not achievable locally at all — say so rather than
implying otherwise.

## Verification independence

`evaluator_id` is a free-form string. A label claiming independence is not
evidence of independence. What the controller can establish from facts it holds
itself is limited to: the evaluator ran under a different spawn than the
builder, and in a different workspace. Anything stronger — a different model or
provider family — is an assertion recorded by the controller, not a property it
verifies. A deterministic grader is the only genuinely checkable case, because
the result can be recomputed and compared.

## What still has no control

- Coordinated edits to the ledger and its journal together.
- The event log is bound into no approval.
- `complete_spawn` accepts an outcome with no binding to an observed exit status.
- `spawn_log` carries no attempt epoch, so a replaced worker's late result is
  indistinguishable from a live one.
- No redaction exists anywhere in logging or evidence.

These are recorded so they are not mistaken for solved problems.

## The same defect, a second place: the project validator

`validation._validator_candidates()` derived its installed fallback from
`Path.home() / ".claude"`. Repointing `HOME` therefore made the runtime
discover a planted `validate_project.py` — and a validator the caller chose is
not validation. Measured: with `HOME` repointed, the fallback candidate
resolved into the planted directory and the planted file was found.

Severity is lower than the trust-root case for one reason only: the in-repo
validator takes precedence when it exists, so exploitation first requires
removing `<repo>/.claude/scripts/validate_project.py` — and `build_identity`
records a removed tracked file as `DELETED`, so that step is visible.

**Now:** the fallback resolves through the same account-derived home as the
trust file. `TURN_UP_TIME_CLAUDE_HOME` is still honoured, because the installed
deployment depends on it; it is therefore **trust-relevant configuration**, not
something a worker may be allowed to set. A supervisor must not pass it through
to a worker, and must not let a worker choose it.

Regression tests: `test_home_does_not_select_the_project_validator` and
`test_explicit_claude_home_still_selects_the_validator`.

## A measured result worth keeping

A nested Claude Code worker was bisected against its environment: greedy
cumulative removal reached the **empty set**, and `env -i claude -p` with a file
-writing task still completed. Provider authentication here is host-managed
rather than environment-borne, so a worker can be launched with essentially no
inherited environment. That does not create isolation between same-account
processes — a sibling's `/proc/<pid>/environ` stays readable — but it removes
the argument for forwarding the parent environment by default.
