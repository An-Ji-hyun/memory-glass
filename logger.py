"""
logger.py — 세션 이벤트 로그

이벤트를 두 곳에 기록:
  1. st.session_state — 현재 세션 내 빠른 조회용
  2. Google Sheets     — 영속 저장

event_type 목록:
  session_start, consent_agreed
  task_started        (detail: {"task": "vacation"/"concern"})
  message_sent        (detail: {"turn": N, "length": N})
  memory_panel_opened (detail: {"memory_count": N})
  memory_viewed       (detail: {"duration_sec": N})
  memory_deleted      (detail: {"memory": "..."})
  memory_edited       (detail: {"old": "...", "new": "..."})
  edit_cancelled      (detail: {"memory": "..."})
  memory_added        (detail: {"memory": "..."})
  session_end
"""

import json
import pandas as pd
import streamlit as st
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_SHEET_HEADERS = ["timestamp", "user_id", "event_type", "detail"]


@st.cache_resource
def _get_sheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=_SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["SHEETS_ID"])

    try:
        ws = sh.worksheet("log")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="log", rows=5000, cols=len(_SHEET_HEADERS))
        ws.append_row(_SHEET_HEADERS)

    return ws


def sync_to_sheets():
    """최신 이벤트 1건을 Sheets에 추가. 실패해도 앱 계속 동작."""
    try:
        logs = st.session_state.get("event_log", [])
        if not logs:
            return
        ws = _get_sheet()
        ws.append_row([logs[-1].get(h, "") for h in _SHEET_HEADERS])
    except Exception:
        pass


def log_event(user_id: str, event_type: str, detail: dict = None):
    entry = {
        "timestamp":  datetime.now().isoformat(),
        "user_id":    user_id,
        "event_type": event_type,
        "detail":     json.dumps(detail or {}, ensure_ascii=False),
    }

    if "event_log" not in st.session_state:
        st.session_state["event_log"] = []
    st.session_state["event_log"].append(entry)

    sync_to_sheets()


def get_log_df() -> pd.DataFrame:
    logs = st.session_state.get("event_log", [])
    if not logs:
        return pd.DataFrame()
    return pd.DataFrame(logs)
