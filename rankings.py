# rankings.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

st.set_page_config(page_title="ランキング", layout="centered")
st.title("つくば市ソフトテニス レーティングランキング")

db_url = os.getenv("DATABASE_URL", "sqlite:///softtennis.db")
engine = create_engine(db_url)

with engine.begin() as conn:
    df = pd.read_sql("SELECT name, rating, gender FROM players", conn)

def make_ranking(data):
    data = data.copy()
    data["順位"] = data["rating"].rank(method="min", ascending=False).astype(int)
    data = data.sort_values(by=["順位", "rating", "name"])
    data = data[["順位", "name", "rating"]].reset_index(drop=True)
    data.columns = ["順位", "選手名", "レーティング"]
    return data

genders = df["gender"].unique().tolist()

tab_labels = []
if any(g in genders for g in ["男子", "男性"]):
    tab_labels.append("👨 男子")
if any(g in genders for g in ["女子", "女性"]):
    tab_labels.append("👩 女子")
if not tab_labels or any(g in genders for g in ["共通", "common"]):
    tab_labels.append("🎾 総合")

if len(tab_labels) == 1:
    st.dataframe(make_ranking(df), use_container_width=True, hide_index=True)
else:
    tab_objects = st.tabs(tab_labels)
    for tab, label in zip(tab_objects, tab_labels):
        with tab:
            if "男子" in label:
                filtered = df[df["gender"].isin(["男子", "男性"])]
            elif "女子" in label:
                filtered = df[df["gender"].isin(["女子", "女性"])]
            else:
                filtered = df
            if filtered.empty:
                st.info("データがありません")
            else:
                st.dataframe(make_ranking(filtered), use_container_width=True, hide_index=True)
