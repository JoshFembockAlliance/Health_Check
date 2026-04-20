# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing 

### Features, Requirements & Deliverables

### Risks & Notes
* [x] Clicking anywhere that isn't a field on a risk or note preview card should open its modal like clicking the title does
* [ ] In the rich text editor, it seems like highlighting a section and clicking it bolds the text, which is annoying. Clicking the highlighted section again reverts it but using the actual bold button does not. Italics can be applied but they also seem like they are not toggling off as expected when the italics button is pressed a second time. The whole thing feels a little clunky. It needs a bit of investigation and some tests. 
* [ ] In the create modal the default height of the text area for the description is too small to fit the placeholder text. In the edit modal the placeholder text does not appear even if the area is empty.

### Misc
* [ ] Using dummy data, update the Readme screenshots based on the new UI. 
* [ ] Update the application browser tab icon to pair with the shield and tick icon we're currently using at the top of the project sidenav bar.


## New Feature Items

### Inter-Dashboard A single card per project designed to show what matters at a glance - High Priority
* [ ] A Project card should highlight the data covered by the top 3 hero cards on the project dashboard but for each project. 


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
