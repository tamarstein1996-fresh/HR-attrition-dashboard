"""
HR Attrition Dashboard
=======================
An interactive Streamlit dashboard for exploring IBM's synthetic HR attrition
dataset. Built for clarity: anyone, including someone who
does not usually read charts, should be able to look at this page and
understand what is happening and why it might matter.

IMPORTANT FRAMING (see CLAUDE.md): this is a SYNTHETIC dataset used as a
method exercise. Every number below describes an ASSOCIATION in this
snapshot of data, never a proven cause of people leaving.

Run with:
    streamlit run dashboard.py
Then open the URL Streamlit prints (usually http://localhost:8501).

Dependencies: streamlit, pandas, numpy, plotly.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# 1. CONSTANTS — a single source of truth for color meaning and data columns.
#    Keeping these in one place is what makes "red = higher risk" consistent
#    across every KPI card, chart, and legend on the page.
# ----------------------------------------------------------------------------
DATA_PATH = "HR_data.csv"

COLOR_BLUE = "#2C6E9E"    # normal / at-or-below-average risk
COLOR_RED = "#E07A7A"     # higher risk / worse than the company average
COLOR_GRAY = "#888888"    # neutral reference line (the "company average" line)

SATISFACTION_COLS = [
    "JobSatisfaction",
    "EnvironmentSatisfaction",
    "RelationshipSatisfaction",
    "WorkLifeBalance",
]

TENURE_ORDER = ["0-2 yrs (New)", "3-5 yrs", "6-10 yrs", "10+ yrs (Senior)"]

# Small-N discipline: never spotlight a subgroup in the "Key takeaways" panel
# unless it has at least this many people behind it.
MIN_N_FOR_TAKEAWAY = 15


# ----------------------------------------------------------------------------
# 2. DATA LOADING & CLEANING
#    Mirrors the cleaning already validated in the notebook, so the
#    dashboard and the report always agree with each other.
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Load HR_data.csv and apply the same cleaning steps as the notebook.

    - Drop the three zero-variance columns (constant for every row, so they
      cannot explain any difference in attrition).
    - Add Attrition_Flag: a numeric 1/0 version of Attrition, needed for
      rate calculations (mean of 1/0 = a percentage).
    - Add Tenure_Group: buckets YearsAtCompany into plain-language bands.
    - Add SatisfactionIndex: the average of the four satisfaction-style
      survey scores (1-4 scale each), a simple summary of "how happy".

    Cached so this only runs once per session, not on every filter click.
    """
    df = pd.read_csv(path)

    df = df.drop(columns=["EmployeeCount", "StandardHours", "Over18"])

    df["Attrition_Flag"] = (df["Attrition"] == "Yes").astype(int)

    df["Tenure_Group"] = pd.cut(
        df["YearsAtCompany"],
        bins=[-1, 2, 5, 10, 99],
        labels=TENURE_ORDER,
    )

    df["SatisfactionIndex"] = df[SATISFACTION_COLS].mean(axis=1)

    return df


df = load_data(DATA_PATH)

# Company-wide baselines, computed ONCE from the full (unfiltered) dataset.
# Every KPI card and chart compares the current filtered view back to these
# numbers, so "better/worse than usual" always means the same thing.
BASELINE_RATE = df["Attrition_Flag"].mean() * 100
BASELINE_INCOME = df["MonthlyIncome"].mean()
BASELINE_SATISFACTION = df["SatisfactionIndex"].mean()


# ----------------------------------------------------------------------------
# 3. PAGE CONFIG, TITLE, AND "HOW TO USE THIS" NOTE
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="HR Attrition Dashboard",
    page_icon="\U0001F4CA",
    layout="wide",
)

st.title("HR Attrition Dashboard")
st.markdown(
    "**Purpose:** explore which groups of employees are leaving more than "
    f"others, using IBM's synthetic HR dataset ({len(df):,} employees)."
)

