# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing Pages

### Dashboard 
* [x] For hero cards current total budget and budget days remaining, I would like to add in an indication of the amount of unrealised risk that has not yet been lost as a contrasting point to time which has been lost to the risk. 

* [x] PM Notes; put stickies first, then sort by due date

* [x] Risk Exposure Panel; Effective Realised impact currently includes numbers from the open risks. Those have NOT been realised yet and can actually be mitigated, so the number is a little misleading. 

* [x] The hero cards at the top of the dashboard are pressed up against the top of the capacity plan item. Capacity plan does not seem to visually match the hero cards or the other summary sections. Maybe split it into 2 hero cards or a new hero card and a new line in another section or whatever way of achieving clarity that aligns with standard UX conventions the most.

### Capacity Planning
* [x] Currently the default rate for the default team size is appearing in the dropdown for roles but that is not helpful as it's the fallback default, not something that a user would configure. Instead, they would probably specifically not configure capacity for a time period if they wanted that rate. 

* [x] It might make sense to move the default team size selector from the settings page into the capacity planner around the top with a selection for the default role as that would be used to calculate the capacity for any time periods where capacity hasn't been explicitly set. There may need to be a refactor and code cleanup to ensure that this change doesn't break anything else that was expecting that information to come from settings. 

### Risks
* [x] In the Risk editor form, text entry for risk descriptions would benefit from being larger. Right now it's a single line but either a decent sized free text box that allows for newlines or even implementing a rich text editor would be better. There's also a pretty standard structure that would be good to add in as a sort of starting-point template for the text: 
> * Original expectation: 
> * What changed / was revealed:
> * Notable tmeline and sequencing impacts: 

## New Feature Items
### Multiple Projects - Low Priority
* [ ] This application is currently set up to help a Project Manager track the health of one and only one project at a time. The ability to create more than one project and to swap between them would allow a PM to keep track of multiple projects at once. Each project would need a name and description and its financials and settings etc should be entirely separate from other projects. I expect this would break imports and exports as they currently exist, so those may need to be removed.

### Mac App - Very, very Low Priority
* [ ] Currently this is a web app, a desktop mac application dmg would be slightly more useful. Pyinstall may be able to achieve this with a wrapper. This one is high risk and low priority and probably shouldn't be picked up unless requested or there's an obvious benefit. Particularly if it would cause issues for the test suites. 

## Periodic Work Items
These are different from the above in that they are iterative in nature and do not need to be 'checked off' as done. Rather they should be addressed whenever necessary as part of maintaining a healthy codebase. It is preferred to only pick these items up on weekends or when explicitly requested unless they are out of date by more than 2 weeks. Each of these items should be contained in their own commit when addressed by the same plan so that they can be rolled back if necessary. 

### Code Comments and Legibility
Browse the codebase for readability. Where non-functional changes to the code thant enhance readability can be made, or where comments would increase clarity to an amatuer getting oriented in the codebase, add them.
Last Addressed: 14/04/2026

### In-Code Unit Test Coverage
Reviewing and enhancing unit test coverage within the project to ensure that regressions resulting from changes to models are caught and addressed. 
Last Addressed: 14/04/2026

### Playwright Unit Test Coverage
Reviewing and enhancing Playwright coverage within the project to reinforce end-to-end coverage.
Last Addressed: 14/04/2026

### Version Bumps
Outdated dependencies can often result in vulnerabilities. Ensure that dependencies are up-to-date and check that the version increase has not broken anything. If things have become broken as a result, rever the change and make a note of it here for manual investigation. This will keep the codebase clean and secure. 
Last Addressed: 14/04/2026

### UI / UX Clarity and Accessibility Review
Review all user interface elements across the different pages. Ensure that each element's purpose is clear and visually legible. Consider accessibility metrics like those that would be used by the Lighthouse chrome plugin. 
Last Addressed: 14/04/2026
