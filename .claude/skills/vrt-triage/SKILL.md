---
name: vrt-triage
description: Triage unresolved runs from VRT Tracker — fetch images, analyze diffs, classify, and suggest decisions (approve/reject/fix-stabilization)
argument-hint: "[--fetch-only | --no-classify | --auto-reject | --comment-only]"
allowed-tools: Read Write Bash(python3) Bash(rm) Bash(mkdir) Bash(ls) Bash(cd) Bash(open) Agent
---

# VRT Triage — Visual Diff Classification Assistant

Skill for triaging unresolved visual regression tests from Visual Regression Tracker. Fetches images, analyzes diffs, classifies them (regression / responsive / noise), and proposes actions (approve / reject / fix-stabilization).

## Trigger

Activate skill when user asks:
- "triage last VRT run"
- "check VRT"
- "classify tracker diffs"
- `/vrt-triage`

## Workflow (3 steps)

With no arguments, run all three steps in a single pass and answer with the report from
step 3. Do not ask which mode to use and do not ask whether to proceed; `--auto-reject` and
`--comment-only` run only when the user typed them. An empty queue is an answer — say so in
one line and stop.

### Step 1 — Fetch images and metadata from VRT (automatic)

1. If path to Python script unknown, use: `.claude/skills/vrt-triage/references/fetch-and-triage.py`
2. Run:
   ```bash
   cd "$(git rev-parse --show-toplevel)" && \
   python3 .claude/skills/vrt-triage/references/fetch-and-triage.py
   ```
3. Script fetches:
   - Metadata (diffPercent, tolerance, browser, OS, branch)
   - Three images: baseline.png, actual.png, diff.png
   - Saves to `/tmp/vrt-triage/{i}-*`
4. If fetch fails (tracker unavailable, auth error), **stop and tell user** which environment variables to set:
   ```bash
   export VRT_EMAIL='you@example.com'
   export VRT_PASSWORD='...'
   export VRT_APIURL='http://localhost:4200'  # if not localhost
   export VRT_PROJECT='AiTesters Gallery'     # if different
   ```

### Step 2 — Analysis and classification (via Claude agent)

Analyze the entries in this context, one by one — for a queue this size do not dispatch
subagents. Reading the images directly keeps the reasoning on screen and avoids a long
silent pause in front of an audience. Fan out to agents only above roughly ten entries.

- Work from the **image list + metadata** written by step 1
- For each entry:
  1. **Open all three files** — `baseline.png`, `actual.png`, `diff.png` — with the Read
     tool. All three, every entry. Never classify from metadata or from the diff map alone:
     when a removed element sat on a plain background, the diff map shows a small mark that
     is easy to dismiss, while baseline against actual shows an element that is simply gone.
  2. **Take inventory before judging.** Name the persistent landmarks visible in
     `baseline.png` — logo or wordmark, navigation items, primary buttons, images,
     footer marks — and confirm each one in `actual.png`. Anything present in the baseline
     and absent in the actual is a `regression`, never `noise`, whatever `diffPercent` says.
  3. **Compares** — what exactly changed?
  4. **Classifies** into one bucket:
     - `regression` — something critical changed (element disappeared, shifted, lost contrast, went out of frame)
     - `responsive` — layout changed at different viewport (hamburger, collapse, reflow)
     - `noise` — render noise (anti-aliasing, sub-pixel shift, shadow rendering, font differences)
  5. **Estimates confidence** 0.0–1.0 (where 1.0 = 100% sure)
  6. **Provides severity** (critical / major / minor) — for regressions only
  7. **Proposes action**:
     - `approve` — change is OK, promote to new baseline
     - `reject` — this is a regression, fail the test
     - `fix-stabilization` — looks like flake, revisit stabilization

If entry is ambiguous (50-50), agent ranks it **first** in report, not last.

### Step 3 — Report to user

Output in table format + action suggestions:

```
# VRT Triage — {DATE} · {COUNT_ENTRIES}

## Summary

| Entries | Regressions | of them critical | Noise | Responsive | Ambiguous |
|---|---|---|---|---|---|
| {N} | {M} | {K} | {L} | {R} | {A} |

## Ranking by priority

| # | Entry | Type | Severity | Confidence | Diff vs tolerance | What changed | Action |
|---|---|---|---|---|---|---|---|
| 1 | [AMBIGUOUS] hero_button | ??? | — | 0.5 | 2.340% / 0.2% | Shadow or margin, unclear | ⚠️ review manually |
| 2 | gallery_card | regression | critical | 0.95 | 4.910% / 1% | Image failed to load, alt text instead | ❌ reject |
| 3 | counter_live | noise | — | 0.9 | 0.120% / 0.1% | Anti-aliasing on digits | ✅ approve |

Keep `What changed` under about ten words: these rows get read off a screen.

## Details per entry

**[1] hero_button**
- Status: unresolved
- Diff: 2.340% (tolerance: 0.2%)
- Browser/OS: Chrome / Windows
- Branch: feature/new-hero
- What shows in diff.png: magenta mask (counter — OK), but no clear visual change
- **Suggestion:** Open baseline and actual side-by-side in browser; if intentional — approve; if flake — fix-stabilization.

## Next steps

1. **Open each entry in tracker UI**: http://localhost:8082
2. **Approve/reject** — this table is a proposal, you make final decision
3. **Feedback:** if many flaky, propose stabilization audit for that section
```

