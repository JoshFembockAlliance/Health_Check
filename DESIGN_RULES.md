# Dashboard Design Rules

These are the non-obvious decisions we've committed to about how the dashboard
calculates and visualises budget. Most rules exist because the alternative
double-counts, mis-frames, or buries something a PM needs to see in a status
update. Re-read before changing budget calcs, hero cards, modals, or progress
visualisations — and update this file when the rules change.

---

## 1. Budget vocabulary

### Questions the dashboard answers

Every metric exists to answer a single, named question. When a metric tries
to answer two, you get the kind of structural discrepancy that motivated
the rename pass — `accessible_budget` was conflating "what's in the
account" with "what I can still commit," and the comparison vs invoiced
spend looked off whichever lens the reader assumed.

| # | Question | Lens | Canonical metric |
|---|---|---|---|
| Q1 | "How much money is left in the account?" | Liquidity | `liquid_budget` |
| Q2 | "What can I still commit to features without overdrawing reservations?" | Capacity to commit | `promisable_budget` |
| Q3a | "Is total invoiced spend tracking the planned pace?" | Pace variance | `expected_spend` vs `actual_spend` |
| Q3b | "Are features pacing on plan?" | Feature pace | `feature_expected_spend` vs earned value |
| Q4a | "When does the project literally run out of money?" | Total runway | `total_runway_days` |
| Q4b | "How many days of feature work can we still fund?" | Feature runway | `feature_runway_days` |
| Q5 | "Where did the spend actually go?" | Decomposition | earned_value / realised_risk / unrealised_spend |
| Q6 | "What forward exposure could erode the buffer?" | Risk | `open_risk_dollars` |

The headline Budget and Runway hero cards expose lens toggles (Q1↔Q2 and
Q4a↔Q4b) so a PM can switch view for the conversation they're in without
the labels lying. Default lens = Promisable / Feature work (the conservative
planning view).

### Canonical names

Three budget values, each with a single purpose.

| Name | Formula | Means |
|---|---|---|
| `total_budget` | `initial_budget + adjustments` | The full pot. Denominator for burn % and the base of allocation tilings. |
| `liquid_budget` | `total_budget − actual_spend` | Q1: what's still in the account. |
| `promisable_budget` | `liquid_budget − fixed_overhead_dollars − overhead_team.remaining_dollars` | Q2: what can still be committed to features without overdrawing reservations. |

**Deprecated aliases** (still in returned summary dict for one release;
remove after the dashboard sweep is complete):
- `current_budget` → `liquid_budget`
- `accessible_budget` → `promisable_budget`
- `budget_days_remaining` / `total_budget_days_remaining` → `feature_runway_days`

**Realised risks are not subtracted from `promisable_budget`.** They're a
categorisation of `actual_spend` (team time on risk handling is logged as
spend), so subtracting them again would double-count. See §3 for details.

**Only the *unspent* portion of the overhead-team commitment is
deducted.** Overhead-team time that has already been invoiced sits inside
`actual_spend` (and therefore is already removed via `liquid_budget`).
Subtracting the lifetime `overhead_team.total_dollars` would double-count
the realised portion — shrinking `feature_runway_days` by
`overhead_team.realised_dollars / total_daily_burn` business days and
making the burndown projection finish earlier than it should. Same
reasoning as realised risks. Fixed overheads are typically separately
invoiced (not in `actual_spend`), so they continue to be deducted at
face value.

**Overheads are subtracted from `promisable_budget`** (and therefore
reduce `feature_runway_days`). They are pre-committed to non-feature work
(PM oversight, ceremonies, support) and cannot be redirected to feature
delivery. Both runway lenses divide by `total_daily_burn` — overhead roles
are active and spending throughout the project regardless of feature
contribution, so they belong in the denominator for both questions.

**`overhead_dollars` decomposes into `fixed_overhead_dollars +
overhead_team_dollars`.** Fixed overheads are manually-entered $ amounts in
Settings → Overheads (PM retainer, tooling licences). Overhead team members
are roles in Capacity / Settings flagged with `category='overhead'` (BAs,
designers, SMEs, facilitators) — the projected total is derived from the
capacity plan + project overhead defaults extrapolated to project end. Both
share the same accessibility/feature-budget treatment (pre-committed,
right-anchored on the bar). The split is purely for hero-card and modal
clarity — toggling "Spend categories" on the Overall Completion bar
splits the right-anchored overhead block into the two sub-blocks; merged,
they read as a single overhead block.

**Two daily-burn rates, two questions.**

| Rate | Formula | Used for |
|---|---|---|
| `delivery_daily_burn` (alias `daily_burn`) | `team_size × default_day_rate` | Burndown **scope-finish marker dates** ("when does feature delivery land?") and feature-pacing comparisons. |
| `total_daily_burn` | `delivery_daily_burn + overhead_daily_burn` where `overhead_daily_burn = overhead_team_size × default_overhead_rate` (flat, mirrors delivery formula) | Q3a `expected_spend`, Q4a `total_runway_days`, Q4b `feature_runway_days`, **and the burndown chart line itself**. Both runway lenses use this rate — overhead roles are active and spending regardless of feature contribution. |

