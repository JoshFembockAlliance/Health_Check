# Inter-Dashboard: per-project summary cards

**Linked from**: [Todos.md](../Todos.md) · *Inter-Dashboard A single card per project designed to show what matters at a glance*

**Goal**: Replace the placeholder cross-project landing page with a card grid — one card per project showing the same trio of metrics as each project's own dashboard hero strip (Net Accessible Budget, Overall Completion, Full-Team Budget Days Remaining).

---

## What we know

- The cross-project landing page route is `cross_project_dashboard()` at `main.py:248`. It currently returns a placeholder template (`templates/cross_project.html`) that shows a simple table of projects with a "coming soon" note.
- The three hero cards on the per-project dashboard (`templates/dashboard.html:41–96`) show: (1) **Net Accessible Budget** (`s.accessible_budget` = `current_budget − overhead_dollars`, where `current_budget = total_budget − actual_spend`); (2) **Overall Completion** (`s.overall_completion` as a weighted % across features); (3) **Full-Team Budget Days Remaining** (`s.budget_days_remaining` = `accessible_budget / daily_burn`). *(Note: `accessible_budget` no longer subtracts `realised_risk_dollars` — see [DESIGN_RULES §1](../DESIGN_RULES.md).)*
- All metrics for those cards come from `agile_project_summary()` in `calculations.py`, which takes a project dict, enriched features list, adjustments list, and a default day rate. This function already exists and is stable — we just need to call it per-project in the cross-project route.
- To feed `agile_project_summary()` we need, for each project: the enriched feature list (call `build_feature_data(project_id)`), budget adjustments, overheads total, and a risk summary. The agile dashboard route already does all of this — the cross-project route just needs to loop it.
- The CSS for hero cards already exists (`.hero-grid`, `.hero-card`). These classes can be reused.
- `shell_context(None)` already returns `projects_list` — list of all projects with name/completion/status. Gives us the project IDs to iterate.
- `_project_shell_meta()` shows the existing pattern for computing a compact per-project summary; the inter-dashboard card is a richer version of that.

## Implementation outline

1. In `cross_project_dashboard()`, loop over all projects, call `build_feature_data` + `agile_project_summary` + risk sums for each, build a `projects_with_metrics` list of dicts.
2. Pass it to the template.
3. In `cross_project.html`, replace the placeholder table with a card grid — one card per project showing the trio of metrics.
4. Each card links to `/p/{id}/` for drill-down.

## Decisions made

- **Card layout**: Each project gets one larger card (not the full hero grid). Fewer projects → larger cards fit comfortably.
- **Missing-data metrics**: Hide them rather than mandate inputs. Different project types may use different burn units (hours, SaaS-style burn-up) and we don't want to force a day-rate model.
- **Health-status colour**: No. The sidebar already shows a status dot; don't duplicate.
- **Performance guard**: Skip the expensive `build_feature_data` call for projects with zero features. Show a "no data yet" state.
- **Empty state for the route**: Replace the existing table with the card grid — don't keep both.

## Caveats

- For a portfolio with many projects, calling `build_feature_data` per project on every page load is O(N × features) DB calls. For typical use (single user, handful of projects) this is fine; for larger usage we'd want to cache or paginate.
- The current `accessible_budget` calc was changed during the spend-decomposition rework — verify this plan still references the right formula when the work starts.
