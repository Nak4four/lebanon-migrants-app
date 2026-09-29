"""
Migrant presence in Lebanon — an interactive drill-down
MSBA 325

Data: IOM Displacement Tracking Matrix, Migrant Presence Monitoring (MPM)
Round 1, collected October 2020 - June 2021, obtained through the AUB linked
data portal (https://linked.aub.edu.lb:8502/).

Run locally with:  streamlit run app.py
"""

import re
import urllib.parse

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Page setup and palette
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Migrant presence in Lebanon",
    page_icon="🇱🇧",
    layout="wide",
)

INK = "#0B3C49"
TEAL = "#2E7D8A"
AMBER = "#E08A3C"
MUTED = "#C9D6D9"
GREY = "#5C6B72"

# One fixed colour per nationality so the composition chart stays readable
# no matter which districts are on screen.
NAT_COLORS = {
    "Ethiopians": "#0B3C49",
    "Bangladeshi": "#2E7D8A",
    "Other nationalities": "#7FB2B8",
    "Egyptian": "#E08A3C",
    "Sri Lankan": "#B5552E",
    "Sudanese": "#8A9BA3",
    "Iraqi": "#C9A227",
}
NATIONALITIES = list(NAT_COLORS)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
@st.cache_data
def load_data(path: str = "data/immigrants_lebanon.csv") -> pd.DataFrame:
    """Read the MPM file and return one tidy row per district."""
    raw = pd.read_csv(path)

    count_cols = [c for c in raw.columns if c.startswith("Number of")]
    for col in count_cols:
        raw[col] = (
            raw[col].astype(str).str.replace(",", "", regex=False).astype(int)
        )

    def place_name(uri: str) -> str:
        """Turn a DBpedia URI into a readable place name."""
        name = urllib.parse.unquote(str(uri)).split("/")[-1]
        name = name.replace("_", " ").replace(", Lebanon", "")
        name = name.replace(" District", "").replace(" Governorate", "")
        # One source name carries stray non-ASCII bytes (Miniyeh-Danniyeh)
        name = re.sub(r"[^\x00-\x7F]+", "-", name)
        return re.sub(r"-+", "-", name).strip()

    raw["District"] = raw["District URI"].map(place_name)
    raw["Governorate"] = raw["Governorate URI"].map(place_name)

    rename = {c: c.replace("Number of ", "").strip() for c in count_cols}
    raw = raw.rename(columns=rename)
    raw = raw.rename(columns={"other nationalities": "Other nationalities"})

    raw["Total"] = raw[NATIONALITIES].sum(axis=1)
    return raw[["Governorate", "District", "Total"] + NATIONALITIES].sort_values(
        "Total", ascending=False
    )


try:
    df = load_data()
except FileNotFoundError:
    st.error(
        "Could not find data/immigrants_lebanon.csv. "
        "Make sure the data folder sits next to app.py."
    )
    st.stop()

NATIONAL_TOTAL = int(df["Total"].sum())
ALL_GOVERNORATES = sorted(df["Governorate"].unique())


# --------------------------------------------------------------------------
# Sidebar — the two linked controls
# --------------------------------------------------------------------------
st.sidebar.header("Drill down")
st.sidebar.caption(
    "Step 1 sets the region. Step 2 only offers districts inside that region, "
    "so the second control is always a narrowing of the first."
)

chosen_govs = st.sidebar.multiselect(
    "Step 1 — Governorates",
    options=ALL_GOVERNORATES,
    default=["Beirut", "Mount Lebanon"],
    help="Leave empty to show all eight governorates.",
)
if not chosen_govs:
    chosen_govs = ALL_GOVERNORATES

# The options here depend on the selection above: this is the link between
# the two controls.
available_districts = sorted(
    df.loc[df["Governorate"].isin(chosen_govs), "District"].unique()
)

# Drop any districts left over from a previous, wider region selection.
previous = st.session_state.get("district_choice", [])
st.session_state["district_choice"] = [
    d for d in previous if d in available_districts
]

chosen_districts = st.sidebar.multiselect(
    "Step 2 — Districts inside those governorates",
    options=available_districts,
    key="district_choice",
    help=(
        f"{len(available_districts)} districts available given Step 1. "
        "Leave empty to compare them all."
    ),
)
comparison_districts = chosen_districts or available_districts

