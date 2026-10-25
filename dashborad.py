"""
BCRED Streamlit Dashboard – Polished UI Version
"""

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from config import OUT

# Global Plotly theme
pio.templates.default = "plotly_white"

# ============================
# Streamlit Page Setup
# ============================
st.set_page_config(
    page_title="BCRED Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Top Banner
st.markdown(
    """
    <div style="background-color:#0e1117;padding:18px;border-radius:8px;margin-bottom:18px;">
        <h2 style="color:white;text-align:center;font-family:Arial;">
            📘 BCRED – Private Credit Analytics Dashboard
        </h2>
        <p style="color:#cccccc;text-align:center;font-size:15px;">
            Instrument-Level • Fund-Level • XBRL • Deterioration Monitoring • NAV / Cashflow
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================
# Data Loader
# ============================
@st.cache_data
def load():
    fl = pd.read_parquet(OUT / "flags.parquet")
    qm = pd.read_csv(OUT / "quarter_metrics.csv")
    comp = pd.read_csv(OUT / "composition.csv")

    # Facts
    try: facts = pd.read_parquet(OUT / "facts_dimensionless.parquet")
    except: facts = pd.DataFrame()

    # Fund-Level CSVs
    try: nav_tab = pd.read_csv(OUT / "nav_tab.csv")
    except: nav_tab = pd.DataFrame()

    try: red_tab = pd.read_csv(OUT / "red_tab.csv")
    except: red_tab = pd.DataFrame()

    try: fund_tab = pd.read_csv(OUT / "fund_tab.csv")
    except: fund_tab = pd.DataFrame()

    return fl, qm, comp, facts, nav_tab, red_tab, fund_tab

fl, qm, comp, facts, nav_tab, red_tab, fund_tab = load()

quarters = sorted(fl.report_date.unique())

# ============================
# Sidebar Navigation
# ============================
st.sidebar.title("Navigation")
menu = st.sidebar.radio(
    "",
    ["Portfolio Overview", "Borrower Explorer", "Deterioration Flags", "Fund Metrics"]
)

# Sidebar quarter selection
selected_q = st.sidebar.selectbox("Select Quarter", quarters[::-1])

st.sidebar.markdown("---")
st.sidebar.info("BCRED Analytics Dashboard\nDeutsche Bank Case Study\n© Pooja Saini")

# ============================
# PORTFOLIO OVERVIEW
# ============================
if menu == "Portfolio Overview":
    st.header("📊 Portfolio Overview")

    q = selected_q
    cur = qm[qm.report_date == q].iloc[0]

    # KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Fair Value ($)", f"{cur.total_fv:,.0f}")
    c2.metric("Borrowers", int(cur.n_borrowers))
    c3.metric("FV / Cost Ratio", f"{cur.fv_to_cost:.3f}")
    c4.metric("Top-10 Concentration", f"{cur.top10_share:.1%}")

    st.markdown("---")

    # Charts
    st.subheader("Value Trends")
    st.plotly_chart(
        px.line(qm, x="report_date", y=["total_fv", "total_cost"],
                title="Fair Value vs Cost Trend"),
        use_container_width=True
    )

    st.subheader("Portfolio Size")
    st.plotly_chart(
        px.line(qm, x="report_date",
                y=["n_borrowers", "n_instruments"],
                title="Borrowers & Instruments Over Time"),
        use_container_width=True
    )

    st.markdown("---")

    dim = st.selectbox("Composition Breakdown", sorted(comp.dimension.unique()))
    cd = comp[comp.dimension == dim]

    colA, colB = st.columns(2)
    colA.plotly_chart(px.pie(cd[cd.report_date == q],
                             names="category",
                             values="fair_value",
                             title=f"{dim} Mix – {q}"),
                      use_container_width=True)

    colB.plotly_chart(px.area(cd,
                              x="report_date",
                              y="fair_value",
                              color="category",
                              title=f"{dim} Over Time"),
                      use_container_width=True)

    st.markdown("---")
    st.subheader("Top 15 Borrowers")
    top15 = fl[fl.report_date == q].groupby("borrower").fair_value.sum().nlargest(15).reset_index()
    st.plotly_chart(px.bar(top15, x="fair_value", y="borrower",
                           orientation="h",
                           title="Largest Exposures"),
                    use_container_width=True)


# ============================
# BORROWER EXPLORER
# ============================
elif menu == "Borrower Explorer":
    st.header("🔎 Borrower Explorer")

    borrower = st.selectbox("Select Borrower", sorted(fl.borrower.dropna().unique()))
    bd = fl[fl.borrower == borrower]

    st.dataframe(
        bd[[
            "report_date", "instrument", "instrument_id", "par", "cost", "fair_value",
            "ref_rate", "spread", "interest_rate", "maturity_date", "source_url"
        ]],
        use_container_width=True
    )

    melted = bd.melt(["report_date", "instrument_id"], ["par", "cost", "fair_value"])

    st.plotly_chart(
        px.line(melted, x="report_date", y="value",
                color="instrument_id", line_dash="variable",
                title="Instrument Value Trajectory"),
        use_container_width=True
    )

    st.plotly_chart(
        px.line(bd, x="report_date", y="spread",
                color="instrument_id",
                title="Spread (%) Trend"),
        use_container_width=True
    )

    st.plotly_chart(
        px.scatter(bd, x="report_date", y="maturity_date",
                   color="instrument_id",
                   title="Maturity Over Time"),
        use_container_width=True
    )


# ============================
# DETERIORATION FLAGS
# ============================
elif menu == "Deterioration Flags":
    st.header("⚠️ Deterioration Monitoring Flags")

    q = selected_q
    d3 = fl[(fl.report_date == q) & (fl.flag_count > 0)].sort_values("flag_count", ascending=False)

    st.caption("Thresholds defined in flags.py. These are monitoring signals, not credit conclusions.")
    st.dataframe(
        d3[
            ["borrower", "instrument", "fair_value", "fv_cost", "fv_par", "fv_cost_qoq_pts"]
            + [c for c in d3.columns if c.startswith("flag_")]
        ],
        use_container_width=True
    )


# ============================
# FUND METRICS (NAV / REDEMPTIONS / ACTIVITY)
# ============================
elif menu == "Fund Metrics":
    st.header("🏛️ Fund-Level Metrics (NAV, Redemptions, Cashflow)")

    if facts.empty:
        st.warning("No XBRL facts available.")
    else:
        # NAV
        st.subheader("Net Asset Value (NAV)")
        if not nav_tab.empty:
            st.dataframe(nav_tab, use_container_width=True)

            st.plotly_chart(
                px.line(nav_tab, x="report_date", y="StockholdersEquity",
                        title="Fund Equity Over Time"),
                use_container_width=True
            )

            st.plotly_chart(
                px.line(nav_tab, x="report_date", y="NetAssetValuePerShare",
                        title="NAV Per Share"),
                use_container_width=True
            )
        else:
            st.error("NAV table missing.")

        st.markdown("---")

        # Fund Activity
        st.subheader("Cash-Flow Style Fund Activity")
        if not fund_tab.empty:
            st.dataframe(fund_tab, use_container_width=True)

            if "NetCashProvidedByUsedInOperatingActivities" in fund_tab.columns:
                st.plotly_chart(
                    px.bar(fund_tab, x="report_date",
                           y="NetCashProvidedByUsedInOperatingActivities",
                           title="Operating Cash Flow"),
                    use_container_width=True
                )

            if "NetCashProvidedByUsedInFinancingActivities" in fund_tab.columns:
                st.plotly_chart(
                    px.bar(fund_tab, x="report_date",
                           y="NetCashProvidedByUsedInFinancingActivities",
                           title="Financing Cash Flow"),
                    use_container_width=True
                )
        else:
            st.error("Fund activity table missing.")

        st.markdown("---")

        # XBRL Raw
        st.subheader("XBRL Fact Explorer")
        concepts = sorted(facts.concept.unique())
        pick = st.selectbox("Select Concept", concepts)
        fx = facts[facts.concept == pick].copy()
        fx["period"] = fx.instant.fillna(fx.start + " to " + fx.end)

        st.dataframe(
            fx[["report_date", "period", "value", "unit", "text"]],
            use_container_width=True
        )

        st.plotly_chart(
            px.bar(fx, x="report_date", y="value", title=f"{pick} – Values by Quarter"),
            use_container_width=True
        )
