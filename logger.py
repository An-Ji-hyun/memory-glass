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


# (질문 텍스트, data dict 키) 쌍으로 정의 — 시트 헤더가 질문 그대로 표시됨
_PRE_SURVEY_FIELDS = [
    ("Q1. 챗봇을 주 몇 회 사용하시나요?",                              "chatbot_frequency"),
    ("Q2. 어떤 챗봇을 사용하시나요?",                                  "chatbots_used"),
    ("Q3. 챗봇 사용 용도는?",                                          "usage_purpose"),
    ("Q4. AI 챗봇이 기억할 것 같은 정보는?",                           "expected_memory"),
    ("Q5. 메모리 기능 인지 여부",                                       "aware_of_memory"),
]

_POST_SURVEY_FIELDS = [
    ("Q1. 대화하면서 정보가 저장된다고 느꼈나요?",                      "memory_awareness"),
    ("Q2. 저장된 메모리가 예상과 달랐나요? (예/아니오)",               "unexpected_memory"),
    ("Q2-1. 예상과 달랐던 경우 설명",                                   "unexpected_desc"),
    ("Q3. 잘못 저장된 정보가 있었나요? (예/아니오)",                   "wrong_memory"),
    ("Q3-1. 잘못 저장된 경우 설명",                                     "wrong_desc"),
    ("Q4. 기존 챗봇에서도 메모리를 쉽게 볼 수 있으면 좋겠나요? (예/아니오)", "want_easy_memory"),
    ("Q4-1. 이유",                                                      "want_reason"),
    ("Q5. 수정/삭제 의도",                                              "edit_delete_intent"),
    ("Q6. 추가 의도",                                                   "add_intent"),
    ("Q7. 수정/삭제/추가 기능 실제 사용 의향",                          "would_use_crud"),
    ("Q8. 유용했던 기능",                                               "useful_feature"),
    ("Q9. 불편하거나 부족했던 점",                                      "inconvenient"),
    ("Q10. 선호하는 메모리 표시 방식",                                  "preferred_display"),
    ("Q11. 메모리 확인 시점",                                           "preferred_timing"),
    ("Q11-1. 시점 이유",                                                "timing_reason"),
    ("Q12. 원하는 추가 기능",                                           "wanted_feature"),
]


def save_pre_survey(user_id: str, data: dict):
    """사전 설문 결과를 pre_survey 탭에 저장 (질문 텍스트를 헤더로 사용)."""
    try:
        headers = ["timestamp", "user_id"] + [q for q, _ in _PRE_SURVEY_FIELDS]
        ws = _get_or_create_ws("pre_survey", headers)
        row = [datetime.now().isoformat(), user_id] + [
            json.dumps(data.get(k, ""), ensure_ascii=False)
            if isinstance(data.get(k), list)
            else str(data.get(k, ""))
            for _, k in _PRE_SURVEY_FIELDS
        ]
        ws.append_row(row)
    except Exception:
        pass


def save_post_survey(user_id: str, data: dict):
    """사후 설문 결과를 post_survey 탭에 저장 (질문 텍스트를 헤더로 사용)."""
    try:
        headers = ["timestamp", "user_id"] + [q for q, _ in _POST_SURVEY_FIELDS]
        ws = _get_or_create_ws("post_survey", headers)
        row = [datetime.now().isoformat(), user_id] + [
            str(data.get(k, "")) for _, k in _POST_SURVEY_FIELDS
        ]
        ws.append_row(row)
    except Exception:
        pass


def get_log_df() -> pd.DataFrame:
    logs = st.session_state.get("event_log", [])
    if not logs:
        return pd.DataFrame()
    return pd.DataFrame(logs)