st.sidebar.divider()
st.sidebar.caption(
    "Source: IOM DTM, Migrant Presence Monitoring Round 1 "
    "(collected October 2020 – June 2021), via the AUB linked data portal."
)

# Subsets used by both charts
region = df[df["Governorate"].isin(chosen_govs)]
selection = df[df["District"].isin(comparison_districts)]


# --------------------------------------------------------------------------
# Header and context
# --------------------------------------------------------------------------
st.title("Migrant presence in Lebanon")
st.markdown(
    """
This page looks at where migrants in Lebanon were living, and which communities
made up that population, using the International Organization for Migration's
**Migrant Presence Monitoring** exercise. The figures come from Round 1, collected
between **October 2020 and June 2021** — during the currency collapse and the year
after the Beirut port explosion. They are estimates supplied by local key
informants such as mukhtars and municipal officials, not a census.

Two limits are worth holding in mind. The exercise counts *migrants* in IOM's
sense — largely migrant workers under the kafala system — so **Syrian refugees are
not in this data at all**; they are counted separately through UNHCR registration
and are an order of magnitude more numerous. And because the estimates are
perception-based, some districts report suspiciously round numbers.
"""
)

col1, col2, col3 = st.columns(3)
col1.metric("Migrants recorded nationally", f"{NATIONAL_TOTAL:,}")
col2.metric(
    "In your current selection",
    f"{int(selection['Total'].sum()):,}",
    f"{selection['Total'].sum() / NATIONAL_TOTAL:.1%} of the national total",
)
# "Other nationalities" is a residual bucket, not a community, so the headline
# metric reports the largest group that is actually named.
named = [n for n in NATIONALITIES if n != "Other nationalities"]
named_totals = selection[named].sum()
top_nat = named_totals.idxmax()
top_share = named_totals.max() / max(selection["Total"].sum(), 1)
col3.metric("Largest named group in selection", top_nat, f"{top_share:.1%} of it")

st.divider()


# --------------------------------------------------------------------------
# Chart 1 — where migrants are (responds to Step 1, highlights Step 2)
# --------------------------------------------------------------------------
st.subheader("1. Where migrants are")

bar_data = region.sort_values("Total")
highlighted = set(comparison_districts)
bar_colors = [
    AMBER if d in highlighted else MUTED for d in bar_data["District"]
]