`actual_spend` is whole-of-project invoicing — it naturally includes
overhead-team time. So `expected_spend = total_daily_burn × elapsed_days`
is the apples-to-apples comparator. Computing `expected_spend` from
delivery-only burn (the previous behaviour) made the burn delta
structurally non-comparable: actual always appeared inflated by exactly
the overhead-team contribution, regardless of real performance.

For feature-pacing comparisons (`feature_expected_burn_pct`, started-feature
targets) use `feature_expected_spend = delivery_daily_burn × elapsed_days`
against `feature_budget = total_budget − overhead_dollars`. Overhead is
out of both numerator and denominator there.

Note: this is **hybrid accrual**. Overhead-team burn shows up progressively
in `expected_spend` and `total_runway_days` (so they compare to actual),
and `promisable_budget` reserves the **remaining** overhead-team
commitment so feature runway isn't promised against money committed to
non-billable roles still to come. The realised portion is left out of
the deduction because it has already left the account via `actual_spend`.
The lens toggle on the headline cards lets PMs view either side without
changing the underlying math.

### "Show unrealised overhead" toggle on the spend decomposition bar

The Overall Completion bar's right-anchored layer represents money gone
or pre-committed without delivery to show for it. The unrealised portion
of the overhead-team commitment (future invoicing not yet landed) is
hidden by default — toggle "Show unrealised overhead" to reveal it. With
the toggle off, the gap on the right of the bar maps to the **Liquid**
budget view; with it on, the gap shrinks to **Promisable**. This is the
same lens distinction as the headline Budget card, projected onto the bar.

Right-anchored = pre-committed / non-deliverable, regardless of whether
realised or projected. Don't move overhead to the left timeline even when
realised; the convention is "left = contributing toward the on-track
feature delivery target, right = not." Realised overhead spent invoicing
that didn't produce features still belongs on the right.

---

## 2. Spend decomposition

`actual_spend` decomposes into exactly four buckets, summing to itself with
no double-count:

```
actual_spend = earned_value + realised_risk_dollars + overhead_team_realised + unrealised_spend

earned_value           = allocated_dollars × overall_completion / 100
overhead_team_realised = overhead_team.realised_dollars (linearly accrued by as_of_date)
unrealised_spend       = max(0, actual_spend − earned_value − realised_risk_dollars − overhead_team_realised)
```

- **Earned value** — spend that produced delivered features.
- **Realised risk** — spend on risk handling (team time on a realised risk).
- **Overhead team (realised)** — invoiced time from overhead-team members
  (BAs, facilitators, SMEs). Explained spend — we know where it went — but
  not counted as earned feature value.
- **Unrealised spend** ("Unexplained") — paid time with no attribution: not
  features, not categorised risk, not overhead. Work in flight, rework,
  exploration. The signal worth investigating in a status meeting.

When `earned_value + realised_risk + overhead_team_realised > actual_spend`
(favourable variance), `unrealised_spend = 0` and the surplus is reported as
`favourable_variance`. The bar doesn't extend past the spent zone in this
case; the legend chip reports the surplus.

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

## 3a. Burndown chart — line vs markers

The agile-dashboard burndown chart deliberately mixes two lenses on a
single picture, because a status meeting needs both at once. Keeping
them separate avoids the previous mis-framing where the line answered
"feature runway" while looking like "cash runway".

* **The line answers Q4a — "when does the project literally run out of
  money?"** Y-axis is `liquid_budget / total_daily_burn` in days, and
  the forward projection burns at the combined delivery + overhead rate
  using all capacity periods (no role filter). The X-axis date where the
  projection meets zero is `budget_exhaustion`.

* **The markers answer Q3 — "when does scope finish?"** `planned_cost`,
  `+inefficiency`, `+pace`, and `+ratio` are date-only verticals. Each
  date is computed at `delivery_daily_burn` against
  `remaining_dollars` (feature scope) — overhead is reserved separately
  and does not move feature delivery. The circle on the line at the
  marker's X is purely informative: it shows where cash sits at that
  date, so the meeting can read both questions at once.

Why not deduct overhead from the line's starting value (the previous
behaviour)? It conflates the two questions. With overhead pre-
subtracted, the line hit zero at `feature_runway_days` instead of
`total_runway_days`, and the reader saw "the project ran out of money"
when the project still had cash for overhead-team time. Capacity changes
to overhead headcount also failed to move the line, even though they
materially change cash runway.

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
  backdrop click or ✕ button. The `<dialog>` must carry `aria-labelledby`
  pointing to the `id` on the title `<strong>` inside it — required so
  screen readers announce the dialog name on open.
- The JS IIFE must include `modal.addEventListener('close', () => card.focus())`
  so keyboard/AT users return to the triggering card after closing (Escape,
  backdrop click, or ✕ button all fire the `close` event).
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