---

## Arguments (optional)

| Argument | What it does |
|---|---|
| `--fetch-only` | Only fetch images to `/tmp/vrt-triage`, skip analysis |
| `--no-classify` | Fetch and show images, skip AI-classify (developer reviews manually) |
| `--auto-reject` | Agent will propose `POST /test-runs/reject` for certain regressions (confidence ≥ 0.8), not just suggest |
| `--comment-only` | Write suggestions only in entry comment (via `PATCH /test-runs/update`), no approve/reject |

---

## Classification rules

### What counts as `regression` (CRITICAL)

- Element **completely disappeared** — image failed to load, text obscured it, CSS visibility:hidden
- Element **shifted position** — layout changed, margin/padding different, positioning different
- Element **lost contrast** — button text now invisible, indistinguishable from background
- Element **went out of frame** — content overflow, scrollbar appeared / disappeared
- **Functionality lost visual impact** — e.g., click handler removed but element still visually present

**Shape beats size.** Noise is diffuse: it sprinkles single pixels along edges across the
whole frame. A regression is concentrated: the marked pixels form one contiguous shape you
can name. A 1.15% diff gathered into the outline of a logo is a regression; a 2.6% diff
scattered over an entire banner is sub-pixel noise. Ask what shape the marked area has
before you ask how large it is.

**A missing logo or wordmark is `critical`**, even when it costs barely one percent of the
frame. Brand marks are small and load-bearing; percentage of pixels is the wrong yardstick
for them.

**Magenta mask (`#FF00FF`)** is NOT a regression. It's a scheduled element (counter, countdown) — masked as invariant. Ignore magenta in assessment.

### What counts as `responsive` (layout change)

- Hamburger menu appeared / disappeared (viewport change)
- Columns collapsed / expanded
- Grid changed from 3 to 2 columns
- Modal appeared / disappeared (breakpoint change)

Only if **viewport change is evident in metadata** (different browser agent, or known breakpoint change in CSS).

### What counts as `noise`

- **Sub-pixel shifts** — element moves 0.5–1px (rendering artifact)
- **Anti-aliasing** — text / SVG edges slightly blurry differently
- **Shadow rendering** — shadow appears deeper/lighter on light/dark background
- **Font rendering** — same text, but font rasterizes differently across OS
- **Sub-pixel rounding** — border slightly different size due to float rounding

Rule: **the percentage does not decide the bucket — what changed does.** An entry only
reaches this queue because it already exceeded its own tolerance, so `diffPercent` tells you
how much of the frame moved, not whether a human should care. A logo vanishing from a small
header can land under 1%; a 0.6px shift of a whole banner can land above 2%. Read the three
images first and treat the number as supporting evidence, quoted against that entry's own
tolerance rather than against a fixed threshold.

### Confidence levels

- **≥ 0.9** — almost certain. Can propose action (approve / reject).
- **0.7–0.9** — fairly sure. Propose action, but note manual check recommended.
- **0.5–0.7** — borderline. Say "might be" — let user decide.
- **< 0.5** — too uncertain. Flag as `[AMBIGUOUS]` and escalate to manual review.

### Severity (regressions only)

- **critical** — function completely broken (e.g., login button invisible)
- **major** — part of UI lost function / visibility (e.g., form field disappeared)
- **minor** — aesthetics (color, margin, small element) — but UI works

---

## Practice

### If tracker won't start

```bash
cd "$(git rev-parse --show-toplevel)/demo"
docker compose up -d
# wait until ready at http://localhost:4200
```

### If you want to propose reject for certain entries (`--auto-reject`)

Rule: **never** approve (approve sets baseline permanently; if wrong, regression becomes the norm).

Reject is safe — test fails, developer code-reviews and pushes fix. If bot was wrong — developer can manually approve.

**Limit:** auto-reject only for confidence ≥ 0.8 and severity = critical.

### If ambiguous

Ask: is it **visible** in diff.png? If you think it's noise but something visually changed → flag `[AMBIGUOUS]` and wait for user decision.

---

## Execution

```bash
# Full workflow (default)
/vrt-triage

# Fetch only (developer reviews manually)
/vrt-triage --fetch-only

# Fetch + analyze, no actions
/vrt-triage --no-classify

# Triage + propose reject for certain regressions
/vrt-triage --auto-reject

# Triage + save suggestions only in tracker comments
/vrt-triage --comment-only
```

---

## Output

After completion:
1. **Report in terminal** — table + details
2. **Images in `/tmp/vrt-triage/`** — developer can review locally (`open /tmp/vrt-triage/1-diff.png`)
3. **If `--auto-reject`** — list of IDs skill proposed for rejection (you make final decision)
