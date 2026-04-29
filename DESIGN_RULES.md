# Dashboard Design Rules

These are the non-obvious decisions we've committed to about how the dashboard
calculates and visualises budget. Most rules exist because the alternative
double-counts, mis-frames, or buries something a PM needs to see in a status
update. Re-read before changing budget calcs, hero cards, modals, or progress
visualisations — and update this file when the rules change.

---

## 1. Budget vocabulary

Three values, each with a single purpose. Don't invent a fourth without a
reason to.

| Name | Formula | Means |
|---|---|---|
| `total_budget` | `initial_budget + adjustments` | The full pot. Denominator for burn % and the base of allocation tilings. |
| `current_budget` | `total_budget − actual_spend` | What's still liquid. "We can't spend what we've already spent." |
| `accessible_budget` | `current_budget − overhead_dollars` | What's still available for feature delivery. |

**Realised risks are not subtracted from `accessible_budget`.** They're a
categorisation of `actual_spend` (team time on risk handling is logged as
spend), so subtracting them again would double-count. See §3 for details.

**Overheads are subtracted from `accessible_budget` and from
`total_budget_days_remaining`.** They are pre-committed to non-feature work
(PM oversight, ceremonies, support) and cannot be redirected to feature
delivery. Showing them as "available days the team can fund" misleads PMs
into promising deliverable runway that was never deliverable.

`total_budget_days_remaining` and `budget_days_remaining` produce the same
value under the current model. Keep both names available; the agile dashboard
hero card label uses the `total_` form. Consolidate at a quieter time.

---

## 2. Spend decomposition

`actual_spend` decomposes into exactly three buckets, summing to itself with
no double-count:

```
actual_spend = earned_value + realised_risk_dollars + unrealised_spend

earned_value     = allocated_dollars × overall_completion / 100
unrealised_spend = max(0, actual_spend − earned_value − realised_risk_dollars)
```

- **Earned value** — spend that produced delivered features.
- **Realised risk** — spend on risk handling (team time on a realised risk).
- **Unrealised spend** — paid time not yet visible as features or
  categorised risk impact (work in flight, rework, exploration, non-feature
  work).

When `earned_value + realised_risk > actual_spend` (favourable variance),
`unrealised_spend = 0` and the surplus is reported as `favourable_variance`.
The bar doesn't extend past the spent zone in this case; the legend chip
reports the surplus.

Any new visualisation involving spend MUST use this decomposition. Don't
invent a new "Spent" block that overlaps with earned value — that
double-counts and distorts the conversation.

---

## 3. Risk temporal semantics

Realised and open risks behave differently and must not be conflated:

| | **Realised risk** | **Open risk** |
|---|---|---|
| State | Already absorbed | Potential, not yet landed |
| Reflected in spend? | Yes (part of `actual_spend`) | No |
| Reduces accessible? | Yes, indirectly via spend | No, but flags exposure |
| Forward demand (single-question, deterministic) | **No** — already gone | **Yes** — could land |
| Forward demand (trend extrapolation) | **Yes — as a *pattern*** | **Implicit** — assumed to keep emerging |
| Visualisation | Solid red block (right) | Striped warning overlay |

**Two different "forward demand" framings; pick the right one for the
question being asked.**

