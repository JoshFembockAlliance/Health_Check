# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially.

## How this file is organised

- **Short items live inline** — one or two sentences per bullet under their category.
- **Anything needing a deeper plan lives in [`plans/`](plans/)** — one markdown file per feature plan, linked from the relevant inline item with `[Plan: file](plans/file.md)`. Keeps this index tight.
- **Design rules** for budget, dashboard, and modal conventions live in [DESIGN_RULES.md](DESIGN_RULES.md) — read that before changing dashboard math or visualisations. New TODOs that affect those areas should reference the rule they're working with or against.

When promoting an inline TODO to a plan file: create `plans/<short-name>.md`, move the deep planning content there, and replace it in this file with a one-line link.

## Enhancements to Existing

### Agile Project Dashboard Items
- [ ] **Budget Burndown - Open Risk Projection** 
I'd like to rework open risk projection. Currently, it uses open risks but actually, the truth of risks is that new ones open periodically. A better way to factor in risks going forward is to use both the spend delta and the ratio of spend that to features to determine a projected case for if money continues to be spent on things other than feature development at the current rate.  


### Fixed Price Project Dashboard Items
- [ ] **Burndown chart for fixed-price projects - projections** 
The agile burndown answers "is there budget runway for remaining work?". The fixed-price equivalent question is "are we earning value at the rate needed to hit each milestone before it's invoiced?". Different math (milestones-driven), same shape of question. Worth a separate visualisation on the fixed-price dashboard, sized similarly to the agile burndown.

- [ ] **Burndown chart for fixed-price projects - Toggles** 
Switch from using checkboxes to the same style of pill toggle as Overall Completion uses.

- [ ] **Net Accessible Budget Modal - Unrealised Spend**
The modal lists a few items that unrealised spend could go toward but doesn't provide a solid metric for if it's a healthy amount of value to have in-flight at the time of the review. Because an agile sprint typically only includes enough items to finish them out during a single sprint, a healthy amount of in-flight unrealised spend would typically be less than at worst one sprint (typically 2 working weeks) of burn. I think that this is worth calculating and using in the discussion the modal facilitates. More than that is unhealthy and should be discussed and accounted for. 

### Settings
- [x] **Page Layout and symbols restructure** 
Move the visual settings lower down in the page below overheads as those are not frequently adjusted 

- [ ] **Project Symbols** 
Remove the really basic symbols like triangle, dot, diamond and circle from symbol selection. Add a few that are tech-industry relevant, evoking finances, industry, etc. 

### Features, Requirements & Deliverables

### Decision Register

### Capacity

### Inter-Project Navbar
- [x] The side panel when collapsed does not show the project icons properly, only when expanded.

### General
### Demo Projects
- [ ] **Demo Projects**
Create a demo project dev dataset that contains a few items for each project type. The idea of this database is to keep it small and only change it infrequently for use in testing when new features are developed without impacting current projects during testing. If this is overly complex, make a note of why here and move on instead of picking it up. Ensure the note contains enough details tha the causes can be addressed to achieve the desired outcome some other way. 

