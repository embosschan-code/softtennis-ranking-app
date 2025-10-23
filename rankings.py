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
    df = pd.read_sql("SELECT name, rating FROM players", conn)
    df["順位"] = df["rating"].rank(method="min", ascending=False).astype(int)
    df = df.sort_values(by=["順位", "rating", "name"])
    df = df[["順位", "name", "rating"]].reset_index(drop=True)

st.dataframe(df, use_container_width=True, hide_index=True)