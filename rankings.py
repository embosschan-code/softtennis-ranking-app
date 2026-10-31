# rankings.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import date

st.set_page_config(page_title="ランキング", layout="centered")
st.title("つくば市ソフトテニス レーティングランキング")

db_url = os.getenv("DATABASE_URL", "sqlite:///softtennis.db")
engine = create_engine(db_url)

with engine.begin() as conn:
    players_df = pd.read_sql("SELECT name, rating, gender FROM players", conn)
    matches_df = pd.read_sql("SELECT player1a, player1b, player2a, player2b, match_date FROM matches", conn)

# 試合に参加した選手名を年度ごとに取得
matches_df["match_date"] = pd.to_datetime(matches_df["match_date"])
matches_df["year"] = matches_df["match_date"].dt.year

def get_active_players(year=None):
    if year is None:
        mdf = matches_df
    else:
        mdf = matches_df[matches_df["year"] == year]
    participants = set(
        mdf["player1a"].tolist() + mdf["player1b"].tolist() +
        mdf["player2a"].tolist() + mdf["player2b"].tolist()
    )
    return participants

def make_ranking(data):
    data = data.copy()
    data["順位"] = data["rating"].rank(method="min", ascending=False).astype(int)
    data = data.sort_values(by=["順位", "rating", "name"])
    data = data[["順位", "name", "rating"]].reset_index(drop=True)
    data.columns = ["順位", "選手名", "レーティング"]
    return data

# 年度リスト（降順）＋全期間
years = sorted(matches_df["year"].unique().tolist(), reverse=True)
current_year = date.today().year

# 男女別サブ関数
def show_by_gender(df):
    genders = df["gender"].unique().tolist()
    has_male = any(g in genders for g in ["男子", "男性"])
    has_female = any(g in genders for g in ["女子", "女性"])

    if has_male and has_female:
        g_tabs = st.tabs(["👨 男子", "👩 女子", "🎾 総合"])
        with g_tabs[0]:
            filtered = df[df["gender"].isin(["男子", "男性"])]
            if not filtered.empty:
                st.dataframe(make_ranking(filtered), use_container_width=True, hide_index=True)
            else:
                st.info("データなし")
        with g_tabs[1]:
            filtered = df[df["gender"].isin(["女子", "女性"])]
            if not filtered.empty:
                st.dataframe(make_ranking(filtered), use_container_width=True, hide_index=True)
            else:
                st.info("データなし")
        with g_tabs[2]:
            st.dataframe(make_ranking(df), use_container_width=True, hide_index=True)
    else:
        if not df.empty:
            st.dataframe(make_ranking(df), use_container_width=True, hide_index=True)
        else:
            st.info("データなし")

# 年度タブ
tab_labels = [f"{y}年度" for y in years] + ["📚 全期間"]
year_tabs = st.tabs(tab_labels)

for i, tab in enumerate(year_tabs):
    with tab:
        if i < len(years):
            year = years[i]
            active = get_active_players(year)
            filtered_df = players_df[players_df["name"].isin(active)]
            if filtered_df.empty:
                st.info(f"{year}年度の参加選手データがありません")
            else:
                st.caption(f"{year}年度大会参加者：{len(filtered_df)}名（レーティングは通算値）")
                show_by_gender(filtered_df)
        else:
            st.caption(f"全登録選手：{len(players_df)}名")
            show_by_gender(players_df)
