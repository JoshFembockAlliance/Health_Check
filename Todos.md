# ToDo Items

This is a list of ToDos. Read through it, plan to address items, and tick items off as they are addressed. It's fine to plan all the items holistically or to draw reasonnable conceptual lines around related blocks of work before working through the blocks one at a time. For each block of items being picked up together, the plan can be implemented holistically without individual approval but create one code commit per item. If there are many items in the list that are unaddressed, then feel free to enhance the descriptions of these based on the planning in case there is only capacity for partial completion. That would allow future sessions to build on the thinking done initially. 

## Enhancements to Existing Pages

### Dashboard 
* [ ] For hero cards current total budget and budget days remaining, I would like to add in an indication of the amount of unrealised risk that has not yet been lost as a contrasting point to time which has been lost to the risk. 

* [ ] PM Notes; put stickies first, then sort by due date

* [ ] Risk Exposure Panel; Effective Realised impact currently includes numbers from the open risks. Those have NOT been realised yet and can actually be mitigated, so the number is a little misleading. 

### Capacity Planning
* [ ] Currently the default rate for the default team size is appearing in the dropdown for roles but that is not helpful as it's the fallback default, not something that a user would configure. Instead, they would probably specifically not configure capacity for a time period if they wanted that rate. 

* [ ] It might make sense to move the default team size selector from the settings page into the capacity planner around the top with a selection for the default role as that would be used to calculate the capacity for any time periods where capacity hasn't been explicitly set. There may need to be a refactor and code cleanup to ensure that this change doesn't break anything else that was expecting that information to come from settings. 

### Risks
* [ ] In the Risk editor form, text entry for risk descriptions would benefit from being larger. Right now it's a single line but either a decent sized free text box that allows for newlines or even implementing a rich text editor would be better. There's also a pretty standard structure that would be good to add in as a sort of starting-point template for the text: 
> * Original expectation: 
> * What changed / was revealed:
> * Notable tmeline and sequencing impacts: 

### Features, Requirements, and Deliverables

### Settings

## New Work Items


### Code Comments - Low Priority
* [ ] Browse the codebase. Where comments would increase clarity to an amatuer getting oriented in the codebase, add them.

### Multiple Projects - Low Priority
* [ ] This application is currently set up to help a Project Manager track the health of one and only one project at a time. The ability to create more than one project and to swap between them would allow a PM to keep track of multiple projects at once. Each project would need a name and description and its financials and settings etc should be entirely separate from other projects. I expect this would break imports and exports as they currently exist, so those may need to be removed. 


### In-Code Unit Test Coverage - Very Low Priority
* [ ] Models have started to grow to the point where many things are interacting between tabs and are expecting for data they require to be passed to them in a certain format. Adding unit tests to the project to ensure that regressions resulting from changes to models are caught and addressed will pay dividends. 

### Playwright Unit Test Coverage - Very Low Priority
* [] A basic Playwright integration and some test coverage to enable end-to-end coverage.

### Mac App - Very, very Low Priority
* [ ] Currently this is a web app, a desktop mac application dmg would be slightly more useful. Pyinstall may be able to achieve this with a wrapper. This one is high risk and low priority and probably shouldn't be picked up unless requested or there's an obvious benefit. Particularly if it would cause issues for the test suites. 