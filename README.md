# Project Health Check

A lightweight web app for tracking project delivery health — budgets, features, requirements, deliverables, and completion status.

![A screenshot of the Project Health Check Dashboard](./readme_screenshots/Dashboard.png) 

## Quick Start

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000

## Setup

1. Go to **Settings** to configure your project name, dates, budget, team size, and roles
2. Add **Features**, then add **Requirements** under each feature
3. Add **Deliverables** under each requirement with budget (in days) and priority
4. Update **% Complete** as work progresses
5. View the **Dashboard** for executive summary and health indicators

## Key Concepts

- **Roles** have day rates. A default role is auto-assigned to new deliverables.
- **Budget Adjustments** track changes to the initial budget over time.
- **Daily Burn Rate** = team size x default role day rate.
- **Health indicators** compare completion % against budget spent % per feature.
