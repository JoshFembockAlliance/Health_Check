## Project Plan: Net Accessible Budget Modal - Unrealised Spend

### Goal
To calculate and display a "Net Accessible Budget" metric on the Agile dashboard that assesses whether the volume of unrealized/in-flight spend (e.g., items in progress, defined risks) is within a "healthy" consumption rate. This rate should generally be kept below what could be burned during a single sprint (approximately two working weeks of burn).

### Dependencies & Knowledge Check
1.  **Data Source:** Requires clear definition of "unrealized spend" (e.g., sum of weighted tasks marked 'In Progress' or 'Defined Risk').
2.  **Calculation Logic:** Must accurately calculate the historical "Sprint Burn Rate" (Cost / Time), and apply that rate to the available budget timeframe.
3.  **Visual/UI:** Affects `templates/dashboard_agile.html` and the budget modal.

### Phase 1: Information Gathering & Metrics Definition
- [ ] **Identify Metric Sources:** Pinpoint the exact fields/objects corresponding to "unrealized spend" and determine how to weight them (e.g., by effort points, or simply total linked budget value).
- [ ] **Define Burn Rate:** Review existing calculation logic in `calculations.py` to understand how the current historical burn rate is computed. If no explicit function exists, define a robust methodology for calculating the average burn rate over the last N projects/sprints.
- [ ] **Set Constraint:** Confirm the "1-sprint buffer" rule (e.g., is it always 2 weeks? Or should it dynamically adjust based on the project's stated sprint length?).

### Phase 2: Calculation Logic Implementation
- [ ] **Logic Implementation (`calculations.py`):** Write and test a function `calculate_unrealized_buffer(project_data)` that performs the calculation:
    $$$$\text{Buffer} = \text{Unrealized Spending Total} / \text{Average Sprint Burn Rate}$$
- [ ] **Unit Test:** Write comprehensive unit tests covering boundary conditions (e.g., zero spend, max spend, negative burn rate).

### Phase 3: UI Integration & Presentation
- [ ] **Front-End Logic:** Update key components in `templates/dashboard_agile.html`.
- [ ] **State Display:** Implement visual cues (e.g., colored dots/icons, status text) that change based on the Buffer calculation:
    *   **Green:** Healthy (Buffer > 1.0)
    *   **Yellow:** Caution (Buffer ≈ 1.0)
    *   **Red:** Warning (Buffer < 1.0, requires risk discussion)
- [ ] **Modal Update:** Modify the associated modal to clearly present the calculated buffer, along with a textual recommendation: "Warning: The current unrealized spend buffer suggests we could exceed our runway by X% if the current burn rate persists."