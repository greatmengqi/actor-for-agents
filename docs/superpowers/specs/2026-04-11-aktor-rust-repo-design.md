# aktor — Native Rust Actor Framework: Repository Bootstrap Design

**Status**: Draft
**Date**: 2026-04-11
**Author**: brainstorming session
**Scope**: Create a new standalone git repository `aktor` as the native Rust counterpart
to the Python `everything-is-an-actor` framework, with a multi-license architecture
mirroring the Python repository.

---

## 1. Goal & Non-Goals

### 1.1 Goal

Bootstrap a new git repository at `~/IdeaProjects/aktor/` containing:

1. A Cargo workspace with five member crates (`aktor-core`, `aktor-flow`, `aktor-agents`,
   `aktor-moa`, `aktor-integrations`) mirroring the Python repository's layer structure.
2. A multi-license distribution matching the Python counterpart:
   BSL 1.1 for core layers, Apache 2.0 for integrations / examples / docs.
3. End-to-end type/trait skeletons per crate (public API signatures with `todo!()`
   bodies or minimal placeholder implementations), such that
   `cargo check --all-targets --all-features` passes cleanly on all crates.
4. Tooling baseline: `rust-toolchain.toml`, `rustfmt.toml`, `clippy.toml`,
   GitHub Actions CI, and editor/SCM config.
5. Governance documents: `README.md`, `CLAUDE.md` (Rust-specific coding principles),
   `CHANGELOG.md`, and root `LICENSE` overview.

The deliverable is a **scaffold**, not a port. No Python-version logic is
translated in this phase; that work happens in subsequent plans.

### 1.2 Explicit Non-Goals

- **Not** a port of Python business logic. All method bodies are `todo!()` or
  minimal placeholders.
- **Not** a PyO3 extension or Python-interop layer. `aktor` is standalone Rust.
- **Not** a reuse of the existing `rust_core/` subdirectory in the Python repo.
  `rust_core/` is a synchronous `crossbeam-channel` + `parking_lot` benchmarking
  binding bridged to Python; `aktor` is a tokio-based fully async native
  framework. They share no code and serve different purposes. This distinction
  is documented in `aktor/CLAUDE.md` under "Non-goals".
- **Not** published to crates.io in this phase. Initial version is `0.0.1`,
  explicitly pre-alpha, no publish step.
- **Not** pushed to any git remote in this phase. Remote creation is a
  user-driven decision deferred to a follow-up step.

---

## 2. Repository Location & Identity

- **Directory**: `~/IdeaProjects/aktor/` (sibling to `actor-for-agents/`)
- **Crate family**: `aktor-*` (prefixed to be publishable to crates.io)
- **Licensor**: `aktor contributors`
- **Licensed Work name** (for BSL exhibit): `aktor`
- **Copyright year**: 2026
- **BSL Change Date**: **2030-04-11** (today + 4 years, matching Python repo's
  4-year BSL-to-Apache conversion window)
- **Change License**: Apache License, Version 2.0

Note on crate name availability: a dormant `aktor` crate (last published ~2018)
exists on crates.io. This does not block scaffolding. Future publication may
require reserving `aktor-*` crates individually or renaming. This risk is
documented in `CHANGELOG.md` and does not affect the bootstrap.

---

## 3. Workspace Structure

### 3.1 Directory Layout

Mirrors the Python repository's top-level layer directories (Approach B from
brainstorming):

