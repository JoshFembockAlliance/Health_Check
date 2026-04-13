# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing Pages

### Dashboard 
#### Hero Cards - High Priority
- [ ] Ensure that the financial and timeline impacts of Risks are being accurately communicated through the Hero cards at the top of the dashboard, and that the realised risks are 'eating into' the useable totals by effectively lowering what the cards think of as 100% of the accessible budget. 

#### PDF Export - Medium Priority
- [] Create an export-to-PDF button (it can appear as simply a small document download icon on the top row of the dashboard to the far right of the project name and date items) so that the project's state at a given as-of date can be downloaded for the PM to communicate. 

### Features, Requirements, and Deliverables

### Settings

## New Work Items

### Scheduling Team Size against Timelines - Medium Priority 
- [] A new feature. Current-state is that the team size is flat-multiplied by some number to detemine the useable days on the project. In reality, the team size fluctuates over time. One week might have 5 team members, another might have 3. To address this, I would like an enhancement that introduces a `Capacity Planning` tab that lets me set specific time periods at the fidelity of one-week block where the team size will be a specific number, overriding the default team size. it should also allow for multiple roles to be assigned to that time period (for example, next week I assign a team size of 2 default, and one Architect or other specific role which may have a different day rate to the default). This feature will need to be accounted for in the Dashboard hero card for Budget Days Remaining by factoring in the fluctuations over time. E.g where before it may have said '10 days remaining' for a team of 4 with an effective date of today, if we know that tomorrow we will be switching to a team of 2 for the next 5 days because it has been entered into the capacity planner then we really have more days remaining and that should be apparent. Use tests to validate the work.
- [] After `Capacity Planning` (explained above) is implemented, include a new Dashboard hero card that breaks down the capacity planning by days allocated to each specific role so that these role requirements can be pre-empted and accounted for. It should have total days remaining from the current as-of date, as well as the role days allocated in the next 2-week period (inclusive of as-of date)  

### PM Notes - Medium/Low Priority
-[] Plan and introduce a new `PM Notes` tab where a PM can leave notes against the project. Make the form structurally similar to risks in that it has a name and description that will probably need to be quite a large multi-line text-box but with a status for todo, doing, done, or also sticky. The notes tab does not need any financial information but does need a due date for each created note that is not 'sticky'. Notes should appear in hero cards on the main dashboard below other hero-card and summary items but above the Feature Health items and have a filter for "all" which is off by default. Typically it should show notes that are either sticky, overdue, or due in the next 2 weeks from the as-of date. If there are more than a single row of notes to display the user will need to navigate to the notes tab to browse them all so that they don't clutter the dashboard. 

### Code Comments - Low Priority
* [] Browse the codebase. Where comments would increase clarity to an amatuer getting oriented in the codebase, add them.

### Multiple Projects - Very Low Priority
* [] This application is currently set up to help a Project Manager track the health of one and only one project at a time. The ability to create more than one project and to swap between them would allow a PM to keep track of multiple projects at once. Each project would need a name and description and its financials and settings etc should be entirely separate from other projects. I expect this would break imports and exports as they currently exist, so those may need to be removed. 


### In-Code Unit Test Coverage - Medium Priority
* [] Models have started to grow to the point where many things are interacting between tabs and are expecting for data they require to be passed to them in a certain format. Adding unit tests to the project to ensure that regressions resulting from changes to models are caught and addressed will pay dividends. 

### Playwright Unit Test Coverage - Low Priority
* [] A basic Playwright integration and some test coverage to enable end-to-end coverage.

### Mac App - Very, very Low Priority
* [] Currently this is a web app, a desktop mac application dmg would be slightly more useful. Pyinstall may be able to achieve this with a wrapper. This one is high risk and low priority and probably shouldn't be picked up unless requested or there's an obvious benefit. Particularly if it would cause issues for the test suites. 