st.info(
    "**How to use this dashboard:** use the filters in the left sidebar to "
    "focus on a Department, Job Role, or Attrition status you care about. "
    "Every number, chart, and sentence on this page updates immediately to "
    "match your selection. Throughout the page, "
    f"**:blue[blue] means at or below the company average risk** and "
    f"**:red[red] means above the company average risk** — this color "
    "meaning stays the same everywhere on the page. Remember: this is a "
    "synthetic practice dataset, so results show patterns worth "
    "investigating, not proven causes of people leaving."
)

st.divider()


# ----------------------------------------------------------------------------
# 4. SIDEBAR FILTERS
#    Every chart, KPI, and takeaway sentence below reads from the SAME
#    filtered_df, so the whole page always tells one consistent story.
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")
st.sidebar.caption("Narrow down the data. Leave everything selected to see the whole company.")

departments = sorted(df["Department"].unique())
selected_departments = st.sidebar.multiselect(
    "Department",
    options=departments,
    default=departments,
    help="Pick one or more departments. Leave all selected to see the whole company.",
)

job_roles = sorted(df["JobRole"].unique())
selected_roles = st.sidebar.multiselect(
    "Job Role",
    options=job_roles,
    default=job_roles,
    help="Narrow down to specific job roles.",
)

attrition_choice = st.sidebar.radio(
    "Attrition status",
    options=["All", "Only people who left", "Only people who stayed"],
    index=0,
    help="Focus on leavers only, stayers only, or see everyone.",
)

st.sidebar.markdown("**More filters (optional)**")

overtime_choice = st.sidebar.radio(
    "OverTime",
    options=["All", "Works overtime", "No overtime"],
    index=0,
    help="See if regularly working overtime changes the picture.",
)

tenure_options = [t for t in TENURE_ORDER if t in df["Tenure_Group"].unique()]
selected_tenure = st.sidebar.multiselect(
    "Tenure band",
    options=tenure_options,
    default=tenure_options,
    help="Filter by how long people have been at the company.",
)

if st.sidebar.button("Reset filters"):
    st.rerun()

# --- Apply filters sequentially to build the single shared filtered_df ---
filtered_df = df[
    df["Department"].isin(selected_departments)
    & df["JobRole"].isin(selected_roles)
    & df["Tenure_Group"].isin(selected_tenure)
].copy()

if attrition_choice == "Only people who left":
    filtered_df = filtered_df[filtered_df["Attrition"] == "Yes"]
elif attrition_choice == "Only people who stayed":
    filtered_df = filtered_df[filtered_df["Attrition"] == "No"]

if overtime_choice == "Works overtime":
    filtered_df = filtered_df[filtered_df["OverTime"] == "Yes"]
elif overtime_choice == "No overtime":
    filtered_df = filtered_df[filtered_df["OverTime"] == "No"]

# --- Edge case: nothing matches the current combination of filters ---
if filtered_df.empty:
    st.warning(
        "No employees match this combination of filters. Try selecting more "
        "departments, job roles, or tenure bands in the sidebar."
    )
    st.stop()


# ----------------------------------------------------------------------------
# 5. KPI CARDS
#    Manual HTML cards (not st.metric) so we have full control over color,
#    keeping "red = worse than company average" consistent with the charts.
# ----------------------------------------------------------------------------
def kpi_card(label: str, big_number: str, meaning: str, is_worse: bool) -> str:
    """Build one KPI card as an HTML snippet with our own risk coloring."""
    accent = COLOR_RED if is_worse else COLOR_BLUE
    return f"""
    <div style="
        border-left: 6px solid {accent};
        background-color: #F5F7FA;
        border-radius: 6px;
        padding: 14px 16px;
        height: 130px;
    ">
        <div style="font-size: 13px; color: #444; font-weight: 600;">{label}</div>
        <div style="font-size: 28px; font-weight: 700; color: {accent}; margin: 4px 0;">
            {big_number}
        </div>
        <div style="font-size: 12px; color: #555;">{meaning}</div>
    </div>
    """


filtered_rate = filtered_df["Attrition_Flag"].mean() * 100
filtered_headcount = len(filtered_df)
filtered_leavers = int(filtered_df["Attrition_Flag"].sum())
filtered_income = filtered_df["MonthlyIncome"].mean()
filtered_satisfaction = filtered_df["SatisfactionIndex"].mean()