```
aktor/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── Cargo.toml                      # workspace root, shared deps/lints/profile
├── rust-toolchain.toml             # pinned channel + MSRV
├── rustfmt.toml                    # formatting
├── clippy.toml                     # lint thresholds
├── README.md
├── CLAUDE.md                       # Rust coding principles (mirrors Python CLAUDE.md)
├── CHANGELOG.md
├── LICENSE                         # multi-license overview (mirrors Python LICENSE)
├── LICENSE-BSL                     # BSL 1.1 full text
├── LICENSE-APACHE                  # Apache 2.0 full text
│
├── core/                           # [BSL 1.1] aktor-core
│   ├── Cargo.toml
│   ├── LICENSE -> ../LICENSE-BSL   # symlink
│   ├── README.md
│   └── src/lib.rs
│
├── flow/                           # [BSL 1.1] aktor-flow
│   ├── Cargo.toml
│   ├── LICENSE -> ../LICENSE-BSL   # symlink
│   ├── README.md
│   └── src/lib.rs
│
├── agents/                         # [BSL 1.1] aktor-agents
│   ├── Cargo.toml
│   ├── LICENSE -> ../LICENSE-BSL   # symlink
│   ├── README.md
│   └── src/lib.rs
│
├── moa/                            # [BSL 1.1] aktor-moa
│   ├── Cargo.toml
│   ├── LICENSE -> ../LICENSE-BSL   # symlink
│   ├── README.md
│   └── src/lib.rs
│
├── integrations/                   # [Apache 2.0] aktor-integrations
│   ├── Cargo.toml
│   ├── LICENSE -> ../LICENSE-APACHE
│   ├── README.md
│   └── src/lib.rs
│
├── examples/                       # [Apache 2.0] non-crate directory
│   ├── LICENSE -> ../LICENSE-APACHE
│   └── README.md                   # placeholder
│
└── docs/                           # [Apache 2.0] non-crate directory
    ├── LICENSE -> ../LICENSE-APACHE
    └── README.md                   # placeholder
```

### 3.2 Dependency Graph

Strictly directed, no cycles. Mirrors the Python layer rules.

```
aktor-integrations ──► aktor-flow ──► aktor-agents ──► aktor-core
                         │
aktor-moa ───────────────┼──────────► aktor-agents ──► aktor-core
                         │
                         └──────────────────────────► aktor-core
```

Hard rules, enforced at code review (no automated tool in bootstrap phase):

| Crate               | May depend on                                |
|---------------------|----------------------------------------------|
| `aktor-core`        | (nothing in the aktor family)                |
| `aktor-flow`        | `aktor-core`                                 |
| `aktor-agents`      | `aktor-core`                                 |
| `aktor-moa`         | `aktor-flow`, `aktor-agents`, `aktor-core`   |
| `aktor-integrations`| `aktor-flow`, `aktor-agents`                 |

