# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing 

### Settings
- [ ] Project Icons. In the same way that a project can have an individual color accent, giving a project its own icon in the sidebar would be a fun way of distinguishing between them at a glance. Add a few icon symbols to settings in the same area as accents are chosen. In a perfect world, the status colour would be the icon's background colour in the navbar while the symbol colour remained consistent, a bit like how the HealthCheck logo has a gradient background with a white shield symbol right now. 

### Features, Requirements & Deliverables
- [x] The little arrows on each Requirement that let the user expand and collapse the deliverables are quite small compared to the title and are easy to miss. Making them around 50% bigger would increase visual clarity.

### Risks 


### Notes
- [ ] Add an option to the filter for hiding notes that are 'Done' which is on by default. If they're closed then they are probably not relevant to the PM any more and are only kept around as a paper trail. 

### Misc

## New Feature Items

### Inter-Dashboard A single card per project designed to show what matters at a glance - High Priority
* [ ] A Project card should highlight the data covered by the top 3 hero cards on the project dashboard but for each project. 

#### Planning Activity

**What we know:**

- The cross-project landing page route is `cross_project_dashboard()` at `main.py:248`. It currently returns a placeholder template (`templates/cross_project.html`) that shows a simple table of projects with a "coming soon" note.
- The three hero cards on the per-project dashboard (`templates/dashboard.html:41–96`) show: (1) **Net Accessible Budget** (`s.accessible_budget` = `current_budget − overhead_dollars − realised_risk_dollars`, where `current_budget = total_budget − actual_spend`), (2) **Overall Completion** (`s.overall_completion` as a weighted % across features), and (3) **Full-Team Budget Days Remaining** (`s.budget_days_remaining` = `accessible_budget / daily_burn`; spend is already subtracted upstream via `current_budget`).
- All metrics for those cards come from `project_summary()` in `calculations.py:112–202`, which takes a project dict, enriched features list, adjustments list, and a default day rate. This function already exists and is stable — we just need to call it per-project in the cross-project route.
- To feed `project_summary()` we need, for each project: the enriched feature list (call `build_feature_data(project_id)` in `main.py:133`), budget adjustments, overheads total, and a risk summary (sums of `effective_impact_days()` / `unrealised_exposure_days()` from `calculations.py:205–226`). The dashboard route at `main.py:313–486` already does all of this — the cross-project route just needs to loop it.
- The CSS for hero cards already exists: `.hero-grid` (3-column grid, `style.css:446`) and `.hero-card` (card style, `style.css:456`). These classes can be reused directly.
- `shell_context(None)` (called in the current route at `main.py:217`) already returns `projects_list` — a list of all projects with name, completion %, and status. This gives us the project IDs to iterate over.
- The `_project_shell_meta()` function (`main.py:199`) shows the existing pattern for computing a compact per-project summary; the inter-dashboard card is a richer version of that.
- Implementation steps that are clear: (1) in `cross_project_dashboard()`, loop over all projects, call `build_feature_data` + `project_summary` + risk sums for each, build a `projects_with_metrics` list of dicts; (2) pass it to the template; (3) in `cross_project.html`, replace the placeholder table with a card grid — one card per project showing the trio of metrics; (4) each card links to `/p/{id}/` for drill-down.
- For a portfolio with many projects, `build_feature_data` per project on every page load could be slow. The dashboard route does this for one project with no caching — for N projects we'll be making O(N × features) DB calls. For typical use (single-user, handful of projects) this is fine.

**Open questions:**

- **Card layout**: Should each project get a full `.hero-grid` trio (3 sub-cards side by side, same as the dashboard), or a single compact "summary card" that shows all three metrics in a condensed layout? The full grid looks great for 2–3 projects but becomes unwieldy at 6+. A compact card (one per project, key numbers in a mini stat row) scales better.
  - Card Layout Answer: Each Project should get one larger card. There will be fewer projects so having a single larger item each will fit. 
- **What to show from card 3**: Budget Days Remaining depends on `team_size × default_day_rate`. If a project has no capacity periods set yet the "days remaining" figure is still meaningful; if it has no default role the number is zero/undefined. Decide whether to show a fallback label or hide that metric when no role is configured. 
  - For all items where a metric does not have enough information to be calculated, it makes sense to simply not show it. The alternative would be making it mandatory which I'd rather not do just yet as different kinds of projects may have a different unit of measure for burndown than a day rate (like maybe hours, or a burn-up for a future SaaS project type). 
- **Health status colour**: The sidebar already shows a status dot (green/amber/grey) per project. Should the inter-dashboard card also reflect a health status (on-track / at-risk / behind) via a coloured border or badge, derived from `health_on_track_pct` / `health_at_risk_pct` thresholds? That would require computing the same logic as the per-project dashboard's feature health summary.
  - No
