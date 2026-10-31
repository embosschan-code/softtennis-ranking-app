# rankings.py
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from datetime import date

st.set_page_config(page_title="ランキング", layout="centered")
st.title("つくば市ソフトテニス レーティングランキング")

db_url = os.getenv("DATABASE_URL", "sqlite:///softtennis.db")
engine = create_engine(db_url)

with engine.begin() as conn:
    players_df = pd.read_sql("SELECT name, rating, gender FROM players", conn)
    matches_df = pd.read_sql(
        "SELECT player1a, player1b, player2a, player2b, score1, score2, match_date, gender FROM matches ORDER BY match_date ASC, id ASC",
        conn
    )

matches_df["match_date"] = pd.to_datetime(matches_df["match_date"])
matches_df["year"] = matches_df["match_date"].dt.year


def calc_ratings_as_of(year=None):
    """year末時点（またはyear=Noneで全期間）のレーティングを再計算して返す"""
    if year is None:
        target_matches = matches_df
    else:
        target_matches = matches_df[matches_df["year"] <= year]

    ratings = {name: 1500.0 for name in players_df["name"]}

    for _, m in target_matches.iterrows():
        p1a, p1b = m["player1a"], m["player1b"]
        p2a, p2b = m["player2a"], m["player2b"]
        s1, s2 = m["score1"], m["score2"]

        r1a = ratings.get(p1a, 1500)
        r1b = ratings.get(p1b, 1500)
        r2a = ratings.get(p2a, 1500)
        r2b = ratings.get(p2b, 1500)

        team1_avg = (r1a + r1b) / 2
        team2_avg = (r2a + r2b) / 2

        if s1 > s2:
            act1, act2 = 1, 0
            margin = max(s1 - s2, 1)
        else:
            act1, act2 = 0, 1
            margin = max(s2 - s1, 1)

        score_bonus = np.log(margin + 1)
        exp1 = 1 / (1 + 10 ** ((team2_avg - team1_avg) / 400))
        exp2 = 1 - exp1
        K = 32

        delta1 = K * score_bonus * (act1 - exp1)
        delta2 = K * score_bonus * (act2 - exp2)

        for p in [p1a, p1b]:
            if p in ratings:
                ratings[p] += delta1
        for p in [p2a, p2b]:
            if p in ratings:
                ratings[p] += delta2

    return ratings


def get_active_players(year=None, gender=None):
    mdf = matches_df.copy()
    if year is not None:
        mdf = mdf[mdf["year"] <= year]
        # その年度に1試合以上出た選手
        active_in_year = matches_df[matches_df["year"] == year]
        participants = set(
            active_in_year["player1a"].tolist() + active_in_year["player1b"].tolist() +
            active_in_year["player2a"].tolist() + active_in_year["player2b"].tolist()
        )
    else:
        participants = set(
            mdf["player1a"].tolist() + mdf["player1b"].tolist() +
            mdf["player2a"].tolist() + mdf["player2b"].tolist()
        )
    return participants


def make_ranking(names, ratings_dict, players_gender=None, gender_filter=None):
    rows = []
    for name in names:
        if name not in ratings_dict:
            continue
        gender = players_df[players_df["name"] == name]["gender"].values
        gender_val = gender[0] if len(gender) > 0 else "共通"
        if gender_filter and gender_filter != "共通":
            if gender_val not in [gender_filter, "共通"]:
                continue
        rows.append({"name": name, "rating": ratings_dict[name], "gender": gender_val})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["順位"] = df["rating"].rank(method="min", ascending=False).astype(int)
    df = df.sort_values(by=["順位", "rating", "name"])
    df = df[["順位", "name", "rating"]].reset_index(drop=True)
    df.columns = ["順位", "選手名", "レーティング"]
    df["レーティング"] = df["レーティング"].round(1)
    return df


def show_ranking_for_year(year, gender_filter):
    """指定年度末時点のレーティングでランキング表示"""
    active = get_active_players(year=year)
    ratings = calc_ratings_as_of(year=year)

    # 性別フィルタ
    if gender_filter and gender_filter != "共通":
        gender_names = players_df[players_df["gender"].isin([gender_filter, "共通"])]["name"].tolist()
        active = active & set(gender_names)

    active_names = [n for n in active if n in ratings]

    if not active_names:
        st.info(f"{year}年度の参加選手データがありません")
        return

    st.caption(f"{year}年度参加者：{len(active_names)}名（{year}年末時点のレーティング）")
    df = make_ranking(active_names, ratings)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_ranking_all(gender_filter):
    """全期間（現在）のレーティング表示"""
    ratings = {row["name"]: row["rating"] for _, row in players_df.iterrows()}

    if gender_filter and gender_filter != "共通":
        names = players_df[players_df["gender"].isin([gender_filter, "共通"])]["name"].tolist()
    else:
        names = players_df["name"].tolist()

    st.caption(f"全登録選手：{len(names)}名（現在のレーティング）")
    df = make_ranking(names, ratings)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_tabs_for_gender(gender_label, gender_filter):
    years = sorted(matches_df["year"].unique().tolist(), reverse=True)
    tab_labels = [f"{y}年度" for y in years] + ["📚 全期間"]
    year_tabs = st.tabs(tab_labels)

    for i, tab in enumerate(year_tabs):
        with tab:
            if i < len(years):
                show_ranking_for_year(years[i], gender_filter)
            else:
                show_ranking_all(gender_filter)


# 男女タブ
gender_tabs = st.tabs(["👨 男子", "👩 女子", "🎾 総合"])

with gender_tabs[0]:
    show_tabs_for_gender("男子", "男子")

with gender_tabs[1]:
    show_tabs_for_gender("女子", "女子")

with gender_tabs[2]:
    show_tabs_for_gender("総合", None)
