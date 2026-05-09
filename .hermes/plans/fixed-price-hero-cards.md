# Fixed-Price Dashboard — Hero Card Redesign

## Four Status-Update Questions

A PM standing in front of a Fixed-Price dashboard needs to answer four questions at a glance. These map to the Agile dashboard's budget / completion / runway / burndown quartet but are reframed for the contract-based nature of fixed-price work:

| # | Question | Agile Analogue | What it measures |
|---|---|---|---|
| Q1 | **How much margin are we making?** | Net Accessible Budget | Paid − spent = current margin. Projected margin from invoiced. This is the "are we profitable?" question, front and center for fixed-price. |
| Q2 | **Where are we on the contract?** | Overall Completion | Earned value vs contract value, milestone-by-milestone progress, earned/invoiced/planned overlay. The "how much of what we promised have we delivered?" question. |
| Q3 | **Are we burning at plan?** | Runway + Burndown | Actual spend vs expected burn (team_size × day_rate × elapsed_days). The "is our burn rate healthy?" question — the fixed-price version of the Agile burndown. |
| Q4 | **What milestone is coming next?** | Sprint / Capacity | Next milestone name, value, linked completion, invoiced/paid status, and risk overlay. The "what's the next cash-event and delivery event?" question. |

## Current State vs Target

### Current fixed-price hero cards (3 cards, 1 row)
- Margin so far (no modal, flat sub-rows)
- Overall Completion (milestones bar + earned/invoiced/planned mini-bars)
- Next Milestone (flat, no modal)