- [ ] Make sure test coverage is up-to-date and accounts for new features like the decision register, burndown chart projections, spend decomposition (`earned_value + realised_risk + unrealised_spend = actual_spend`), and the budget-model change in [DESIGN_RULES §1](DESIGN_RULES.md).
- [ ] Ensure that project import and export are still robust and account for new features like decision register.
- [ ] **Save-on-blur form-association sweep.** Standardise inline-edit forms across the codebase on the HTML5 `form="..."` association pattern — single `<form>` element per row with inputs in different cells referencing it by `id`. This avoids the stale-data bug we hit on milestones (where two separate forms held duplicated hidden inputs and editing one stole the other's stale state).
  - **Reference pattern** (already migrated): `templates/milestones.html` lines 47-65. The `<form id="mil-{{ m.id }}">` sits outside the table cells; inputs in different `<td>` elements use `form="mil-{{ m.id }}"` to associate.
  - **Migrate**: `templates/feature_detail.html` deliverables autosave (~lines 278-307). The current `autoSave(tr)` function scans `tr.querySelectorAll('input')` and POSTs to `/api/p/${PID}/deliverables/${delId}/update` — works, but the row's HTML uses implicit forms and won't catch the same multi-form-stale-state class of bug if extended. Refactor to one `<form>` per deliverable row with the form-association pattern, then simplify `autoSave` to `new FormData(form)`.
  - **Leave as-is**: `templates/risks.html` inline-status (`data-action="inline-status"`) and inline-realised (`data-action="inline-realised"`) are single-field PATCH-style updates — the form-association pattern adds nothing for single-field cases. Only worth migrating if those grow to multi-field inline edits.
  - **Reference rule**: [DESIGN_RULES §7](DESIGN_RULES.md) — codifies this pattern.
- [ ] **CSS cache-bust automation.** The `<link rel="stylesheet" href="/static/style.css?v=designN">` in `templates/base.html` (line 15) is bumped manually whenever `static/style.css` changes. We've forgotten it at least once during this session — the new strip-toggle CSS rules silently didn't load until we noticed via diagnostics. Pick one of:
  - **Content-hash**: at request time (or app start), compute a hash of `static/style.css` and use that as the `v=` param. No manual step. Simplest fix.
  - **mtime-based**: use `os.path.getmtime('static/style.css')` as the param. Cheaper than hashing, slightly less safe if the file is rewritten with the same content.
  - **Pre-commit hook**: detect `static/style.css` in the diff and auto-increment the version. Keeps the static value but automates the bump.
  - **Reference**: [DESIGN_RULES §9](DESIGN_RULES.md) flags this as a manual step that should be automated.

## New Feature Items

### Project snapshot comparison — Medium Priority
- [ ] Being able to use the import feature to populate data not for the project itself but for a comparison report between two different project dates where differences between dashboard metrics (not at the granularity of individual deliverable deltas because it would be hard to account for new deliverables but maybe overall completion percentages of features) new risks, etc are included and shown to the user to answer the question of "what has changed since the last time we exported the project" at a glance. The import feature may not be required for this if a deep copy of report-relevant information could be made for the snapshot comparison purposes.

### Inter-Dashboard — single card per project — High Priority
- [ ] A Project card should highlight the data covered by the top 3 hero cards on the project dashboard but for each project. **Plan**: [`plans/inter-dashboard-card.md`](plans/inter-dashboard-card.md).

### Distinct Project Types — Medium Priority, do not pick up or plan yet
Every project has to strike a balance between Scope, Price, and Timeline. There are different types of project that a Project Manager might be working on to optimise for one or more of these, typically one must be left flexible or the project can't manoeuvre when issues arise. Plan and add one of the following that has not been implemented and then check it off. Not all project types should be added at once; in fact initially I'd like to add Fixed Price and see how this changes platform architecture.

- **Agile Feature Development** *(Scope very slightly flexible, Timeline slightly flexible, Budget flexible)*: this is what we've been working on so far; primarily a PM engaging with this kind of project wants to answer "Have I been getting a return roughly equal to my spend in an ongoing fashion." Tracks delivery against budget and risks.
- **Fixed Price with Milestones** *(Budget inflexible, Scope inflexible, Timeline flexible)*: has Milestones that unlock payments which increase the effective budget. Multiple features or even deliverables may contribute toward those milestones. Answers "Am I on track to have a return better than my investment overall and/or relative to each milestone." An easy way to illustrate this would be for Fixed-Price projects to have milestones show up on the overall completion progress bar instead of the expected completion, invoiced milestones being one colour and uninvoiced another. Then if the completion line passes a milestone it tells the story that work for something other than the next milestone must have been happening. Expected completion metrics are less important for fixed price projects; "$X should earn $Y value" is a perspective seen through the lens of milestones in fixed price projects.
- **Limited Scope SaaS Development** *(Budget inflexible, Timeline slightly flexible, Scope flexible)*: budget infusions are assumed to be unlocked over time (eg every X weeks, increases by $Y), items chosen for development are typically those lower in size than current margin between spent and unlocked budget. Risks are not an issue for these; instead a manager needs to know which deliverables are financially viable at a given time and to be able to add them to a queue, removing their cost from the current accessible margin (basically adding it to what has been spent, and the opposite if removed).

- [x] Agile Feature Development
- [x] Fixed Price with Milestones
- [ ] Limited Scope SaaS Development

### Rework to be based on Alliance Platform 2 — Very Low Priority, will consume lots of tokens
Alliance Platform 2 (https://github.com/AllianceSoftware/alliance-platform-py) provides a lot of tools and a uniform visual design. A redesign onto AP2 might provide more structure than our current flask-based setup.

### Single sign-on — Very Low priority, do not pick up before Alliance Platform 2 rework
Support for integration with various SSO to allow for multiple users each with their own projects in a single organisation.

### Mac App — Very, very Low Priority
- [ ] Currently this is a web app, a desktop mac application dmg would be slightly more useful. Pyinstall may be able to achieve this with a wrapper. This one is high risk and low priority and probably shouldn't be picked up unless requested or there's an obvious benefit. Particularly if it would cause issues for the test suites.

## Periodic Work Items

These are different from the above in that they are iterative in nature and do not need to be 'checked off' as done. Rather they should be addressed whenever necessary as part of maintaining a healthy codebase. It is preferred to only pick these items up on weekends or when explicitly requested unless they are out of date by more than 2 weeks. Each of these items should be contained in their own commit when addressed by the same plan so that they can be rolled back if necessary.

### Code Comments and Legibility
Browse the codebase for readability. Where non-functional changes to the code that enhance readability can be made, or where comments would increase clarity to an amateur getting oriented in the codebase, add them.
Last Addressed: 14/04/2026

### In-Code Unit Test Coverage
Reviewing and enhancing unit test coverage within the project to ensure that regressions resulting from changes to models are caught and addressed.
Last Addressed: 17/04/2026

### Playwright Unit Test Coverage
Reviewing and enhancing Playwright coverage within the project to reinforce end-to-end coverage.
Last Addressed: 17/04/2026

### Version Bumps
Outdated dependencies can often result in vulnerabilities. Ensure that dependencies are up-to-date and check that the version increase has not broken anything. If things have become broken as a result, revert the change and make a note of it here for manual investigation. This will keep the codebase clean and secure.
Last Addressed: 19/04/2026

### UI / UX Clarity and Accessibility Review
Review all user interface elements across the different pages. Ensure that each element's purpose is clear and visually legible. Consider accessibility metrics like those that would be used by the Lighthouse chrome plugin.

**Each pass should explicitly include a modal a11y check** — we now have several "click hero card → open `<dialog>` modal" patterns and they need keyboard / screen-reader scrutiny:
- **Modals to verify**: `#budget-days-modal` and `#overall-completion-modal` in `templates/dashboard_agile.html`. Both opened via `dialog.showModal()`.
- **Triggers**: `#hero-budget-days` (whole card) and `#hero-overall-completion` (whole card, with `e.target.closest('.detail-toggles')` exclusion so the strip checkboxes don't open the modal). Both have `role="button"`, `tabindex="0"`, `aria-haspopup="dialog"`, `aria-controls` set.
- **Verify**:
  1. Escape key closes each modal (browser-default for `<dialog>` — confirm not blocked by other handlers).
  2. Focus traps inside the modal while open (Tab cycles within, doesn't leak to background page).
  3. Initial focus on open lands sensibly — probably on the close button or the first interactive element. Currently we don't set this explicitly.
  4. Screen reader announces the modal as a dialog with its title (e.g. "Budget Days Remaining — Detail").
  5. Click-on-backdrop closes (we have an `e.target === modal` handler — verify it doesn't fire from inside-card clicks).
  6. Keyboard-only path: focusing the hero card and pressing Enter/Space opens the modal (we have a `keydown` handler — verify it works).
  7. Returning focus to the trigger card after closing.
- **Reference rule**: [DESIGN_RULES §6](DESIGN_RULES.md) describes the modal pattern; if any of the above fail, update the rule with the corrected guidance and fix the existing modals.

Last Addressed: 19/04/2026

### Readme Review
Check that the readme is up to date. Ensure any recent changes that require revisions to the document have been adjusted for. If there have been significant changes, synchronise the readme with the true current state. If the Readme is getting crowded, consider adding one or more purpose-specific multiple documents and linking them to essentially maintain a multi-page readme in a way that is friendly with GitHub. If you update screenshots, ensure mock data is in use instead of actual data as it could contain sensitive customer information.
Last Addressed: 19/04/2026

### Design-Rules Review
Re-read [DESIGN_RULES.md](DESIGN_RULES.md) and prune or update rules whose underlying decisions have changed. Add new rules for non-obvious decisions reached since last addressed. Don't let it become an exhaustive style guide — keep it focused on the things you'd want a fresh pair of eyes to know before touching the dashboard.
Last Addressed: 27/04/2026
