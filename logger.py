"""
logger.py — 세션 내 이벤트 로그

사용자 행동을 st.session_state에 누적 저장한다.
연구 종료 후 관리자 패널에서 CSV로 다운로드해 분석에 사용한다.
"""

import json
import pandas as pd
import streamlit as st
from datetime import datetime

# event_type 종류:
#   session_start    — 세션 시작
#   message_sent     — 사용자 메시지 전송
#   memory_viewed    — 메모리 목록 조회 (Condition A)
#   memory_approved  — 메모리 저장 승인 (Condition A)
#   memory_rejected  — 메모리 저장 거부 (Condition A)
#   memory_deleted   — 메모리 삭제 (Condition A)


def log_event(user_id: str, condition: str, event_type: str, detail: dict = None):
    if "event_log" not in st.session_state:
        st.session_state["event_log"] = []

    st.session_state["event_log"].append({
        "timestamp": datetime.now().isoformat(),
        "user_id":   user_id,
        "condition": condition,
        "event_type": event_type,
        "detail":    json.dumps(detail or {}, ensure_ascii=False)
    })


def get_log_dataframe() -> pd.DataFrame:
    logs = st.session_state.get("event_log", [])
    if not logs:
        return pd.DataFrame()
    return pd.DataFrame(logs)
