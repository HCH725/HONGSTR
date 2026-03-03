# Binance "AI Agent Skills" -> HONGSTR Skills/SSOT Mapping (Docs-only)

## Purpose

This document maps Binance's announced "AI Agent Skills" into HONGSTR's stability-first architecture to extract reusable design patterns **without** violating HONGSTR red lines:

- **core diff=0**: no changes under `src/hongstr`
- **report_only by default**
- **tg_cp strictly read-only / no-exec** (no subprocess/os.system/Popen)
- **SSOT-only consumers** (dashboard + tg_cp read `data/state/*` only)
- **no data/** artifacts committed to git

Primary goal: borrow the **skill-pack modularization + unified interface + risk-as-first-class** patterns, while keeping execution/trading out of control-plane.

Source announcement:
- Binance Support Announcement: "Binance Launches AI Agent Skills" (published 2026-03-03)
  - https://www.binance.com/en/support/announcement/detail/bafb9dda6cbb47d5882a4090c31d4c64

## Star Rating Rubric (for adoption priority)

- ⭐⭐⭐⭐⭐: Governance/boundary/provenance improvement; low integration risk; doesn't touch red lines
- ⭐⭐⭐⭐: High value; needs some wiring or data readiness
- ⭐⭐⭐: Spec + schema placeholder first; implement later when data maturity/sample size improves
- ⭐⭐ and below: Observe only / defer

## Mapping Summary Table

| Binance Skill | Binance Capability Summary | HONGSTR Borrowable Pattern | HONGSTR Proposed Skill (report_only) | SSOT Touchpoint | Priority |
|---|---|---|---|---|---|
| Spot Skill | Market data + trade execution (incl. OCO/OPO/OTOCO); requires API key/secret | Explicit separation of **read vs write** capabilities; strict boundary around execution | `skill.market_data.venue_spot_readonly` (read-only snapshots/derived) | Optional: include read-side provenance in `daily_report_latest.json` | ⭐⭐⭐⭐⭐ |
| Query Address Info | Address holdings/value/24h change/concentration | Fixed input/output contract for repeatable analysis tasks | `skill.onchain.address_report` (schema-fixed report) | SSOT stores only summary flags (avoid state bloat) | ⭐⭐⭐ |
| Query Token Info | Token meta/chain/price/liquidity/holders/activity | "Asset master" as a first-class skill/dictionary | `skill.asset.asset_master_lookup` | Define `asset_master_latest.json` schema (docs-first) | ⭐⭐⭐⭐ |
| Crypto Market Rank | Aggregated ranks/"what to watch today" | Use external consensus signals for **universe narrowing**, not entry/exit | `skill.universe.external_rank_ingest` | `daily_report_latest.json.external_watchlist[]` + provenance | ⭐⭐⭐⭐ |
| Meme Rush | Meme lifecycle buckets + narratives | Lifecycle tagging as risk/context, not alpha | `skill.tags.lifecycle_classifier` | `token_tags_latest.json` (optional SSOT summary) | ⭐⭐⭐ |
| Trading Signal | Smart money buy/sell signal fields (trigger/maxGain/exitRate/status) | A universal **signal contract schema** to reduce format drift | `skill.signal.signal_contract_v1_emit` | Standardize rendering in daily/dashboard via schema | ⭐⭐⭐⭐⭐ |
| Token Audit | Contract risk factors (mint/freeze/owner privileges) | Risk checks are co-equal with signals; output must include provenance | `skill.risk.token_audit` | SSOT stores `risk_flags[]`, banded score, provenance | ⭐⭐⭐⭐* |

\* If HONGSTR focuses mainly on large-cap CEX symbols, Token Audit can be deferred; if expanding into on-chain/new listings, promote priority.

## Design Principles to Borrow

### 1) Unified Skill Interface, Modular Capability Registry

Even without adopting Binance's execution path, the **pattern** is valuable:
- Each skill has a stable **input schema**
- Each skill emits a stable **output schema**
- Each skill declares:
  - read/write scope (HONGSTR: read-only / report_only)
  - provenance (source, version, timestamp)
  - failure mode (WARN with graceful fallback)
  - SSOT impact (what fields are allowed into `data/state/*`)

### 2) Risk as a First-Class Output (not an afterthought)

Binance lists "signal" and "audit" side-by-side. HONGSTR should enforce:
- Any candidate list / signal output MUST attach at least one risk summary:
  - liquidity band / venue availability
  - regime/risk gating summary (existing: Brake/RegimeSignal/SystemHealth)
  - if on-chain: contract risk flags

### 3) External Signals Are for Watchlists, Not Alpha

External platform rank/signals should be treated as:
- candidate universe narrowing
- monitoring and triage
NOT as direct buy/sell triggers.

## Proposed HONGSTR Skill Registry (Docs-first)

### Capability Types (suggested)

- `read`: read SSOT snapshots / derived datasets
- `derive`: compute report_only analysis artifacts
- `tag`: create categorical labels (lifecycle/narratives)
- `risk`: produce risk flags/bands with provenance

### Naming Convention (suggested)

`skill.<domain>.<function>`

Examples:
- `skill.universe.external_rank_ingest`
- `skill.signal.signal_contract_v1_emit`
- `skill.risk.token_audit`

## SSOT Integration Rules (stability-first)

### What can go into SSOT (`data/state/*`)
Only compact, decision-support summaries:
- watchlist arrays with provenance
- risk flags/bands with provenance
- normalized signal objects under a strict schema

### What stays out of SSOT
High-cardinality raw data or large reports:
- full token holder lists
- full address breakdowns
- deep contract analysis details

Keep those in `reports/*` or `research/*` outputs (untracked).

## Failure Modes

- Missing/blocked external sources -> `coverage=WARN` and continue
- Any skill failure must degrade gracefully:
  - `status=WARN`
  - `actions=[]`
  - "how to refresh" hint if relevant
- Never block `refresh_state` completion due to optional skills

## Backlog (P0/P1/P2)

### P0 (Docs-first, low-risk)
- Define `signal_contract_v1` schema (docs-only)
- Add "external_watchlist + provenance" fields to daily report spec (docs-only)
- Add "asset master" schema (docs-only)

### P1 (Optional wiring, still report_only)
- Implement external rank ingestion from already-available datasets (e.g., narratives feed) into watchlist summaries
- Implement lifecycle tagging as metadata labels

### P2 (Data source expansion)
- On-chain address reports
- Token audit integration