### Target fixed-price hero cards (4 cards, 2-row grid matching Agile)
1. **Margin Health** (full width, row 1 — analogue to Agile's Net Accessible Budget)
   - Headline: current margin (paid − spent), colour-coded
   - Spend decomposition: earned value, realised risk, overhead, unexplained
   - Projected margin: invoiced − spent
   - Burn delta vs plan (pace)
   - Open-risk exposure (forward-looking)
   - Clickable modal for sentence-form breakdown

2. **Overall Completion** (row 2, left half — enhanced current card)
   - Milestone segment bar (already exists)
   - Overall completion % (already exists)
   - Earned/Invoiced/Planned overlay bars (already exist)
   - Add: spend decomposition bar (right-anchored, matching Agile convention)
   - Add: clickable modal
   - Add: sub-row with delivery target (based on elapsed days)

3. **Burn Rate & Forecast** (row 2, right half — NEW, analogue to Agile Runway)
   - Headline: days of runway remaining (remaining_dollars / daily_burn)
   - Daily burn rate and team size
   - Burn delta vs plan (% over/under)
   - Not-at-risk vs at-risk days split
   - Sub-row: remaining work cost, buffer/shortfall
   - Lens toggle if overhead is configured
   - Clickable modal

4. **Next Milestone** (row 3, full width — enhanced current card)
   - Milestone name, contract value
   - Linked completion %
   - Invoiced / Paid amounts
   - Status chip
   - Add: visual progress element (mini bar or cycle indicator)
   - Add: clickable modal with milestone context
   - Handle "all paid" empty state elegantly

## Design Decisions

### Spacing: two-row hero grid with full-width bottom
Following Agile's `hero-grid two-row` pattern:
- Row 1: Margin Health (spans full width, `grid-column: span 4`)
- Row 2: Overall Completion (span 2) + Burn Rate (span 2)
- Row 3: Next Milestone (span 4, or merged into row 2 if too tall)

### Spend decomposition: reuse Agile's four-bucket model
The four buckets (earned value, realised risk, overhead team, unrealised spend) already exist in the Agile path. For fixed-price, we need to add these calculations to `fixed_price_project_summary()`.

### Modals: sentence-form answers, following Agile's pattern
Each hero card gets a `<dialog>` element with `role="button"`, `tabindex`, `aria-haspopup`, chevron hint. Modal contains paragraphs answering follow-up questions you'd otherwise do mental arithmetic for.

### Colour conventions
- Margin: green if positive, red if negative (already done)
- Completion: green if ahead of target, amber if within 20%, red if behind
- Burn delta: green if under-burning (favourable), red if over-burning
- Risk overlay: striped warning (existing convention)

## Implementation Steps

### Step 1: Extend `fixed_price_project_summary()` in calculations.py
Add the fields needed by the new hero cards:
- `liquid_budget` = total_budget − actual_spend
- `earned_value` = allocated_dollars × overall_completion / 100
- `realised_risk_dollars` = passed in from route (already computed)
- `overhead_team_dollars_realised` = 0 for fixed-price (no overhead team concept in FP; can add later)
- `unrealised_spend` = max(0, actual_spend − earned_value − realised_risk − overhead_realised)
- `feature_expected_burn_pct` = (elapsed_days / planned_days) × 100 — the "should be at X%" target
- `burn_delta` = actual_spend − expected_spend (where expected = team_size × day_rate × elapsed_days)
- `feature_runway_days` = remaining_dollars / daily_burn
- `total_runway_days` = liquid_budget / daily_burn
- `open_risk_dollars` = passed in from route
- `started_feature_count` and `total_feature_count`
- `allocated_dollars` = sum of feature total_dollars (already computed)
- `remaining_dollars` = sum of feature remaining_dollars (already computed)
- `planned_days` = days between start_date and end_date (need end_date from project)

### Step 2: Update `_fixed_price_dashboard()` in main.py
Pass additional computed values (realised_risk_dollars, open_risk_dollars) into the summary dict. The route already computes these for risk_summary — lift them to the summary as well.

### Step 3: Redesign `dashboard_fixed_price.html` hero cards
Rewrite the hero-grid section with the four cards described above, matching the Agile dashboard's visual style:
- Use the same CSS classes (hero-card, hero-grid, two-row, progress, fill-good, etc.)
- Use the same toggle patterns (pill-toggle)
- Use the same modal patterns (<dialog>, aria attributes, JS IIFE)
- Add chevron hints (›) on clickable cards
- Add lens toggles where relevant

### Step 4: Add modal JS for each hero card
For each card that needs a modal, add:
- `<dialog>` element with aria-labelledby
- JS IIFE that opens on card click/keypress, closes on backdrop/escape/✕
- Returns focus to the card on close
- Sentence-form answers with colour-coded deltas

### Step 5: Update tests in test_calculations.py
Add assertions for new fields in `fixed_price_project_summary()` — liquid_budget, earned_value, burn_delta, feature_runway_days, etc.

### Step 6: CSS cache-bust bump in base.html
Bump the `?v=designN` parameter for the static/style.css link.

## Files to Touch

| File | Changes |
|---|---|
| `calculations.py` | Extend `fixed_price_project_summary()` with new fields |
| `main.py` | Lift risk dollars into summary in `_fixed_price_dashboard()` |
| `templates/dashboard_fixed_price.html` | Rewrite hero-grid (4 cards, modals, toggles) |
| `tests/test_calculations.py` | Add assertions for new summary fields |
| `templates/base.html` | Bump CSS cache-bust version |

## Risk Areas

1. **Spend decomposition on fixed-price**: The four-bucket model works naturally for Agile (where actual_spend is team time logged against features). For fixed-price, actual_spend may come from invoices rather than time logs. We need to clarify whether earned_value is still computed the same way. Answer: yes — earned_value = allocated_dollars × overall_completion / 100 is a planned-rate valuation, independent of actual invoicing. The decomposition still works: earned_value + realised_risk + overhead + unrealised = actual_spend. If actual_spend is lower than earned_value (favourable variance), unrealised = 0 and we report the surplus.

2. **Overhead on fixed-price**: Fixed-price projects typically don't have overhead-team members (those are an Agile concept). The overhead fields will be zero, which is fine — the UI handles the zero case gracefully (see Agile card lines 149-157).

3. **Planned completion target**: Agile computes `feature_expected_burn_pct` from capacity periods. Fixed-price needs a simpler formula: elapsed_days / (end_date - start_date in business days). The project dict needs `end_date`. If not set, the target line is hidden.