st.caption(
    "Card colors follow the same rule everywhere on this page: "
    f":blue[**blue = at or below**] the company average, "
    f":red[**red = worse than**] the company average."
)

card_cols = st.columns(5)

with card_cols[0]:
    st.markdown(
        kpi_card(
            "Attrition rate",
            f"{filtered_rate:.1f}%",
            f"Share of this group that has left. Company average is {BASELINE_RATE:.1f}%.",
            is_worse=filtered_rate > BASELINE_RATE,
        ),
        unsafe_allow_html=True,
    )

with card_cols[1]:
    st.markdown(
        kpi_card(
            "Headcount",
            f"{filtered_headcount:,}",
            "Number of employees in this selection.",
            is_worse=False,  # headcount has no risk direction
        ),
        unsafe_allow_html=True,
    )

with card_cols[2]:
    st.markdown(
        kpi_card(
            "Leavers",
            f"{filtered_leavers:,}",
            "How many of them have left the company.",
            is_worse=False,  # a raw count isn't comparable to a baseline rate
        ),
        unsafe_allow_html=True,
    )

with card_cols[3]:
    st.markdown(
        kpi_card(
            "Avg monthly income",
            f"${filtered_income:,.0f}",
            f"Average monthly pay for this group. Company average is ${BASELINE_INCOME:,.0f}.",
            is_worse=filtered_income < BASELINE_INCOME,
        ),
        unsafe_allow_html=True,
    )

with card_cols[4]:
    st.markdown(
        kpi_card(
            "Avg satisfaction index",
            f"{filtered_satisfaction:.2f} / 4",
            f"Average self-reported happiness at work. Company average is {BASELINE_SATISFACTION:.2f}.",
            is_worse=filtered_satisfaction < BASELINE_SATISFACTION,
        ),
        unsafe_allow_html=True,
    )

st.divider()


# ----------------------------------------------------------------------------
# 6. KEY TAKEAWAYS PANEL — plain-English summary of the CURRENT selection.
# ----------------------------------------------------------------------------
def describe_vs_baseline(value: float, baseline: float, tolerance: float = 1.5) -> str:
    """Turn a filtered-vs-baseline comparison into a plain-English phrase."""
    diff = value - baseline
    if abs(diff) <= tolerance:
        return "about the same as"
    return "higher than" if diff > 0 else "lower than"


takeaway_lines = []

rate_phrase = describe_vs_baseline(filtered_rate, BASELINE_RATE)
takeaway_lines.append(
    f"In this selection, **{filtered_rate:.1f}%** of employees have left "
    f"({filtered_leavers} of {filtered_headcount}) — this is **{rate_phrase}** "
    f"the company-wide average of {BASELINE_RATE:.1f}%."
)

# Highest-risk subgroup within the current selection, respecting the
# small-N rule: never spotlight a group with fewer than MIN_N_FOR_TAKEAWAY people.
# We look at JobRole if more than one role is present, otherwise Department.
group_col = "JobRole" if filtered_df["JobRole"].nunique() > 1 else "Department"
# Only emit a "highest-risk subgroup" line when there is more than one group to
# compare; with a single group it would just restate the overall selection.
if filtered_df[group_col].nunique() > 1:
    group_stats = (
        filtered_df.groupby(group_col)["Attrition_Flag"]
        .agg(rate="mean", n="count")
        .assign(rate=lambda d: d["rate"] * 100)
    )
    eligible_groups = group_stats[group_stats["n"] >= MIN_N_FOR_TAKEAWAY]

    if not eligible_groups.empty:
        top_group = eligible_groups["rate"].idxmax()
        top_rate = eligible_groups.loc[top_group, "rate"]
        top_n = int(eligible_groups.loc[top_group, "n"])
        takeaway_lines.append(
            f"The highest-risk group with enough data to be meaningful "
            f"(at least {MIN_N_FOR_TAKEAWAY} people) is **{top_group}**, "
            f"at **{top_rate:.1f}% attrition (N={top_n})**."
        )
    else:
        takeaway_lines.append(
            f"No group in this selection has at least {MIN_N_FOR_TAKEAWAY} people, "
            "so we won't name a 'highest-risk' group here — the numbers would be "
            "too noisy to trust."
        )

