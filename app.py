# app.py

import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------
# 1. PAGE CONFIG
# -------------------------------------------------------
st.set_page_config(
    page_title="AmbitionBox Job Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 AmbitionBox Job Analysis Dashboard")

# -------------------------------------------------------
# 2. LOAD DATA
#    Uses your CSV: ambitionbox_company_reviews_ratings.csv
# -------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("ambitionbox_company_reviews_ratings.csv")
    # Standardize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

df = load_data()

# After renaming, columns are:
# name, rating, rating_count, description, highly_rated_for
# Convert numeric-looking columns
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

# Clean rating_count like "(1.1L)" -> numeric approx (e.g. 110000)
def parse_rating_count(x: str):
    if pd.isna(x):
        return None
    x = str(x).strip("()").lower()
    try:
        if "k" in x:
            return float(x.replace("k", "")) * 1000
        if "l" in x:
            return float(x.replace("l", "")) * 100000
        return float(x)
    except ValueError:
        return None

df["rating_count_num"] = df["rating_count"].apply(parse_rating_count)

# Drop rows without rating
df = df.dropna(subset=["rating"])

# -------------------------------------------------------
# 3. SIDEBAR FILTERS
# -------------------------------------------------------
st.sidebar.header("Filters")

# Rating range
min_rating = float(df["rating"].min())
max_rating = float(df["rating"].max())
rating_range = st.sidebar.slider(
    "Rating range",
    min_value=min_rating,
    max_value=max_rating,
    value=(min_rating, max_rating),
    step=0.1
)

# Filter by “highly_rated_for” (multiple selection)
options_high = (
    df["highly_rated_for"]
    .dropna()
    .apply(lambda x: [s.strip() for s in str(x).split(",")])
)
all_tags = sorted({tag for sub in options_high for tag in sub})
selected_tags = st.sidebar.multiselect(
    "Highly rated for (tags)",
    options=all_tags,
    default=[]
)

# Output choice
output_type = st.sidebar.radio(
    "Select Output",
    ["Show Visualizations", "Show Table"],
    index=0
)

# -------------------------------------------------------
# 4. APPLY FILTERS
# -------------------------------------------------------
filtered_df = df[
    (df["rating"] >= rating_range[0]) &
    (df["rating"] <= rating_range[1])
].copy()

if selected_tags:
    def has_tag(cell):
        if pd.isna(cell):
            return False
        tags = [s.strip() for s in str(cell).split(",")]
        return any(t in tags for t in selected_tags)

    filtered_df = filtered_df[filtered_df["highly_rated_for"].apply(has_tag)]

st.markdown(
    f"### Total Companies After Filter: **{filtered_df['name'].nunique()}**"
)

# -------------------------------------------------------
# 5. METRICS
# -------------------------------------------------------
col_m1, col_m2, col_m3 = st.columns(3)

avg_rating = filtered_df["rating"].mean()
col_m1.metric(
    "Average Rating",
    f"{avg_rating:.2f}" if pd.notna(avg_rating) else "NA"
)

if not filtered_df.empty:
    top_row = filtered_df.loc[filtered_df["rating"].idxmax()]
    col_m2.metric(
        "Top Rated Company",
        top_row["name"],
        f"{top_row['rating']:.1f}"
    )
else:
    col_m2.metric("Top Rated Company", "NA")

total_reviews = filtered_df["rating_count_num"].sum()
col_m3.metric(
    "Approx. Total Ratings Count",
    f"{int(total_reviews):,}" if pd.notna(total_reviews) else "NA"
)

# -------------------------------------------------------
# 6. VISUALIZATIONS
# -------------------------------------------------------
if output_type == "Show Visualizations":

    # Row 1: Rating distribution + Ratings count distribution
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Distribution of Company Ratings")
        fig_rating = px.histogram(
            filtered_df,
            x="rating",
            nbins=15,
            color_discrete_sequence=["royalblue"]
        )
        fig_rating.update_layout(
            xaxis_title="Rating",
            yaxis_title="Number of Companies"
        )
        st.plotly_chart(fig_rating, use_container_width=True)

    with c2:
        st.subheader("Distribution of Ratings Count")
        fig_count = px.histogram(
            filtered_df.dropna(subset=["rating_count_num"]),
            x="rating_count_num",
            nbins=15,
            color_discrete_sequence=["darkorange"]
        )
        fig_count.update_layout(
            xaxis_title="Number of Ratings (approx.)",
            yaxis_title="Number of Companies"
        )
        st.plotly_chart(fig_count, use_container_width=True)

    # Row 2: Top companies by rating + rating vs rating_count scatter
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Top 20 Companies by Rating")
        top20 = (
            filtered_df
            .sort_values(["rating", "rating_count_num"], ascending=[False, False])
            .head(20)
        )
        fig_top = px.bar(
            top20,
            x="name",
            y="rating",
            color="rating",
            color_continuous_scale="Blues"
        )
        fig_top.update_layout(
            xaxis_title="Company",
            yaxis_title="Rating",
            xaxis_tickangle=45
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with c4:
        st.subheader("Rating vs Ratings Count")
        fig_scatter = px.scatter(
            filtered_df.dropna(subset=["rating_count_num"]),
            x="rating",
            y="rating_count_num",
            hover_name="name",
            color="rating",
            color_continuous_scale="Viridis"
        )
        fig_scatter.update_layout(
            xaxis_title="Rating",
            yaxis_title="Number of Ratings (approx.)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Row 3: Pie chart of “highly rated for”
    st.subheader("What Are Companies Highly Rated For?")
    tags_series = (
        filtered_df["highly_rated_for"]
        .dropna()
        .apply(lambda x: [s.strip() for s in str(x).split(",")])
    )

    all_items = []
    for lst in tags_series:
        all_items.extend(lst)

    if all_items:
        tag_counts = pd.Series(all_items).value_counts().reset_index()
        tag_counts.columns = ["tag", "count"]
        fig_pie = px.pie(
            tag_counts,
            names="tag",
            values="count",
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No 'highly rated for' information available after filters.")

# -------------------------------------------------------
# 7. TABLE VIEW
# -------------------------------------------------------
else:
    st.subheader("Filtered Company Data")
    st.dataframe(filtered_df[["name", "rating", "rating_count", "description", "highly_rated_for"]])

