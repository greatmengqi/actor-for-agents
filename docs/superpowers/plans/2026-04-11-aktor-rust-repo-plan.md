# aktor Rust Repo Bootstrap — Implementation Plan

**Spec**: [`../specs/2026-04-11-aktor-rust-repo-design.md`](../specs/2026-04-11-aktor-rust-repo-design.md)
**Target**: `~/IdeaProjects/aktor/`
**Expected final state**: single git commit, `v0.0.1-scaffold` tag, all
validation steps pass.

---

## Step 1 — Initialize directory and git

```bash
cd ~/IdeaProjects
mkdir aktor
cd aktor
git init -b main
```

**Validation**: `test -d ~/IdeaProjects/aktor/.git`

## Step 2 — Write license files

- `LICENSE` — multi-license overview (§7, §4.4 of spec)
- `LICENSE-BSL` — BSL 1.1 full text with aktor exhibit (§4.2)
- `LICENSE-APACHE` — Apache License 2.0 full text with copyright boilerplate

**Validation**: three files exist, each ≥ 50 lines.

## Step 3 — Write workspace root config files

- `Cargo.toml` — `[workspace]` + `[workspace.package]` + `[workspace.dependencies]`
  + `[workspace.lints]` + `[profile.release]` per §5.2
- `rust-toolchain.toml` — pin channel `1.85`, components `rustfmt, clippy`
- `rustfmt.toml` — edition 2024, max_width 100, StdExternalCrate group
- `clippy.toml` — `msrv = "1.85"`
- `.gitignore` — target, lock, IDE noise

**Validation**: `cargo metadata --no-deps` runs without error once crate
directories exist.

## Step 4 — Write governance files

- `README.md` — short landing page (§7.1)
- `CLAUDE.md` — Rust coding principles mirroring Python version (§7.2)
- `CHANGELOG.md` — Keep a Changelog format, `[Unreleased]` entry (§7.3)

## Step 5 — Write CI workflow

`.github/workflows/ci.yml` with two jobs:

1. `build` — checkout → rust-toolchain → fmt check → clippy → check → test → doc
2. `license-check` — bash assertions on symlink targets and members list

## Step 6 — Write five crate directories

For each of `core`, `flow`, `agents`, `moa`, `integrations`:

- `<crate>/Cargo.toml` — inherits workspace package/lints, declares license
- `<crate>/README.md` — one-paragraph purpose
- `<crate>/src/lib.rs` — public API skeleton per §6.X of spec

## Step 7 — Write examples and docs placeholders

- `examples/README.md` — "examples will be added later"
- `docs/README.md` — "documentation will be added later"

## Step 8 — Create 7 license symlinks

```bash
ln -s ../LICENSE-BSL      core/LICENSE
ln -s ../LICENSE-BSL      flow/LICENSE
ln -s ../LICENSE-BSL      agents/LICENSE
ln -s ../LICENSE-BSL      moa/LICENSE
ln -s ../LICENSE-APACHE   integrations/LICENSE
ln -s ../LICENSE-APACHE   examples/LICENSE
ln -s ../LICENSE-APACHE   docs/LICENSE
```

**Validation**: `readlink core/LICENSE` returns `../LICENSE-BSL`, etc.

## Step 9 — Validation gate (spec §9.1 acceptance criteria)

Run in order; any failure blocks commit:

```bash
cd ~/IdeaProjects/aktor
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo check --all-targets --all-features
cargo test --all-targets --all-features
cargo doc --no-deps --all-features
```

Also verify:

- `grep -r "async_trait" .` returns zero hits
- `grep -r "rust_core\|pyo3\|crossbeam" .` returns zero hits
- All 7 symlinks resolve (`readlink` checks)

If clippy pedantic/nursery flags anything on the skeleton that cannot be
reasonably fixed (e.g., `missing_errors_doc` on `todo!()` stubs), either:
- add a targeted `#[allow(...)]` with an inline comment explaining why, OR
- add a workspace-level `allow` in `[workspace.lints.clippy]`.

Prefer workspace-level allows over scattered inline allows.

## Step 10 — Bootstrap commit and tag

```bash
git add -A
git commit -m "chore: bootstrap aktor Rust workspace with multi-license architecture"
git tag v0.0.1-scaffold
```

**No `git remote add`. No `git push`. No `cargo publish`.**

## Step 11 — Final report

Report back to user:

- Commit hash
- File count (expected: 29 real + 7 symlinks)
- `cargo check` time
- Any clippy allows that were added (with reasoning)
- Next steps the user might want (remote push, first port PR, etc.)