- **Performance guard**: For large project counts, consider whether to lazily skip the expensive `build_feature_data` call and show a "no data yet" state for projects with zero features, rather than paying the DB cost for empty projects.
  - Yes
- **Empty state for the route**: The current "All Projects" page doubles as the inter-dashboard. Should it keep the current table at all (useful for quick name/description scan), or fully replace it with the card grid?
  - Replace it


### Distinct Project Types - Medium Priority
* [ ] Every project has to strike a balance betwen Scope, Price, and Timeline. There are different types of project that a Project Manager might be working on to optimise for one or more of these, typically one must be left flexible or the project can't maneuver when issues arise. Plan and add one of the following that has not been implemented and then check it off. 
Not all project types should to be added at once, in fact initially I'd like to add Fixed Price and see how this changes platform architecture.
- Agile Feature Development: (Scope Very Slightly Flexible, Timeline Slightly Flexible, Budget Flexible) This is what we've been working on so far, primarily this a PM engaing with this kind of project wants to answer the question "Have I been getting a return roughly equal to my spend in an ongoing fashion. This kind of project tracks delivery against budget and risks.
- Fixed Price with Milestones: (Budget inflexible, Scope inflexible, Timeline Flexible ) This kind of project has Milestones that unlock payments which increase the effective budget. Multiple features or even deliverables may contribute toward those milestones. Answers the question "Am I on track to have a return better than my investment overall and/o relative to each milestone."
- Limited Scope SaaS Devekopment: (Budget Inflexible, Timeline slightly flexible, Scope Flexible) Budget infusions are assumed to be unlocked over time (eg every X weeks, increases by $Y), items chosen for development are typically those lower in size than current margin between spent and unlocked budget. Risks are not an issue for these, instead a manager needs to know which deliverables are financially viable at a given time and to be able to add them to a queue, removing their cost from the current accessible margin by basically adding it to what has been spent (and the opposite if removed)
- [*] Agile Feature Development
- [ ] Fixed Price with Milestones
- [ ] Limited Scope SaaS Development



### Rework to be based on Alliance Platform 2 - Very Low Priority, will consume lots of tokens 
Alliance Platform 2 (https://github.com/AllianceSoftware/alliance-platform-py) provides a lot of tools and a uniform visual design. A redesign onto AP2 might provide more structure than our current flask-based setup.

### Single sign-on - Very Low priority, do not  pick up before lliance Platform 2 rework
Support for integration with various SSO to allow for multiple users each with their own projects in a single organisation.

### Mac App - Very, very Low Priority
* [ ] Currently this is a web app, a desktop mac application dmg would be slightly more useful. Pyinstall may be able to achieve this with a wrapper. This one is high risk and low priority and probably shouldn't be picked up unless requested or there's an obvious benefit. Particularly if it would cause issues for the test suites. 

## Periodic Work Items
These are different from the above in that they are iterative in nature and do not need to be 'checked off' as done. Rather they should be addressed whenever necessary as part of maintaining a healthy codebase. It is preferred to only pick these items up on weekends or when explicitly requested unless they are out of date by more than 2 weeks. Each of these items should be contained in their own commit when addressed by the same plan so that they can be rolled back if necessary. 

### Code Comments and Legibility
Browse the codebase for readability. Where non-functional changes to the code thant enhance readability can be made, or where comments would increase clarity to an amatuer getting oriented in the codebase, add them.
Last Addressed: 14/04/2026

### In-Code Unit Test Coverage
Reviewing and enhancing unit test coverage within the project to ensure that regressions resulting from changes to models are caught and addressed. 
Last Addressed: 17/04/2026

### Playwright Unit Test Coverage
Reviewing and enhancing Playwright coverage within the project to reinforce end-to-end coverage.
Last Addressed: 17/04/2026

### Version Bumps
Outdated dependencies can often result in vulnerabilities. Ensure that dependencies are up-to-date and check that the version increase has not broken anything. If things have become broken as a result, rever the change and make a note of it here for manual investigation. This will keep the codebase clean and secure. 
Last Addressed: 19/04/2026

### UI / UX Clarity and Accessibility Review
Review all user interface elements across the different pages. Ensure that each element's purpose is clear and visually legible. Consider accessibility metrics like those that would be used by the Lighthouse chrome plugin. 
Last Addressed: 19/04/2026

### Readme Review
Check that the readme is up to date. Ensure any recent changes that require revisions to the document have been adjusted for. If there have been significant changes, synchronise the readme with the true current state. If the Readme is getting crowded, consider ading one or more purpose-specific multiple documents and linking them to essentially maintain a multi-page readme in a way that is friendly with GitHub. If you update screenshots, ensure mock data is in use instead of actual data as it could contain sensitive customer information. 
Last Addressed: 19/04/2026