# Leaver vs stayer comparison, only if both groups are present in the selection.
if filtered_df["Attrition"].nunique() == 2:
    income_leavers = filtered_df.loc[filtered_df["Attrition"] == "Yes", "MonthlyIncome"].mean()
    income_stayers = filtered_df.loc[filtered_df["Attrition"] == "No", "MonthlyIncome"].mean()
    sat_leavers = filtered_df.loc[filtered_df["Attrition"] == "Yes", "SatisfactionIndex"].mean()
    sat_stayers = filtered_df.loc[filtered_df["Attrition"] == "No", "SatisfactionIndex"].mean()
    takeaway_lines.append(
        f"People who left earned **\\${income_leavers:,.0f}/month** on average, "
        f"versus **\\${income_stayers:,.0f}/month** for those who stayed. "
        f"Their average satisfaction was **{sat_leavers:.2f}** vs **{sat_stayers:.2f}** (scale 1-4)."
    )
elif attrition_choice == "Only people who left":
    takeaway_lines.append(
        f"You are viewing only the {filtered_headcount} employees who left. "
        f"Their average monthly income was \\${filtered_income:,.0f}, compared "
        f"to \\${BASELINE_INCOME:,.0f} company-wide."
    )
elif attrition_choice == "Only people who stayed":
    takeaway_lines.append(
        f"You are viewing only the {filtered_headcount} employees who stayed. "
        f"Their average monthly income was \\${filtered_income:,.0f}, compared "
        f"to \\${BASELINE_INCOME:,.0f} company-wide."
    )

st.subheader("Key takeaways")
# Render each takeaway line with plain st.markdown so **bold** renders natively.
# A bordered container styles the panel without raw HTML (where markdown is inert).
with st.container(border=True):
    for line in takeaway_lines:
        st.markdown(line)

st.divider()


# ----------------------------------------------------------------------------
# 7. MAIN CHARTS — six simple, labeled bar charts.
#    Shared helper builds a "rate by group" bar chart with:
#      - one bar per group, red if above baseline else blue
#      - a data label showing BOTH the rate and the group's N (small-N discipline)
#      - a gray dashed reference line at the company-wide baseline
# ----------------------------------------------------------------------------
def rate_by_group_chart(
    data: pd.DataFrame,
    group_col: str,
    category_order: list | None,
    x_title: str,
    sort_descending: bool = False,
) -> go.Figure:
    """Build a bar chart of attrition rate (%) by group, with N shown on
    each bar so viewers can see how much data backs every number.
    """
    stats = (
        data.groupby(group_col)["Attrition_Flag"]
        .agg(rate="mean", n="count")
        .reset_index()
    )
    stats["rate"] = stats["rate"] * 100

    if sort_descending:
        stats = stats.sort_values("rate", ascending=False)
    elif category_order is not None:
        stats[group_col] = pd.Categorical(stats[group_col], categories=category_order, ordered=True)
        stats = stats.sort_values(group_col)

    stats["risk_label"] = np.where(
        stats["rate"] > BASELINE_RATE, "Above company average", "At or below company average"
    )
    # Data label combines the rate and the sample size, e.g. "39.8% (N=83)"
    stats["label_text"] = stats.apply(lambda r: f"{r['rate']:.1f}%  (N={int(r['n'])})", axis=1)

    fig = px.bar(
        stats,
        x=group_col,
        y="rate",
        color="risk_label",
        color_discrete_map={
            "Above company average": COLOR_RED,
            "At or below company average": COLOR_BLUE,
        },
        text="label_text",
        custom_data=["n"],
        labels={"rate": "Attrition rate (%)", group_col: x_title, "risk_label": "Risk level"},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate="%{x}<br>Attrition rate: %{y:.1f}%<br>People in group (N): %{customdata[0]}<extra></extra>",
    )
    fig.add_hline(
        y=BASELINE_RATE,
        line_dash="dash",
        line_color=COLOR_GRAY,
        annotation_text=f"Company average: {BASELINE_RATE:.1f}%",
        annotation_position="top left",
    )
    fig.update_layout(
        yaxis_title="Attrition rate (%)",
        xaxis_title=x_title,
        legend_title_text="Risk level",
        margin=dict(t=40, b=10),
    )
    return fig


