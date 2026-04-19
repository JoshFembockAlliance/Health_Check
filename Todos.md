# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing Pages

### Dashboard 
Export to PDF is never going to be printed so it does not need to use a blank background, make sure it looks similar to the dashboard itself and provides a representative export of the page. 

### Features & Deliverables

### Risks & Notes UI changes
* [ ] The pop-up modal should be larger, particularly horizontally for risks and just in general for notes. The intent of having this kind of modal is to let the user see more details, after all. 
* [ ] The rich text-editor should be given the space to display a lot of rich text, several paragraphs even. 
* [ ] Clicking anywhere on a card that isn't a button should open the details modal, right now it's just the title.
* [ ] Cards taking up slightly more vertical space so that a bit more of descriptions can be shown before it becomes necessary to cut them off would be good.
* [ ] The Risks modal field labels could be shortened to use (d) instead of (days) and not wrap to take up two lines, it looks messy. 

### Risks grid changes
* [ ] The risks have background colours that don't seem to add value. If the intent is to indicate the urgency of a given risk then perhaps having a more neutral background but instead adding a sort of progress indicator bar showing how much budget is at risk vs how much has become unrecoverable would work better.


## New Feature Items

### Rework to be based on Alliance Platform 2 - Very Low Priority, will consume lots of tokens 
Alliance Platform 2 (https://github.com/AllianceSoftware/alliance-platform-py) provides a lot of tools and a uniform visual design. A redesign onto AP2 might provide more structure than our current flask-based setup.

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
Last Addressed: 17/04/2026

### Playwright Unit Test Coverage
Reviewing and enhancing Playwright coverage within the project to reinforce end-to-end coverage.
Last Addressed: 17/04/2026

### Version Bumps
Outdated dependencies can often result in vulnerabilities. Ensure that dependencies are up-to-date and check that the version increase has not broken anything. If things have become broken as a result, rever the change and make a note of it here for manual investigation. This will keep the codebase clean and secure. 
Last Addressed: 14/04/2026

### UI / UX Clarity and Accessibility Review
Review all user interface elements across the different pages. Ensure that each element's purpose is clear and visually legible. Consider accessibility metrics like those that would be used by the Lighthouse chrome plugin. 
Last Addressed: 14/04/2026

### Readme Review
Check that the readme is up to date. Ensure any recent changes that require revisions to the document have been adjusted for. If there have been significant changes, synchronise the readme with the true current state. If the Readme is getting crowded, consider ading one or more purpose-specific multiple documents and linking them to essentially maintain a multi-page readme in a way that is friendly with GitHub. If you update screenshots, ensure mock data is in use instead of actual data as it could contain sensitive customer information. 