No reverse dependencies. No private module access across crates (`pub(crate)`
only, never `pub(super)` from outside the module's own tree).

---

## 4. Licensing

### 4.1 File Distribution

Three canonical files at the repository root:

| File              | Content                                                     |
|-------------------|-------------------------------------------------------------|
| `LICENSE`         | Multi-license overview table (mirrors Python `LICENSE`)     |
| `LICENSE-BSL`     | BSL 1.1 full text with `aktor` exhibit parameters           |
| `LICENSE-APACHE`  | Apache License 2.0 full text + copyright boilerplate        |

Each sub-directory's `LICENSE` is a **symbolic link** to one of these roots:

| Path                     | Target            |
|--------------------------|-------------------|
| `core/LICENSE`           | `../LICENSE-BSL`  |
| `flow/LICENSE`           | `../LICENSE-BSL`  |
| `agents/LICENSE`         | `../LICENSE-BSL`  |
| `moa/LICENSE`            | `../LICENSE-BSL`  |
| `integrations/LICENSE`   | `../LICENSE-APACHE` |
| `examples/LICENSE`       | `../LICENSE-APACHE` |
| `docs/LICENSE`           | `../LICENSE-APACHE` |

Git must have `core.symlinks = true` (git 2.10+, default on modern installs).
Windows users may need developer mode. This is the same compromise major Rust
repositories like `tokio` accept.

### 4.2 BSL 1.1 Exhibit Parameters

```
Licensor:             aktor contributors
Licensed Work:        aktor
Additional Use Grant: You may use the Licensed Work for any purpose, including
                      internal commercial use, except selling, licensing, or
                      otherwise providing the Licensed Work or a substantially
                      similar product to third parties for commercial gain.
Change Date:          2030-04-11
Change License:       Apache License, Version 2.0
```

Full text is adapted verbatim from the Python repo's `core/LICENSE`, with only
the parameters above substituted.

### 4.3 Cargo.toml License Metadata

- BSL crates (`aktor-core`, `aktor-flow`, `aktor-agents`, `aktor-moa`):
  ```toml
  license      = "BUSL-1.1"
  license-file = "LICENSE"
  ```
- Apache crates (`aktor-integrations`):
  ```toml
  license      = "Apache-2.0"
  license-file = "LICENSE"
  ```

Note: crates.io treats `BUSL-1.1` as a non-OSI license and emits a warning on
publish. This is expected. Mitigation when publishing is out of scope for the
bootstrap phase.

### 4.4 Root `LICENSE` Overview Content

Mirrors the Python repo's `LICENSE` markdown format, with a component table,
permitted/prohibited usage summary for BSL, change-date disclosure, and
Apache 2.0 summary for community components.

---

## 5. Tooling Baseline

### 5.1 Toolchain Pin (`rust-toolchain.toml`)

```toml
[toolchain]
channel    = "1.85"
components = ["rustfmt", "clippy"]
profile    = "minimal"
```

MSRV is **1.85** — the minimum version required for Rust Edition 2024.

### 5.2 Workspace Root `Cargo.toml`

```toml
[workspace]
resolver = "3"
members  = ["core", "flow", "agents", "moa", "integrations"]

[workspace.package]
edition      = "2024"
rust-version = "1.85"
authors      = ["aktor contributors"]
repository   = "https://github.com/<owner>/aktor"
homepage     = "https://github.com/<owner>/aktor"
license      = "BUSL-1.1"        # default; Apache crates override

[workspace.dependencies]
# async runtime
tokio           = { version = "1", features = ["rt-multi-thread", "sync", "time", "macros"] }
futures         = "0.3"

# error / types
thiserror       = "2"
anyhow          = "1"              # examples only

# serialization
serde           = { version = "1", features = ["derive"] }
serde_json      = "1"

# observability
tracing         = "0.1"

# testing
tokio-test      = "0.4"
proptest        = "1"              # property-based testing; mirrors hypothesis

[workspace.lints.rust]
unsafe_code       = "forbid"
missing_docs      = "warn"
unreachable_pub   = "warn"

[workspace.lints.clippy]
pedantic          = { level = "warn", priority = -1 }
nursery           = { level = "warn", priority = -1 }
module_name_repetitions = "allow"
must_use_candidate      = "allow"

[profile.release]
lto           = "thin"
codegen-units = 1
```

**Deliberate omission**: no `async-trait` dependency. Native `async fn in trait`
(stabilized Rust 1.75) is used throughout.

### 5.3 Per-Crate `Cargo.toml` Template

```toml
[package]
name         = "aktor-core"         # adjust per crate
version      = "0.0.1"
edition.workspace      = true
rust-version.workspace = true
authors.workspace      = true
repository.workspace   = true
license      = "BUSL-1.1"           # or "Apache-2.0" for integrations
license-file = "LICENSE"            # symlink target resolves correctly for cargo
description  = "<one-line purpose>"

[lints]
workspace = true

[dependencies]
tokio       = { workspace = true }
thiserror   = { workspace = true }
tracing     = { workspace = true }
# plus crate-specific deps
```

### 5.4 `rustfmt.toml`

```toml
edition             = "2024"
max_width           = 100
imports_granularity = "Crate"
group_imports       = "StdExternalCrate"
newline_style       = "Unix"
```

### 5.5 `clippy.toml`

```toml
msrv = "1.85"
```

### 5.6 GitHub Actions CI (`.github/workflows/ci.yml`)

Single workflow, single job, fails fast on any step:

1. `actions/checkout@v4`
2. `dtolnay/rust-toolchain@1.85` with `rustfmt, clippy`
3. `cargo fmt --all -- --check`
4. `cargo clippy --all-targets --all-features -- -D warnings`
5. `cargo check --all-targets --all-features`
6. `cargo test --all-targets --all-features`
7. `cargo doc --no-deps --all-features` (catches doc-comment syntax errors)

A second `license-check` job (bash-only, no new tools):

- Assert `core/LICENSE`, `flow/LICENSE`, `agents/LICENSE`, `moa/LICENSE` all
  resolve to `LICENSE-BSL`.
- Assert `integrations/LICENSE`, `examples/LICENSE`, `docs/LICENSE` all resolve
  to `LICENSE-APACHE`.
- Assert the `members` list in `Cargo.toml` matches the directory names in the
  root `LICENSE` overview table.

### 5.7 `.gitignore`

```
/target
**/*.rs.bk
Cargo.lock
.DS_Store
.idea/
.vscode/
```

`Cargo.lock` is gitignored because all five crates are libraries. When an
executable crate is added (future phase), this decision is revisited.

---

## 6. Public API Skeletons

Each crate ships a `src/lib.rs` with end-to-end type definitions, trait
signatures, and `todo!()` bodies. Goal: `cargo check` and `cargo doc` pass.

All async trait methods use **native `async fn` in trait** with explicit
`impl Future<Output = _> + Send` return types. No `#[async_trait]` macro.

### 6.1 `aktor-core`

Mirrors Python's `core/` layer: `ActorSystem`, `ActorRef`, `ActorContext`,
`Actor` trait, supervision, mailbox, lifecycle, virtual-actor registry.

```rust
//! Native Rust actor runtime with Orleans-style virtual actors.

use std::future::Future;

pub type Result<T, E = Error> = std::result::Result<T, E>;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("actor is stopped")]
    Stopped,
    #[error("mailbox full")]
    MailboxFull,
    #[error("operation timed out")]
    Timeout,
    #[error("actor not found: {0}")]
    NotFound(String),
    #[error(transparent)]
    Other(#[from] Box<dyn std::error::Error + Send + Sync>),
}

pub trait Actor: Send + 'static {
    type Msg: Send + 'static;

    fn on_started(
        &mut self,
        _ctx: &mut ActorContext<Self::Msg>,
    ) -> impl Future<Output = Result<()>> + Send {
        async { Ok(()) }
    }

    fn on_message(
        &mut self,
        ctx: &mut ActorContext<Self::Msg>,
        msg: Self::Msg,
    ) -> impl Future<Output = Result<()>> + Send;

    fn on_stopped(
        &mut self,
        _ctx: &mut ActorContext<Self::Msg>,
    ) -> impl Future<Output = Result<()>> + Send {
        async { Ok(()) }
    }
}

pub struct ActorContext<M> { _msg: std::marker::PhantomData<M> }

impl<M: Send + 'static> ActorContext<M> {
    pub fn self_ref(&self) -> ActorRef<M> { todo!() }
    pub fn stop(&self) { todo!() }
    pub async fn run_blocking<F, T>(&self, _f: F) -> Result<T>
    where F: FnOnce() -> T + Send + 'static, T: Send + 'static
    { todo!() }
}

pub struct ActorRef<M> { _msg: std::marker::PhantomData<M> }

impl<M: Send + 'static> ActorRef<M> {
    pub fn tell(&self, _msg: M) -> Result<()> { todo!() }
    pub async fn ask<R, F>(&self, _f: F) -> Result<R>
    where F: FnOnce(tokio::sync::oneshot::Sender<R>) -> M, R: Send + 'static
    { todo!() }
    pub fn stop(&self) { todo!() }
    pub async fn join(self) { todo!() }
}

pub struct ActorSystem { /* ... */ }

impl ActorSystem {
    pub fn new(_name: impl Into<String>) -> Self { todo!() }
    pub fn spawn<A: Actor>(&self, _actor: A) -> ActorRef<A::Msg> { todo!() }
    pub async fn shutdown(self) { todo!() }
}

pub enum SupervisorStrategy { Restart, Stop, Escalate }

pub trait Supervisor: Send + Sync + 'static {
    fn decide(&self, err: &Error) -> SupervisorStrategy;
}

pub trait RegistryStore: Send + Sync + 'static {
    fn get(
        &self, id: &str,
    ) -> impl Future<Output = Result<Option<Vec<u8>>>> + Send;
    fn put(
        &self, id: &str, state: Vec<u8>,
    ) -> impl Future<Output = Result<()>> + Send;
    fn delete(&self, id: &str) -> impl Future<Output = Result<()>> + Send;
}

pub struct VirtualActorRegistry<S: RegistryStore> { _store: S }
```

### 6.2 `aktor-flow`

Mirrors Python's `flow/`: the `Flow<I, O>` ADT, categorical combinators, the
interpreter bridging to the actor runtime, and optional serialization.

Key design points (mirroring Python version constraints):

- `Flow<I, O>` is a pure `enum` — all variants own immutable data.
- Combinators return new values; never mutate in place.
- Constructor functions validate invariants at creation time (`zip_all`
  requires `>= 2` flows).
- Serialization supports only structural variants; closure-carrying variants
  error at `to_json`.

The skeleton `lib.rs` defines the enum variants, method-chain API, constructor
functions (`pure`, `agent`, `zip_all`, `race`, `at_least`, `loop_`), the
`Interpreter` struct, and a `SerializableFlow` trait. All method bodies are
`todo!()`.

Subtlety: `Flow::Pure` uses `Arc<dyn Fn(I) -> O + Send + Sync>` rather than a
generic `F: Fn`, because Flow variants must be `Sized` to nest inside `Box` /
`Vec` / `HashMap`. Async work lives in `Flow::Agent`, not `Flow::Pure`.

### 6.3 `aktor-agents`

Mirrors Python's `agents/`: `Task` trait, `AgentActor`, streaming events,
`AgentCard` discovery, A2A multi-turn is a usage pattern (no new type).

```rust
pub trait Task: Send + 'static {
    type Input: Send;
    type Output: Send;

    fn execute(
        &mut self,
        input: Self::Input,
    ) -> impl Future<Output = Result<Self::Output>> + Send;
}

pub enum StreamItem<O> {
    Progress(ProgressEvent),
    Chunk(Vec<u8>),
    Result(O),
}

pub struct AgentCard {
    pub name: String,
    pub description: String,
    pub skills: Vec<Skill>,
}

pub struct Skill { pub name: String, pub description: String }

pub struct AgentSystem { /* wraps ActorSystem */ }

impl AgentSystem {
    pub fn spawn_agent<T: Task>(&self, _task: T) -> AgentRef<T> { todo!() }
    pub fn discover_one<F>(&self, _m: F) -> Option<AgentRef<()>>
    where F: Fn(&AgentCard) -> bool { todo!() }
    pub fn discover_all<F>(&self, _m: F) -> Vec<AgentRef<()>>
    where F: Fn(&AgentCard) -> bool { todo!() }
}

pub struct AgentRef<T> { _task: std::marker::PhantomData<T> }
```

### 6.4 `aktor-moa`

Mirrors Python's `moa/`: `moa_layer`, `moa_tree`, `MoASystem`, `LayerOutput`.
Defined entirely in terms of `aktor-flow` combinators and `aktor-agents`
tasks; no new runtime primitives.

### 6.5 `aktor-integrations`

LLM provider adapters, Apache 2.0. Only the trait surface in bootstrap:

```rust
pub trait LlmProvider: Send + Sync + 'static {
    fn complete(
        &self, req: CompletionRequest,
    ) -> impl Future<Output = Result<CompletionResponse>> + Send;
    fn stream(
        &self, req: CompletionRequest,
    ) -> impl Future<Output = Result<BoxStream<CompletionChunk>>> + Send;
}
```

Provider-specific modules are gated behind feature flags:

```toml
[features]
openai    = []
anthropic = []
langchain = []
```

No implementation in bootstrap — only the trait and empty feature-gated
`mod openai {}`, etc.

---

## 7. Governance Documents

### 7.1 `README.md`

Short landing page: project tagline, relationship to Python counterpart, crate
table with licenses and one-line purposes, status disclaimer (pre-alpha),
license pointer.

### 7.2 `CLAUDE.md`

Rust-specific coding principles, structured to mirror the Python repo's
`CLAUDE.md`. Sections:

- Environment (Rust 1.85+, Edition 2024, Cargo workspace, library usage
  conventions for tokio / thiserror / serde / tracing / proptest)
- Layer separation with dependency graph
- Flow API coding constraints (ADT immutability, combinator purity, invariant
  validation at construction, serialization limits)
- Virtual Actor model (flat, registry-managed, pluggable store)
- Lifecycle guarantees (`on_started` / `on_stopped`)
- Actor encapsulation (message-only communication)
- Let-it-crash (`Result` propagation, supervision)
- Fail-fast (invalid state raises at call boundaries)
- Strong typing (type parameters end-to-end, no `Box<dyn Any>`, `unsafe_code = forbid`)
- Async-native (no blocking calls, `spawn_blocking` escape hatch)
- Testing (behavior over internals, property-based for categorical laws)
- **Non-goals** (explicit note: `aktor` is not related to the Python repo's
  `rust_core/` PyO3 binding)

### 7.3 `CHANGELOG.md`

```markdown
# Changelog

All notable changes to aktor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Initial repository scaffolding with multi-license architecture.
- Five workspace crates: `aktor-core`, `aktor-flow`, `aktor-agents`,
  `aktor-moa`, `aktor-integrations`.
- End-to-end type/trait skeletons; `cargo check --all-targets` passes.
- BSL 1.1 / Apache 2.0 license distribution mirroring the Python counterpart
  `everything-is-an-actor`.
- Native `async fn in trait` throughout; no `async-trait` macro dependency.
- `rust-toolchain.toml` pinned to 1.85, Edition 2024.
- GitHub Actions CI: fmt, clippy (pedantic+nursery), check, test, doc, license-check.

### Notes
- BSL Change Date: 2030-04-11 (converts to Apache License 2.0).
- Crate name `aktor` on crates.io has a dormant pre-existing reservation;
  publication strategy deferred.
```

---

## 8. File Manifest

Exhaustive list of files and symlinks to be created:

### 8.1 Real Files (29 total)

```
aktor/.github/workflows/ci.yml
aktor/.gitignore
aktor/Cargo.toml
aktor/rust-toolchain.toml
aktor/rustfmt.toml
aktor/clippy.toml
aktor/README.md
aktor/CLAUDE.md
aktor/CHANGELOG.md
aktor/LICENSE
aktor/LICENSE-BSL
aktor/LICENSE-APACHE
aktor/core/Cargo.toml
aktor/core/README.md
aktor/core/src/lib.rs
aktor/flow/Cargo.toml
aktor/flow/README.md
aktor/flow/src/lib.rs
aktor/agents/Cargo.toml
aktor/agents/README.md
aktor/agents/src/lib.rs
aktor/moa/Cargo.toml
aktor/moa/README.md
aktor/moa/src/lib.rs
aktor/integrations/Cargo.toml
aktor/integrations/README.md
aktor/integrations/src/lib.rs
aktor/examples/README.md
aktor/docs/README.md
```

### 8.2 Symbolic Links (7)

```
aktor/core/LICENSE          -> ../LICENSE-BSL
aktor/flow/LICENSE          -> ../LICENSE-BSL
aktor/agents/LICENSE        -> ../LICENSE-BSL
aktor/moa/LICENSE           -> ../LICENSE-BSL
aktor/integrations/LICENSE  -> ../LICENSE-APACHE
aktor/examples/LICENSE      -> ../LICENSE-APACHE
aktor/docs/LICENSE          -> ../LICENSE-APACHE
```

---

## 9. Bootstrap Procedure

Single-commit bootstrap to make the BSL Change Date unambiguous:

```bash
cd ~/IdeaProjects
mkdir aktor && cd aktor
git init -b main

# Write all files per §8
# Create all symlinks per §8.2 using `ln -s ../LICENSE-BSL core/LICENSE`, etc.

# Validate
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo check --all-targets --all-features
cargo test --all-targets --all-features
cargo doc --no-deps --all-features

# Commit
git add .
git commit -m "chore: bootstrap aktor Rust workspace with multi-license architecture"
git tag v0.0.1-scaffold
```

### 9.1 Acceptance Criteria

Bootstrap is considered done when **all** of the following hold:

1. Directory `~/IdeaProjects/aktor/` exists and is a git repository on branch
   `main` with exactly one commit (plus the `v0.0.1-scaffold` tag).
2. All 32 files in §8.1 exist with non-placeholder content matching the
   specifications in §3–§7.
3. All 7 symlinks in §8.2 exist and resolve correctly.
4. `cargo fmt --all -- --check` exits 0.
5. `cargo clippy --all-targets --all-features -- -D warnings` exits 0.
6. `cargo check --all-targets --all-features` exits 0.
7. `cargo test --all-targets --all-features` exits 0 (0 tests is acceptable).
8. `cargo doc --no-deps --all-features` exits 0.
9. No `async-trait` crate appears anywhere in `Cargo.lock` or dependency tree.
10. No reference to `async_trait`, `rust_core`, `pyo3`, or `crossbeam-channel`
    appears in any source file.

### 9.2 Explicitly Out of Scope

- `git remote add origin ...` — remote creation is a user decision.
- `gh repo create` — same.
- `cargo publish` — bootstrap version is 0.0.1-scaffold, not for distribution.
- Any business logic implementation beyond `todo!()` placeholders.
- Any port of Python code from `everything-is-an-actor`.

---

## 10. Risks & Open Questions

| Risk | Mitigation |
|------|------------|
| `aktor` name on crates.io is taken by a dormant crate | Document in CHANGELOG; defer publication strategy; scaffold uses `aktor-*` family, which may be individually available. |
| Clippy pedantic+nursery is noisy on skeleton code | Use `workspace.lints.clippy` to allow `module_name_repetitions` and `must_use_candidate`; add `#[allow(dead_code)]` where needed on stub types. |
| Symlink portability on Windows | Matches tokio's approach; Windows contributors enable developer mode or set `core.symlinks=true`. |
| Native `async fn in trait` ergonomic limitations (no `dyn Actor`) | Architecture avoids trait objects for Actor; every actor is generic-concrete via `ActorRef<M>`. |
| MSRV 1.85 is recent (Feb 2025 stabilization) | Acceptable: user explicitly opted into "latest capabilities"; CI uses the same pin, so there is no drift risk. |
| Edition 2024 `resolver = "3"` interaction with older crates | All workspace dependencies (tokio, thiserror, serde, tracing) are actively maintained and resolver-3 compatible. |

### Open Questions (deferred to implementation plan)

1. Should `aktor-integrations` ship any default feature-flagged provider stubs
   in bootstrap (e.g., empty `mod openai {}`), or only the `LlmProvider` trait?
   Current design: trait only. Revisit if CI warns about unused cfg flags.
2. Should `examples/` contain a single "hello world" actor to prove the
   skeleton can be consumed? Current design: no — `examples/` has only a
   README. Revisit if acceptance criteria require a cargo-buildable example.
3. Git remote: GitHub under `greatmengqi`, or a new org, or private? Deferred
   to user decision after bootstrap.

---

## 11. Transition to Implementation

After this spec is approved, the next step is to invoke `writing-plans` to
produce a concrete implementation plan. The plan will break the bootstrap into
ordered, verifiable steps (e.g., "step 1: create directory and git init; step
2: write LICENSE files; step 3: write workspace Cargo.toml; ..."), each with
its own validation gate.

The implementation plan **will not** include any business logic — it only
covers the scaffold described in this document.

---

## Appendix A: Cross-Reference to Python Repository

| Python path                               | aktor path                 | License   |
|-------------------------------------------|----------------------------|-----------|
| `everything-is-an-actor/core/`            | `aktor/core/`              | BSL 1.1   |
| `everything-is-an-actor/flow/`            | `aktor/flow/`              | BSL 1.1   |
| `everything-is-an-actor/agents/`          | `aktor/agents/`            | BSL 1.1   |
| `everything-is-an-actor/moa/`             | `aktor/moa/`               | BSL 1.1   |
| `everything-is-an-actor/integrations/`    | `aktor/integrations/`      | Apache 2.0|
| `everything-is-an-actor/examples/`        | `aktor/examples/`          | Apache 2.0|
| `everything-is-an-actor/docs/`            | `aktor/docs/`              | Apache 2.0|
| `everything-is-an-actor/LICENSE`          | `aktor/LICENSE`            | (overview)|
| `everything-is-an-actor/CLAUDE.md`        | `aktor/CLAUDE.md`          | N/A       |
| `everything-is-an-actor/rust_core/`       | (not mirrored; unrelated)  | N/A       |

`rust_core/` in the Python repository is a PyO3 binding for benchmarking,
using synchronous `crossbeam-channel` + `parking_lot` + OS threads. It is
deliberately **not** reused by `aktor`. `aktor` is a fully async tokio-native
framework and shares no code with `rust_core/`.
