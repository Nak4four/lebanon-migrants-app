# Migrant presence in Lebanon — interactive drill-down

MSBA 325 · Streamlit application

**Live app:** _paste your Streamlit Community Cloud link here after deploying_

## What this is

An interactive page built on the International Organization for Migration's
**Migrant Presence Monitoring (MPM)** exercise for Lebanon — Round 1, collected
October 2020 to June 2021, obtained through the AUB linked data portal
(https://linked.aub.edu.lb:8502/).

It carries two linked visualisations:

1. **Where migrants are** — migrant totals by district, for whichever governorates
   the reader selects, with the drilled-into districts highlighted.
2. **Who they are** — nationality composition of the selected districts, each bar
   normalised to 100%, with the national mix pinned on top as a baseline.

## The two interaction features

The controls are deliberately **linked rather than independent**:

| Control | What it does |
| --- | --- |
| Step 1 — Governorates | Sets the region under examination and drives Chart 1. |
| Step 2 — Districts | Its **options are generated from the Step 1 selection**, so the reader drills down rather than filtering two things separately. It drives Chart 2 and the highlight in Chart 1. |

Changing Step 1 prunes any Step 2 choices that no longer belong to the selected
region, so the app can never land in a contradictory state.

A written justification for each control sits on the page itself, in the
"Why these controls" expanders.

## Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501.

## Repository layout

```
app.py                        the Streamlit application
requirements.txt              pinned dependencies for Streamlit Cloud
data/immigrants_lebanon.csv   the source dataset
README.md                     this file
```

## A note on the data

The MPM counts *migrants* in IOM's sense — largely migrant workers under the
kafala system. **Syrian refugees are not included**; they are counted separately
through UNHCR registration and are far more numerous. The figures are estimates
given by local key informants rather than an enumeration, so some districts report
conspicuously round numbers.
