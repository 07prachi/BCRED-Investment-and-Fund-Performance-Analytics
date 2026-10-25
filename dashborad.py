"""Step 7. streamlit run dashboard.py"""
import pandas as pd, plotly.express as px, streamlit as st
from config import OUT
st.set_page_config(layout="wide", page_title="BCRED analytics")
@st.cache_data
def load():
    fl = pd.read_parquet(OUT / "flags.parquet"); qm = pd.read_csv(OUT / "quarter_metrics.csv"); comp = pd.read_csv(OUT / "composition.csv")
    try: facts = pd.read_parquet(OUT / "facts_dimensionless.parquet")
    except Exception: facts = pd.DataFrame()
    return fl, qm, comp, facts
fl, qm, comp, facts = load()
quarters = sorted(fl.report_date.unique())
t1, t2, t3, t4 = st.tabs(["Portfolio", "Borrower explorer", "Deterioration flags", "Fund metrics"])

with t1:
    q = st.select_slider("Quarter-end", quarters, value=quarters[-1])
    cur = qm[qm.report_date == q].iloc[0]
    c = st.columns(4); c[0].metric("Total FV ($)", f"{cur.total_fv:,.0f}"); c[1].metric("Borrowers", int(cur.n_borrowers))
    c[2].metric("FV / cost", f"{cur.fv_to_cost:.3f}" if pd.notna(cur.fv_to_cost) else "n/a"); c[3].metric("Top-10 share", f"{cur.top10_share:.1%}" if pd.notna(cur.top10_share) else "n/a")
    st.plotly_chart(px.line(qm, x="report_date", y=["total_fv", "total_cost"], title="Fair value vs cost"), use_container_width=True)
    st.plotly_chart(px.line(qm, x="report_date", y=["n_borrowers", "n_instruments"], title="Portfolio companies / instruments"), use_container_width=True)
    dim = st.selectbox("Composition by", sorted(comp.dimension.unique()))
    cd = comp[comp.dimension == dim]
    a, b = st.columns(2)
    a.plotly_chart(px.pie(cd[cd.report_date == q], names="category", values="fair_value", title=f"{dim} at {q}"), use_container_width=True)
    b.plotly_chart(px.area(cd, x="report_date", y="fair_value", color="category", title=f"{dim} over time"), use_container_width=True)
    snap = fl[fl.report_date == q].groupby("borrower").fair_value.sum().nlargest(15).reset_index()
    st.plotly_chart(px.bar(snap, x="fair_value", y="borrower", orientation="h", title="Top 15 borrowers"), use_container_width=True)

with t2:
    b = st.selectbox("Borrower", sorted(fl.borrower.dropna().unique())); bd = fl[fl.borrower == b]
    st.dataframe(bd[["report_date", "instrument", "instrument_id", "par", "cost", "fair_value", "ref_rate", "spread", "interest_rate", "maturity_date", "source_url"]], use_container_width=True)
    m = bd.melt(["report_date", "instrument_id"], ["par", "cost", "fair_value"])
    st.plotly_chart(px.line(m, x="report_date", y="value", color="instrument_id", line_dash="variable", markers=True), use_container_width=True)
    st.plotly_chart(px.line(bd, x="report_date", y="spread", color="instrument_id", markers=True, title="Spread (%)"), use_container_width=True)
    st.plotly_chart(px.scatter(bd, x="report_date", y="maturity_date", color="instrument_id", title="Maturity date over time"), use_container_width=True)

with t3:
    q3 = st.selectbox("Quarter", quarters[::-1]); d3 = fl[(fl.report_date == q3) & (fl.flag_count > 0)].sort_values("flag_count", ascending=False)
    st.caption("Monitoring flags only. Thresholds in flags.py. Marks are mostly Level 3 estimates; disclosures lag.")
    st.dataframe(d3[["borrower", "instrument", "fair_value", "fv_cost", "fv_par", "fv_cost_qoq_pts"] + [c for c in d3 if c.startswith("flag_")]], use_container_width=True)

with t4:
    if facts.empty: st.info("No dimensionless XBRL facts (Era A filings need the manual CSV, see README).")
    else:
        concepts = sorted(facts.concept.unique())
        pick = st.selectbox("Concept (search: NetAssets, PerShare, Proceeds, Payments, Distribution, Repurchase ...)", concepts)
        fx = facts[facts.concept == pick]; fx = fx.assign(period=fx.instant.fillna(fx.start + " to " + fx.end))
        st.dataframe(fx[["report_date", "period", "value", "unit", "text"]], use_container_width=True)
        st.plotly_chart(px.bar(fx, x="report_date", y="value"), use_container_width=True)
    try: st.dataframe(pd.read_csv(OUT.parent / "manual_fund_metrics.csv"))
    except FileNotFoundError: pass
