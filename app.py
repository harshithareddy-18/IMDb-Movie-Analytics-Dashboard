import ast
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# IMDb Movie Analytics Dashboard
# Run: streamlit run app.py
# Keep imdb_top_250.csv in the same folder as this file.
# ------------------------------------------------------------

st.set_page_config(
    page_title="IMDb Movie Analytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark dashboard styling inspired by the supplied reference image.
st.markdown("""
<style>
    .stApp { background: #0b1020; color: #f4f7ff; }
    [data-testid="stSidebar"] { background: #111827; }
    .hero {
        padding: 24px 28px; border-radius: 16px; margin-bottom: 18px;
        background: linear-gradient(105deg, #17243b, #25365a 55%, #412b55);
        border: 1px solid #34445f;
    }
    .hero h1 { margin: 0; color: white; font-size: 2rem; }
    .hero p { margin: 7px 0 0; color: #d5def0; }
    .kpi {
        padding: 16px 18px; border-radius: 13px; min-height: 104px;
        background: linear-gradient(135deg, #173d69, #1767a8);
        border: 1px solid #397bb4;
    }
    .kpi.green { background: linear-gradient(135deg,#126347,#1a9b68); border-color:#279c72; }
    .kpi.purple { background: linear-gradient(135deg,#51328b,#8150c8); border-color:#8b68d0; }
    .kpi.orange { background: linear-gradient(135deg,#a94b0b,#ed8616); border-color:#e99a3b; }
    .kpi-label { color:#e3eafa; font-size: .88rem; }
    .kpi-value { color:white; font-size:1.8rem; font-weight:800; margin-top:5px; }
    .small-note { color:#aab8d0; font-size:.85rem; }
    div[data-testid="stMetric"] {
        background:#17243a; padding:12px 14px; border-radius:12px;
        border:1px solid #2c3d58;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background:#17243a; border-radius:8px 8px 0 0; padding:9px 16px;
    }
    div[data-testid="stDataFrame"] { border:1px solid #2c3d58; border-radius:10px; }
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


def find_col(frame, candidates):
    """Return the first matching column name, ignoring case and spaces."""
    lookup = {str(c).strip().lower(): c for c in frame.columns}
    for name in candidates:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def parse_list(value):
    """Convert genre/country cells such as \"['Drama', 'Crime']\" to a list."""
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    return [x.strip() for x in re.split(r"[,|]", text) if x.strip()]


def money_label(value):
    if pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


# Load the provided CSV. A file uploader is available if the CSV is elsewhere.
default_csv = Path(__file__).with_name("imdb_top_1000.csv")
if not default_csv.exists():
    default_csv = Path(__file__).with_name("imdb_top_250.csv")
uploaded = None
with st.sidebar:
    st.markdown("## 🎞️ IMDb Studio")
    st.caption("Movie Analytics Dashboard")
    uploaded = st.file_uploader("Upload IMDb CSV (optional)", type=["csv"])

try:
    if uploaded is not None:
        raw_df = pd.read_csv(uploaded)
    elif default_csv.exists():
        raw_df = pd.read_csv(default_csv)
    else:
        st.error("Could not find imdb_top_250.csv. Put it beside app.py or upload it in the sidebar.")
        st.stop()
except Exception as exc:
    st.error(f"Unable to load the CSV: {exc}")
    st.stop()

# Resolve dataset columns. The supplied CSV uses snake_case names.
title_col = find_col(raw_df, ["title", "movie_title", "primaryTitle", "Series_Title"])
genre_col = find_col(raw_df, ["genres", "genre", "Genre"])
rating_col = find_col(raw_df, ["averageRating", "average_rating", "imdb_rating", "rating", "IMDB_Rating"])
votes_col = find_col(raw_df, ["numVotes", "num_votes", "votes", "No_of_Votes"])
country_col = find_col(raw_df, ["countriesOfOrigin", "countries", "country", "country_of_origin"])
gross_col = find_col(raw_df, ["grossWorldwide", "gross_worldwide", "worldwide_gross", "Gross"])
runtime_col = find_col(raw_df, ["runtime_minutes", "runtime", "duration", "Runtime"])

if title_col is None:
    st.error("The CSV must contain a movie title column (for example: title).")
    st.stop()

df = raw_df.copy()
df["_title"] = df[title_col].fillna("").astype(str)
df["_genres"] = df[genre_col].apply(parse_list) if genre_col else [[] for _ in range(len(df))]
if rating_col:
    df["_rating"] = pd.to_numeric(df[rating_col], errors="coerce")
if votes_col:
    df["_votes"] = pd.to_numeric(df[votes_col], errors="coerce").fillna(0)
else:
    df["_votes"] = 0
if gross_col:
    # Gross in the supplied IMDb Top 1000 file is comma-formatted text.
    df["_gross"] = pd.to_numeric(
        df[gross_col].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
        errors="coerce",
    )
if country_col:
    df["_countries"] = df[country_col].apply(parse_list)

all_genres = sorted({g for values in df["_genres"] for g in values})
all_countries = sorted({c for values in df["_countries"] for c in values}) if country_col else []
total_movies = len(df)
total_votes = int(df["_votes"].sum())

# Sidebar navigation
with st.sidebar:
    page = st.radio("Navigate", ["Dashboard", "Movie Explorer", "Movie Search"])
    st.divider()
    st.markdown("### Dataset Information")
    st.write(f"**Rows:** {raw_df.shape[0]}")
    st.write(f"**Columns:** {raw_df.shape[1]}")
    st.write(f"**Genres:** {len(all_genres)}")
    st.caption("Loaded successfully from the supplied CSV.")

# ------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------
if page == "Dashboard":
    st.markdown("""
    <div class="hero">
      <h1>🎬 IMDb Movie Analytics Dashboard</h1>
      <p>Explore. Analyze. Discover. &nbsp; | &nbsp; IMDb Movie Collection</p>
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi"><div class="kpi-label">🎞️ Total Movies</div><div class="kpi-value">{total_movies:,}</div></div>', unsafe_allow_html=True)
    with k2:
        avg = df["_rating"].mean() if rating_col else None
        val = f"{avg:.2f}" if pd.notna(avg) else "N/A"
        st.markdown(f'<div class="kpi green"><div class="kpi-label">⭐ Average IMDb Rating</div><div class="kpi-value">{val}</div></div>', unsafe_allow_html=True)
    with k3:
        high = df["_rating"].max() if rating_col else None
        val = f"{high:.1f}" if pd.notna(high) else "N/A"
        st.markdown(f'<div class="kpi purple"><div class="kpi-label">🏆 Highest Rating</div><div class="kpi-value">{val}</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi orange"><div class="kpi-label">👥 Total Votes</div><div class="kpi-value">{total_votes:,}</div></div>', unsafe_allow_html=True)

    st.divider()
    if not rating_col:
        st.warning("Your attached CSV does not contain averageRating. Rating KPIs, rating histogram, rating scatter plot, and rating-based filtering cannot be calculated from this file.")
    if not country_col:
        st.info("Your attached CSV does not contain country/countries. The Explorer will use the available Content Rating field only if present; it will not pretend that this is a country.")
    if not gross_col:
        st.info("Your attached CSV does not contain grossWorldwide, so worldwide-gross rankings cannot be calculated.")

    tab_genre, tab_rating, tab_gross, tab_data = st.tabs(
        ["📊 Genre Analysis", "⭐ Rating Analysis", "💰 Gross Collection", "📁 Dataset Preview"]
    )

    with tab_genre:
        st.subheader("Movies by Genre")
        if all_genres:
            genre_counts = pd.Series([g for values in df["_genres"] for g in values]).value_counts().rename_axis("Genre").reset_index(name="Movies")
            fig = px.bar(genre_counts, x="Genre", y="Movies", color="Genre", title="Number of Movies in Each Genre")
            fig.update_layout(showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No genre column was found in this CSV.")

    with tab_rating:
        st.subheader("IMDb Rating Distribution")
        if rating_col and df["_rating"].notna().any():
            fig = px.histogram(df, x="_rating", nbins=15, title="Distribution of IMDb Ratings", labels={"_rating": "IMDb Rating"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.scatter(df, x="_rating", y="_votes", hover_name="_title", title="IMDb Rating vs Number of Votes", labels={"_rating":"IMDb Rating", "_votes":"Number of Votes"})
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        elif runtime_col:
            st.info("Rating values are absent. Showing the available alternative: Runtime vs Number of Votes.")
            fig = px.scatter(df, x=runtime_col, y="_votes", hover_name="_title", title="Runtime vs Number of Votes")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No IMDb rating column is available in the supplied CSV.")

    with tab_gross:
        st.subheader("Top 10 Movies by Worldwide Gross")
        if gross_col:
            gross_top = df.dropna(subset=["_gross"]).nlargest(10, "_gross").sort_values("_gross")
            fig = px.bar(gross_top, x="_gross", y="_title", orientation="h", title="Top 10 Worldwide Gross Collections", labels={"_gross":"Worldwide Gross (USD)", "_title":"Movie"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("This calculation requires a grossWorldwide column. It is not present in the uploaded CSV.")
            st.dataframe(df[[title_col] + ([genre_col] if genre_col else [])].head(10), use_container_width=True)

    with tab_data:
        st.subheader("First 10 Records")
        st.dataframe(raw_df.head(10), use_container_width=True)
        with st.expander("Dataset Information"):
            st.write(f"**Rows:** {raw_df.shape[0]}")
            st.write(f"**Columns:** {raw_df.shape[1]}")
            st.write("**Column names:**", list(raw_df.columns))
            st.write("**Data types:**")
            st.dataframe(raw_df.dtypes.astype(str).rename("Data type"))
            st.write("**Missing values by column:**")
            st.dataframe(raw_df.isna().sum().rename("Missing values"))
        st.success("Dataset loaded successfully!")

# ------------------------------------------------------------
# Interactive Movie Explorer
# ------------------------------------------------------------
elif page == "Movie Explorer":
    st.markdown('<div class="hero"><h1>🔎 Interactive Movie Explorer</h1><p>Filter, search and sort the IMDb movie dataset</p></div>', unsafe_allow_html=True)

    if st.button("↺ Reset all filters", key="reset_explorer"):
        for key in ["genre_filter", "country_filter", "rating_filter", "votes_filter", "title_filter", "sort_filter"]:
            st.session_state.pop(key, None)
        st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        genre_options = ["All"] + all_genres
        selected_genre = st.selectbox("Genre", genre_options, key="genre_filter")
    with c2:
        if country_col:
            selected_countries = st.multiselect("Countries", all_countries, key="country_filter")
        else:
            selected_countries = []
            st.caption("Country filter unavailable: no country column in this CSV.")
    with c3:
        if rating_col:
            lo = float(df["_rating"].min())
            hi = float(df["_rating"].max())
            rating_range = st.slider("IMDb Rating Range", min_value=lo, max_value=hi, value=(lo, hi), key="rating_filter")
        else:
            rating_range = None
            st.caption("Rating filter unavailable: no averageRating column.")

    c4, c5, c6 = st.columns(3)
    with c4:
        min_votes = st.number_input("Minimum Number of Votes", min_value=0, value=0, step=10000, key="votes_filter")
    with c5:
        search_title = st.text_input("Search Movie Title", key="title_filter")
    with c6:
        sort_order = st.radio("Sort IMDb Rating", ["Descending", "Ascending"], key="sort_filter", horizontal=True) if rating_col else st.radio("Sort by Votes", ["Descending", "Ascending"], key="sort_filter", horizontal=True)

    filtered = df.copy()
    if selected_genre != "All":
        filtered = filtered[filtered["_genres"].apply(lambda items: selected_genre in items)]
    if country_col and selected_countries:
        filtered = filtered[filtered["_countries"].apply(lambda items: any(c in items for c in selected_countries))]
    if rating_col and rating_range:
        filtered = filtered[filtered["_rating"].between(rating_range[0], rating_range[1])]
    filtered = filtered[filtered["_votes"] >= min_votes]
    if search_title.strip():
        filtered = filtered[filtered["_title"].str.contains(search_title.strip(), case=False, na=False)]
    sort_col = "_rating" if rating_col else "_votes"
    filtered = filtered.sort_values(sort_col, ascending=(sort_order == "Ascending"))

    st.divider()
    st.metric("Movies after applying filters", f"{len(filtered):,}")
    st.dataframe(filtered.drop(columns=["_genres"] + (["_countries"] if country_col else []), errors="ignore"), use_container_width=True, hide_index=True)
    st.caption("All filters are applied together to the same filtered DataFrame.")

# ------------------------------------------------------------
# Session state and form handling
# ------------------------------------------------------------
else:
    st.markdown('<div class="hero"><h1>🎯 Movie Search Form</h1><p>Submit preferences and view a matching movie</p></div>', unsafe_allow_html=True)
    if "selected_movie" not in st.session_state:
        st.session_state.selected_movie = None

    genre_options = ["All"] + all_genres
    with st.form("movie_search_form"):
        movie_query = st.text_input("Movie Title", placeholder="Enter a movie title...")
        preferred_genre = st.selectbox("Preferred Genre", genre_options)
        min_rating = st.slider("Minimum IMDb Rating", 0.0, 10.0, 7.0, 0.1, disabled=(rating_col is None))
        submitted = st.form_submit_button("🔍 Search Movie", use_container_width=True)

    if submitted:
        matches = df.copy()
        if movie_query.strip():
            matches = matches[matches["_title"].str.contains(movie_query.strip(), case=False, na=False)]
        if preferred_genre != "All":
            matches = matches[matches["_genres"].apply(lambda items: preferred_genre in items)]
        if rating_col:
            matches = matches[matches["_rating"] >= min_rating]
        if not matches.empty:
            st.session_state.selected_movie = matches.sort_values("_votes", ascending=False).iloc[0].to_dict()
            st.success("Matching movie found!")
        else:
            st.session_state.selected_movie = None
            st.info("No movie matched those preferences. Try another title or genre.")

    if st.session_state.selected_movie is not None:
        movie = st.session_state.selected_movie
        st.subheader("Selected Movie")
        a, b, c = st.columns(3)
        a.metric("Movie Title", str(movie.get("_title", "N/A")))
        b.metric("IMDb Rating", f"{movie.get('_rating', 'N/A'):.1f}" if rating_col and pd.notna(movie.get("_rating")) else "Not in CSV")
        c.metric("Number of Votes", f"{int(movie.get('_votes', 0)):,}")
        st.write("**Genre:**", ", ".join(movie.get("_genres", [])) or "Not available")
        if not rating_col:
            st.warning("The provided CSV has no IMDb rating field. The minimum-rating control is shown but cannot be used to verify or filter ratings.")
        st.dataframe(pd.DataFrame([movie]).drop(columns=["_genres", "_countries"], errors="ignore"), use_container_width=True)
