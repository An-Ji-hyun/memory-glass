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
def _get_spreadsheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=_SCOPES
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(st.secrets["SHEETS_ID"])


def _get_or_create_ws(title: str, headers: list):
    sh = _get_spreadsheet()
    try:
        return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=2000, cols=len(headers))
        ws.append_row(headers)
        return ws


def _get_sheet():
    return _get_or_create_ws("log", _SHEET_HEADERS)


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


_PRE_SURVEY_HEADERS = [
    "timestamp", "user_id",
    "chatbot_frequency", "chatbots_used", "usage_purpose",
    "expected_memory", "aware_of_memory",
]

_POST_SURVEY_HEADERS = [
    "timestamp", "user_id",
    "memory_awareness", "unexpected_memory", "unexpected_desc",
    "wrong_memory", "wrong_desc", "want_easy_memory", "want_reason",
    "edit_delete_intent", "add_intent", "would_use_crud",
    "useful_feature", "inconvenient", "preferred_display",
    "preferred_timing", "timing_reason", "wanted_feature",
]


def save_pre_survey(user_id: str, data: dict):
    """사전 설문 결과를 pre_survey 탭에 저장."""
    try:
        ws = _get_or_create_ws("pre_survey", _PRE_SURVEY_HEADERS)
        row = [datetime.now().isoformat(), user_id] + [
            json.dumps(data.get(h, ""), ensure_ascii=False)
            if isinstance(data.get(h), list)
            else str(data.get(h, ""))
            for h in _PRE_SURVEY_HEADERS[2:]
        ]
        ws.append_row(row)
    except Exception:
        pass


def save_post_survey(user_id: str, data: dict):
    """사후 설문 결과를 post_survey 탭에 저장."""
    try:
        ws = _get_or_create_ws("post_survey", _POST_SURVEY_HEADERS)
        row = [datetime.now().isoformat(), user_id] + [
            str(data.get(h, "")) for h in _POST_SURVEY_HEADERS[2:]
        ]
        ws.append_row(row)
    except Exception:
        pass


def get_log_df() -> pd.DataFrame:
    logs = st.session_state.get("event_log", [])
    if not logs:
        return pd.DataFrame()
    return pd.DataFrame(logs)