* **Deterministic forward demand** (e.g. budget-days-remaining "exposed
  to open risks", overall-completion modal "after open-risk exposure,
  is there headroom?"): use `features + open_risks` only. Adding
  realised risks would double-count — they've already eaten into the
  runway via spend.

* **Trend forward demand** (e.g. burndown chart's `+ratio` finish):
  extrapolate the *historical pattern* of spend forward. The
  feature-vs-non-feature ratio is computed from `actual_spend` (which
  includes realised risk impact), and the same share of future spend
  is assumed to go on non-feature work. This implicitly accounts for
  new risks opening over time without summing currently-known open
  risks. Realised-risk *dollars* are not added — only the *ratio they
  imply* is projected forward. The companion `+pace` finish does the
  same for spend pace (actual cumulative burn per business day vs
  full-team), so a meeting can diagnose whether pace, productivity,
  or both are pushing the finish date out.

When realised risks are referenced in sub-rows or modals (e.g.
"realised-risk share of past spend: 17.2d"), frame them as *context
about past spend*, never as a fresh deterministic deduction line.

---

## 4. Visualisation conventions

These apply to every hero-card progress bar across the dashboard.

- **Right-anchored layers** = "money gone or pre-committed without delivery
  to show for it" (overhead, unrealised spend, realised risk).
- **Left-anchored layers** = "delivered work" (earned value fill).
- **Middle gap** = truly accessible budget (in lenses where the denominator
  is `total_budget`).
- **Striped overlay** = warning, not consumption. Reserved for open-risk
  exposure on top of accessible.

The denominator of every bar layer must be stated in its tooltip ("of total
budget", "of accessible budget", etc.). Mixing scales without labelling is
where readers get misled.

**One primary visual per hero card.** If a second visualisation is
genuinely needed, it goes in a modal — not stacked beneath the first.

**Toggles control level of detail on a single bar; don't toggle between
alternative views.** The Lifecycle/What's-left toggle was removed because
two whole alternative bars on one card was harder to read than one bar with
hide/show toggles for individual layer-groups. Pattern to follow: "Spend
categories", "Plan markers", "Risk overlay" toggles on the Overall
Completion card.

Always-visible elements (don't put behind toggles):
- Earned value fill
- Overhead block
- Accessible gap

Toggleable elements (can be hidden for declutter):
- Segmented spend categories (collapse into a single merged block when off)
- Plan markers (feature-budget zone tint, on-track target line)
- Open-risk overlay

When a bar layer is hidden by a toggle, the corresponding legend item
hides with it. Use the same class hooks (`spend-detail`, `spend-merged`,
`plan-marker`, `risk-marker`) on bar elements and legend items to keep them
in sync via CSS.

---

## 5. Hero-card sub-rows

Sub-rows must reflect the same semantic hierarchy as the headline value.
Don't introduce new deductions in a sub-row that aren't in the calc.

For categorisations (e.g. "of past spend, this much was on realised risks"),
use the indented-arrow style with reduced opacity:

```html
<div class="row" style="opacity:0.7;" title="...context, not a fresh deduction.">
    <span class="lbl tiny" style="font-size:11px;">↳ realised-risk share of past spend</span>
    <span class="val tiny" style="font-size:11px;">17.2d</span>
</div>
```

This visually distinguishes "subtraction from headline" rows from
"explanation of headline" rows, so PMs aren't tempted to mentally subtract
the categorisation again.

---

## 6. Modal patterns

Modals exist for **sentence-form** answers to PM questions, not for richer
visualisations of the same data. The bar is the visualisation; the modal
explains it.

Pattern (template in `dashboard_agile.html`'s Budget Days modal):

- Hero card carries `role="button"`, `tabindex="0"`, a small `›` chevron
  hint in the label, `cursor: pointer`, and an `aria-haspopup="dialog"`
  reference to the modal id.
- Modal is a `<dialog>` element; opened via `showModal()`, closed via
  backdrop click or ✕ button.
- Each question is its own `<p>` paragraph with an uppercase muted label and
  the answer in plain prose.
- Numeric deltas in the answer are colour-coded (green for surplus, red for
  shortfall) using `var(--good)` / `var(--bad)`.
- Conditional sentences for edge cases (no end date, all features done, no
  risks, no spend, etc.) — never break math by silently dividing by zero or
  showing nonsensical values.

Modals don't replace what the hero card already shows; they answer
follow-up questions you'd otherwise have to do mental arithmetic for.

---

## 7. Forms and filters

**Inline edit save-on-blur**: use a single `<form>` element with
`form="form-id"` attributes on each input/button so all fields submit
together via fetch. Don't duplicate state via hidden inputs across multiple
forms — that creates stale-data bugs when fields are edited in sequence.
Pattern lives on `templates/milestones.html`.

**Filter forms preserve all filter state across changes.** When any single
filter (status, sort, date range) changes, the form submission must carry
the others through. Pattern: every filter input is in the same `<form>`,
sort/date use `onchange="form.submit()"`, status uses `<button type="submit"
name="filter" value="...">`. Clear-filter links explicitly carry forward
the non-cleared params (e.g. `?filter={{ filter_key }}&sort={{ sort_key }}`
without the date params).

---

## 8. Fixed-price specifics

- **Contract value = sum of milestone values**, not `initial_budget`. The
  `total_budget` for a fixed-price project is derived from milestones.
- **Earned-value vs invoiced overlay** lives on the dashboard's Overall
  Completion card. Two thin bars (`Earned`, `Invoiced`) plus a `Planned`
  reference, all denominated against contract value. PM uses this to spot
  "we've earned more than we've invoiced" or vice versa.
- Milestones page uses save-on-blur (see §7) so PMs can bulk-edit values
  without page refresh.

---

## 9. Operational

- **CSS cache busting**: any change to `static/style.css` must bump the
  `?v=designN` parameter in `templates/base.html`. The browser caches
  aggressively otherwise. Current version is in the `<link>` tag at the top
  of `base.html`.
- **Tests**: `tests/test_calculations.py` is the contract for the budget
  model. Update it when changing the meaning of any field in
  `agile_project_summary` or `fixed_price_project_summary`.
- **PostToolUse QMD reindex** runs automatically after Edit/Write — don't
  run `qmd update` manually.

---

## When to update this file

Add a rule when:
- A design decision was non-obvious or had a near-miss alternative
- The same question is likely to come up again in future
- A calc change has implications across multiple cards/modals

Don't add a rule for things that are obvious from reading the code (variable
naming, simple formatting, etc.). This file is for the things you'd want a
fresh pair of eyes to know before they touched the dashboard.
