# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing Pages

### Dashboard 

* [x] The Capacity Remaining hero card does not seem to give the actual number of person days available at the default day rate. Please check, explain, verify, and correct for clarity the calculation being performed. 

* [x] For budget and spend, group like items together. As a concrete example: if we have a current and expected spend to date, a current and expected burn, allocated and unallocated, then these things should be presented together to tell a cohesive story, either in sequence or on the same line. 

### Features & Deliverables
* [x] Typically I prefer to bulk update estimates against multiple deliverables before pressing save. Currently when I eventually save a deliverable, the page refreshes and I lose any edits I have made to other deliverables. I would rather have the page kept in sync with what is on my screen by having it not refresh and save regardless of whether I have pressed the save button when I leave the field I was editing. A visual indicator like having the background of the deliverable that was saved pulse for a moment afterwards might also help to communicate the change.  


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