def leaver_vs_stayer_chart(data: pd.DataFrame, value_col: str, y_title: str, value_format: str) -> go.Figure:
    """Build a simple two-bar chart comparing leavers vs stayers on one
    numeric measure (income or satisfaction). The two bars are each
    other's reference, so no baseline line is needed here.
    """
    stats = (
        data.groupby("Attrition")[value_col]
        .mean()
        .reindex(["No", "Yes"])
        .reset_index()
    )
    stats["Group"] = stats["Attrition"].map({"No": "Stayed", "Yes": "Left"})
    stats["label_text"] = stats[value_col].apply(lambda v: value_format.format(v))

    fig = px.bar(
        stats,
        x="Group",
        y=value_col,
        color="Group",
        color_discrete_map={"Stayed": COLOR_BLUE, "Left": COLOR_RED},
        text="label_text",
        labels={value_col: y_title, "Group": "Employee status"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        yaxis_title=y_title,
        xaxis_title="",
        legend_title_text="Employee status",
        margin=dict(t=40, b=10),
    )
    return fig


chart_row1 = st.columns(2)
chart_row2 = st.columns(2)
chart_row3 = st.columns(2)

# --- Chart 1: Which departments lose the most people? ---
with chart_row1[0]:
    st.subheader("Which departments lose the most people?")
    fig1 = rate_by_group_chart(
        filtered_df, "Department", category_order=None, x_title="Department", sort_descending=True
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.caption(
        "Bars above the dashed line are losing people faster than the company "
        "average. The (N=...) label shows how many employees back each bar — "
        "smaller N means the number is less reliable."
    )

# --- Chart 2: Which job roles are highest-risk? ---
with chart_row1[1]:
    st.subheader("Which job roles are highest-risk?")
    fig2 = rate_by_group_chart(
        filtered_df, "JobRole", category_order=None, x_title="Job role", sort_descending=True
    )
    fig2.update_xaxes(tickangle=-30)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(
        "Roles are sorted from highest to lowest attrition; red bars are above "
        "the company average. Check the N before drawing conclusions about a role."
    )

# --- Chart 3: When do people leave? ---
with chart_row2[0]:
    st.subheader("When do people leave?")
    fig3 = rate_by_group_chart(
        filtered_df, "Tenure_Group", category_order=TENURE_ORDER, x_title="Time at the company"
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "Watch the first bar — new employees (0-2 years) typically leave at a "
        "higher rate than employees who have stayed longer."
    )

# --- Chart 4: Does overtime matter? ---
with chart_row2[1]:
    st.subheader("Does overtime matter?")
    overtime_data = filtered_df.copy()
    overtime_data["OverTime_Label"] = overtime_data["OverTime"].map({"Yes": "Works overtime", "No": "No overtime"})
    fig4 = rate_by_group_chart(
        overtime_data, "OverTime_Label", category_order=["No overtime", "Works overtime"], x_title="Overtime"
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.caption(
        "Compare the two bars — working overtime is strongly linked to higher "
        "attrition in this selection."
    )

# --- Chart 5: Do lower earners leave more? ---
with chart_row3[0]:
    st.subheader("Do lower earners leave more?")
    if filtered_df["Attrition"].nunique() == 2:
        fig5 = leaver_vs_stayer_chart(filtered_df, "MonthlyIncome", "Average monthly income ($)", "${:,.0f}")
        st.plotly_chart(fig5, use_container_width=True)
        st.caption(
            "The 'Left' bar is usually shorter — people who left tend to earn "
            "less on average than people who stayed."
        )
    else:
        st.info("Select both leavers and stayers (Attrition status = All) to compare income.")

# --- Chart 6: Are unhappy people leaving? ---
with chart_row3[1]:
    st.subheader("Are unhappy people leaving?")
    if filtered_df["Attrition"].nunique() == 2:
        fig6 = leaver_vs_stayer_chart(
            filtered_df, "SatisfactionIndex", "Average satisfaction index (1-4)", "{:.2f}"
        )
        st.plotly_chart(fig6, use_container_width=True)
        st.caption(
            "The 'Left' bar is usually a little lower — people who left report "
            "somewhat less satisfaction on average, though the gap is often modest."
        )
    else:
        st.info("Select both leavers and stayers (Attrition status = All) to compare satisfaction.")

st.divider()


# ----------------------------------------------------------------------------
# 8. ADVANCED VIEW — technical charts kept out of the main flow on purpose.
# ----------------------------------------------------------------------------
with st.expander("Advanced view (for data-literate users)"):
    st.caption(
        "These views are more technical. They're here for people who want to "
        "dig deeper — they are not needed to understand the main story above."
    )

    # --- Correlation heatmap ---
    st.markdown("**How do numeric factors move together with leaving?**")
    numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
    corr = filtered_df[numeric_cols].corr()
    fig_corr = px.imshow(
        corr,
        color_continuous_scale=[COLOR_BLUE, "#FFFFFF", COLOR_RED],
        zmin=-1,
        zmax=1,
        aspect="auto",
        labels=dict(color="Correlation"),
    )
    fig_corr.update_layout(margin=dict(t=20, b=10))
    st.plotly_chart(fig_corr, use_container_width=True)
    st.caption(
        "Red-ish cells move together with leaving more; blue-ish cells move "
        "together with staying more. This shows association only, not proof "
        "that one thing causes another."
    )

    # --- Income distribution box plot ---
    st.markdown("**Income distribution: leavers vs stayers**")
    if filtered_df["Attrition"].nunique() == 2:
        fig_box = px.box(
            filtered_df,
            x="Attrition",
            y="MonthlyIncome",
            color="Attrition",
            color_discrete_map={"No": COLOR_BLUE, "Yes": COLOR_RED},
            labels={"MonthlyIncome": "Monthly income ($)", "Attrition": "Left the company?"},
        )
        fig_box.update_layout(margin=dict(t=20, b=10))
        st.plotly_chart(fig_box, use_container_width=True)
        st.caption(
            "Each box shows the spread of incomes, not just the average — useful "
            "for seeing how much incomes vary within each group."
        )
    else:
        st.info("Select both leavers and stayers (Attrition status = All) to see this comparison.")

    # --- At-risk employee table ---
    st.markdown("**Illustrative at-risk table (top 20 by a simple heuristic)**")
    risk_table = filtered_df.copy()
    # A simple, transparent heuristic — NOT a predictive model — combining
    # three factors already discussed above: overtime, low satisfaction,
    # short tenure. Used only to illustrate what "high risk" might look like.
    risk_table["RiskScore"] = (
        (risk_table["OverTime"] == "Yes").astype(int) * 2
        + (4 - risk_table["SatisfactionIndex"])
        + (risk_table["YearsAtCompany"] <= 2).astype(int) * 2
    )
    display_cols = [
        "Department", "JobRole", "OverTime", "SatisfactionIndex",
        "YearsAtCompany", "MonthlyIncome", "Attrition", "RiskScore",
    ]
    st.dataframe(
        risk_table.sort_values("RiskScore", ascending=False)[display_cols].head(20),
        use_container_width=True,
    )
    st.caption(
        "RiskScore is a simple, transparent illustration combining overtime, "
        "low satisfaction, and short tenure — it is not a validated predictive "
        "model and should not be used on its own for real decisions."
    )

st.divider()
st.caption(
    f"Data source: IBM's synthetic HR attrition dataset ({len(df):,} employees). "
    "All findings describe associations in this snapshot, not proven causes "
    "of attrition. Use these patterns as hypotheses worth investigating, not "
    "as final conclusions."
)
