# court.py - コート割り当て・試合進行 公開ページ
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import date
from itertools import combinations

st.set_page_config(page_title="コート割り当て", layout="centered")
st.title("🏸 コート割り当て・試合進行")

db_url = os.getenv("DATABASE_URL", "sqlite:///softtennis.db")
engine = create_engine(db_url)

selected_date = st.date_input("📅 日付", value=date.today())

if st.button("🔄 更新"):
    st.rerun()

with engine.begin() as conn:
    sessions_df = pd.read_sql("""
        SELECT phase, court_number, team_number, members, avg_rating
        FROM court_sessions
        WHERE session_date = %s
        ORDER BY phase, court_number, team_number
    """, conn, params=(selected_date,))

    matches_df = pd.read_sql("""
        SELECT phase, court_number, match_number, team_a, team_b, score_a, score_b
        FROM court_matches
        WHERE session_date = %s
        ORDER BY phase, court_number, match_number
    """, conn, params=(selected_date,))

if sessions_df.empty:
    st.info(f"{selected_date.strftime('%Y年%m月%d日')}のデータはまだ登録されていません。")
    st.stop()

st.caption(f"📅 {selected_date.strftime('%Y年%m月%d日')}")

phases = sorted(sessions_df["phase"].unique().tolist())
phase_tabs = st.tabs([f"第{p}フェーズ" for p in phases])

for tab, phase_num in zip(phase_tabs, phases):
    with tab:
        phase_sessions = sessions_df[sessions_df["phase"] == phase_num]
        phase_matches = matches_df[matches_df["phase"] == phase_num]

        # 完了試合数サマリー
        total_m = len(phase_matches)
        done_m = int(phase_matches["score_a"].notna().sum())
        if total_m > 0:
            st.progress(done_m / total_m, text=f"フェーズ進捗：{done_m}/{total_m}試合完了")

        courts = sorted(phase_sessions["court_number"].unique())
        court_tabs = st.tabs([f"🏟️ コート{c}" for c in courts])

        for ctab, court_num in zip(court_tabs, courts):
            with ctab:
                court_sessions = phase_sessions[phase_sessions["court_number"] == court_num]
                court_matches = phase_matches[phase_matches["court_number"] == court_num].sort_values("match_number")

                # チーム一覧 + コート内順位
                team_stats = {}
                for _, row in court_sessions.iterrows():
                    team_stats[row["members"]] = {"wins": 0, "losses": 0, "avg_rating": row["avg_rating"]}

                for _, m in court_matches.iterrows():
                    if pd.notna(m["score_a"]):
                        if m["score_a"] > m["score_b"]:
                            if m["team_a"] in team_stats:
                                team_stats[m["team_a"]]["wins"] += 1
                            if m["team_b"] in team_stats:
                                team_stats[m["team_b"]]["losses"] += 1
                        elif m["score_b"] > m["score_a"]:
                            if m["team_b"] in team_stats:
                                team_stats[m["team_b"]]["wins"] += 1
                            if m["team_a"] in team_stats:
                                team_stats[m["team_a"]]["losses"] += 1

                standings = pd.DataFrame([
                    {
                        "チーム": row["members"],
                        "勝": team_stats.get(row["members"], {}).get("wins", 0),
                        "敗": team_stats.get(row["members"], {}).get("losses", 0),
                        "平均レーティング": round(row["avg_rating"])
                    }
                    for _, row in court_sessions.iterrows()
                ]).sort_values(["勝", "平均レーティング"], ascending=[False, False]).reset_index(drop=True)
                standings.insert(0, "順位", range(1, len(standings) + 1))

                st.markdown("**📊 コート内順位**")
                st.dataframe(standings, use_container_width=True, hide_index=True)

                # 試合進行
                st.markdown("**📋 試合進行**")
                if court_matches.empty:
                    st.info("試合データがありません")
                else:
                    for _, m in court_matches.iterrows():
                        is_done = pd.notna(m["score_a"])
                        if is_done:
                            sa, sb = int(m["score_a"]), int(m["score_b"])
                            if sa > sb:
                                result = f"✅ **{m['team_a']}** {sa} - {sb} {m['team_b']}"
                            elif sb > sa:
                                result = f"✅ {m['team_a']} {sa} - {sb} **{m['team_b']}**"
                            else:
                                result = f"✅ {m['team_a']} {sa} - {sb} {m['team_b']}（引き分け）"
                        else:
                            result = f"⏳ {m['team_a']}  vs  {m['team_b']}"
                        st.markdown(f"第{int(m['match_number'])}試合：{result}")
