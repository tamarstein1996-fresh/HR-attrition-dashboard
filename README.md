[README.md](https://github.com/user-attachments/files/29692705/README.md)
# HR Employee Attrition Analysis

A data-driven analysis of IBM's synthetic HR dataset (1,470 employees, 35 attributes)
to identify the factors **associated** with employee turnover, compute retention KPIs,
and produce clear, hypothesis-framed recommendations for a non-technical HR audience.

**Deliverables:** a Jupyter analysis notebook, an interactive Streamlit dashboard, and a
data-storytelling presentation.

> **Live dashboard:** _paste your Streamlit Cloud URL here after deploying_
> (e.g. `https://hr-attrition-analysis.streamlit.app`)

---

## What's in this package

| File | What it is |
|------|------------|
| `HR_Attrition_Analysis.ipynb` | The full analysis: cleaning, EDA, six retention KPIs, and refined findings — runs end-to-end with all outputs. |
| `dashboard.py` | Interactive Streamlit dashboard built for non-technical HR users. |
| `.streamlit/config.toml` | Dashboard theme (professional blue / soft-red risk palette). |
| `HR_Attrition_Story.pptx` | Data-storytelling presentation that walks through the whole project. |
| `HR_data.csv` | The analysis-ready dataset (1,470 × 35). |
| `HRDB.sql` | The source MySQL dump, documenting the data-extraction (SQL) step. |
| `requirements.txt` | Python dependencies. |
| `screenshots/` | Dashboard screenshot(s). |

---

## Key findings (the short version)

- **Overall attrition is 16.1%** — 237 of 1,470 employees left. Every group is measured against this baseline.
- **Role separates risk far better than department.** Sales Representatives leave at **39.8%** (N=83) — about 2.5× the company average.
- **The first two years are the danger zone:** 29.8% of employees with 0–2 years of tenure leave.
- **Overtime is the single strongest, most controllable signal:** 30.5% attrition with overtime vs 10.4% without.
- **Pay does not explain leaving.** Income and job satisfaction are essentially uncorrelated (r = −0.007), and the apparent income gap between leavers and stayers ($4,787 vs $6,833) **collapses once you control for job level** — it was a confound, not a pay effect.
- Distance-from-home and time-since-promotion do **not** hold up as drivers once examined properly.

All numbers were independently verified against the raw data, and every subgroup figure
reports its sample size (N) so small groups are never over-interpreted.

---

## Running the dashboard locally

From this folder:

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).
Use the sidebar filters (Department, Job Role, Attrition status, Overtime, Tenure) to explore;
every KPI card, chart, and plain-language takeaway updates to match your selection.

## Running the notebook

```bash
pip install -r requirements.txt
jupyter notebook HR_Attrition_Analysis.ipynb
```

All cells are already executed with outputs, so it can also be read top-to-bottom as a report.

---

## Data & methodology note

This uses IBM's **synthetic** HR dataset and a single snapshot in time. Every finding therefore
describes an **association**, not a proven cause of attrition. The value of the project is the
method: clean data, tested claims, verified numbers, small-sample discipline, and conclusions
stated with the appropriate level of confidence — ready to be re-run on real HR data.

**Tech stack:** Python · pandas · NumPy · Plotly · Streamlit · Matplotlib / Seaborn (notebook) · Jupyter
