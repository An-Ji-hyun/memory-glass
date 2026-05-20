"""
logger.py — 세션 이벤트 로그

이벤트를 두 곳에 동시 기록한다:
  1. st.session_state  — 현재 세션 내 빠른 조회용 (새로고침 시 초기화)
  2. Google Sheets      — 영속 저장 (새로고침·세션 종료 후에도 유지)

Sheets 기록 실패 시 앱이 중단되지 않도록 예외를 무시한다.
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

# event_type 종류:
#   session_start    — 세션 시작
#   message_sent     — 사용자 메시지 전송
#   memory_viewed    — 메모리 목록 조회 (Condition A)
#   memory_approved  — 메모리 저장 승인 (Condition A)
#   memory_rejected  — 메모리 저장 거부 (Condition A)
#   memory_deleted   — 메모리 삭제 (Condition A)

_SHEET_HEADERS = ["timestamp", "user_id", "condition", "event_type", "detail"]


@st.cache_resource
def _get_sheet():
    """Google Sheets 워크시트 연결 (앱 전체에서 1회만 생성)."""
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=_SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["SHEETS_ID"])

    # 'log' 시트가 없으면 생성 후 헤더 추가
    try:
        ws = sh.worksheet("log")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="log", rows=5000, cols=len(_SHEET_HEADERS))
        ws.append_row(_SHEET_HEADERS)

    return ws


def _append_to_sheets(entry: dict):
    """Sheets에 한 행 추가. 실패해도 앱은 계속 동작한다."""
    try:
        ws = _get_sheet()
        ws.append_row([entry.get(h, "") for h in _SHEET_HEADERS])
    except Exception:
        pass


def log_event(user_id: str, condition: str, event_type: str, detail: dict = None):
    entry = {
        "timestamp":  datetime.now().isoformat(),
        "user_id":    user_id,
        "condition":  condition,
        "event_type": event_type,
        "detail":     json.dumps(detail or {}, ensure_ascii=False),
    }

    # 1. 세션 내 저장
    if "event_log" not in st.session_state:
        st.session_state["event_log"] = []
    st.session_state["event_log"].append(entry)

    # 2. Google Sheets 영속 저장
    _append_to_sheets(entry)


def get_log_dataframe() -> pd.DataFrame:
    """세션 내 로그를 DataFrame으로 반환. 관리자 패널용."""
    logs = st.session_state.get("event_log", [])
    if not logs:
        return pd.DataFrame()
    return pd.DataFrame(logs)