fig_totals = go.Figure(
    go.Bar(
        x=bar_data["Total"],
        y=bar_data["District"],
        orientation="h",
        marker=dict(color=bar_colors),
        text=[f"{v:,}" for v in bar_data["Total"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:,} migrants<extra></extra>",
    )
)
fig_totals.update_layout(
    template="plotly_white",
    height=max(320, 26 * len(bar_data) + 130),
    margin=dict(l=10, r=40, t=10, b=40),
    xaxis=dict(
        title="Migrants recorded",
        range=[0, bar_data["Total"].max() * 1.18],
    ),
    yaxis=dict(title=""),
    font=dict(family="Helvetica, Arial, sans-serif", color=INK),
)
st.plotly_chart(fig_totals, width="stretch")

if chosen_districts:
    st.caption(
        "Highlighted bars are the districts picked in Step 2; the rest of the "
        "region is kept in grey for scale."
    )
else:
    st.caption(
        "No districts picked yet, so every district in the chosen governorates "
        "is highlighted."
    )


# --------------------------------------------------------------------------
# Chart 2 — who they are (responds to Step 2)
# --------------------------------------------------------------------------
st.subheader("2. Who they are")
st.markdown(
    "Each bar is normalised to 100%, which separates *composition* from *size*: "
    "a district of 300 people and a district of 120,000 can be compared directly. "
    "The top row is the national picture, as a baseline to read the others against."
)

comp_rows = selection.sort_values("Total", ascending=True)
labels = list(comp_rows["District"]) + ["ALL LEBANON"]
national = df[NATIONALITIES].sum()

fig_mix = go.Figure()
for nat in NATIONALITIES:
    district_share = (comp_rows[nat] / comp_rows["Total"] * 100).tolist()
    national_share = [national[nat] / NATIONAL_TOTAL * 100]
    fig_mix.add_trace(
        go.Bar(
            y=labels,
            x=district_share + national_share,
            name=nat,
            orientation="h",
            marker=dict(color=NAT_COLORS[nat]),
            hovertemplate="%{y} — " + nat + ": %{x:.1f}%<extra></extra>",
        )
    )

fig_mix.update_layout(
    barmode="stack",
    template="plotly_white",
    height=max(320, 30 * len(labels) + 150),
    margin=dict(l=10, r=20, t=10, b=40),
    xaxis=dict(title="Share of that area's recorded migrants (%)", range=[0, 100]),
    yaxis=dict(title=""),
    legend=dict(orientation="h", y=-0.18, x=0),
    font=dict(family="Helvetica, Arial, sans-serif", color=INK),
)
st.plotly_chart(fig_mix, width="stretch")


# --------------------------------------------------------------------------
# Insights
# --------------------------------------------------------------------------
st.divider()
st.subheader("Two things the data shows")

left, right = st.columns(2)

with left:
    beirut = int(df.loc[df["District"] == "Beirut", "Total"].iloc[0])
    top3 = int(df.nlargest(3, "Total")["Total"].sum())
    st.markdown(
        f"""
**Presence is extraordinarily concentrated.**
Beirut district alone holds {beirut:,} of the {NATIONAL_TOTAL:,} people recorded —
{beirut / NATIONAL_TOTAL:.1%} of the national total. Add Matn and Tyre and the top
three districts reach {top3 / NATIONAL_TOTAL:.1%}. At the other end, Hermel records
100 people. Any national average is really a statement about Beirut.
"""
    )

with right:
    shares = df.set_index("District")[NATIONALITIES].div(
        df.set_index("District")["Total"], axis=0
    )
    eth_heavy = int((shares["Ethiopians"] >= 0.40).sum())
    beirut_max = shares.loc["Beirut"].max()
    st.markdown(
        f"""
**The capital is mixed; the periphery is not.**
Ethiopians are at least 40% of recorded migrants in {eth_heavy} of the 26 districts,
reaching 100% in Hermel and 91% in Baalbek. Beirut is the most diverse district in
the country — no single group exceeds {beirut_max:.0%} of it. Diversity of origin
tracks the size of the labour market, not geography.
"""
    )


# --------------------------------------------------------------------------
# Design justifications
# --------------------------------------------------------------------------
st.divider()
st.subheader("Why these controls")

with st.expander("Step 1 — Governorate multiselect"):
    st.markdown(
        """
**The question it answers.** *Which part of the country am I looking at?* A reader
arrives with a region in mind — the coast, the Beqaa, the south — and needs to cut
26 districts down to the handful that concern them before any comparison is useful.

**Why a multiselect.** A single-select dropdown was the obvious alternative, and I
rejected it because the most interesting comparisons cross governorate lines:
Beirut against Mount Lebanon is the comparison that carries this dataset, and a
dropdown would force the reader to look at them one at a time and hold the first in
memory. A slider was not an option either — governorates have no natural order, and
a slider would invent one. Checkboxes would work for eight items but would take
eight lines of sidebar for something a multiselect does in one.

**Course concept — reducing clutter.** Plotting all 26 districts at once produces a
chart where Beirut's bar is so long that twenty of the others are visually
indistinguishable from zero. Letting the reader remove whole regions is the
cheapest way to get the number of marks down to something the eye can actually
compare, without discarding any data from the underlying file.
"""
    )

with st.expander("Step 2 — District multiselect, linked to Step 1"):
    st.markdown(
        """
**The question it answers.** *Within this region, which specific districts do I want
to examine, and how does their nationality mix differ?* This is the drill-down
step: Step 1 sets the neighbourhood, Step 2 picks the houses.

**Why this widget, and why linked.** Its options are generated from the Step 1
selection rather than being fixed, so the reader can never construct an empty or
contradictory view — asking for Tripoli while looking at the South is simply not
offered. I considered leaving both controls independent and filtering on the
intersection, but that lets the user reach a blank screen and gives no hint why.
I also considered a search box, which scales better than a multiselect at hundreds
of options but is worse here, where the whole point is that the reader can *see*
the available districts and discover ones they did not know belonged to the region.

**Course concept — overview first, then details on demand, and focusing attention.**
Chart 1 keeps the unselected districts on screen in grey rather than deleting them,
so the drill-down never costs the reader their sense of scale; the selection is
signalled by colour alone. Chart 2 then shows only the chosen districts, with the
national row pinned at the top as context, so a district's share is read
against a known baseline rather than floating free.
"""
    )

st.divider()
st.caption(
    "Built for MSBA 325. Data: IOM DTM Migrant Presence Monitoring Round 1, "
    "via the AUB linked data portal."
)
