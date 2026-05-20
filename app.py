"""
app.py — MemoryGlass 메인 앱

실행: streamlit run app.py
배포: Streamlit Cloud (secrets.toml에 OPENAI_API_KEY, MEM0_API_KEY 입력)

URL 파라미터:
    ?uid=P001&cond=A  → Condition A (메모리 투명/통제 가능)
    ?uid=P007&cond=B  → Condition B (메모리 자동/불투명)
    ?admin=true       → 연구자 로그 확인 패널
"""

import streamlit as st
from agent import generate_response, extract_memories_preview
from memory_engine import add_memory
from logger import log_event, get_log_dataframe
from ui_components import (
    render_memory_approval,
    render_memory_panel,
    render_memory_chatcommand,
)

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MemoryGlass", layout="wide")

# ── URL 파라미터 파싱 ────────────────────────────────────────────────────────
params   = st.query_params
uid      = params.get("uid", "guest")
cond_raw = params.get("cond", "B")
cond     = cond_raw.upper() if cond_raw.upper() in ("A", "B") else "B"
is_admin = params.get("admin", "").lower() == "true"

# ── 관리자 패널 ──────────────────────────────────────────────────────────────
if is_admin:
    st.title("MemoryGlass — 연구자 로그")
    df = get_log_dataframe()
    if df.empty:
        st.info("기록된 로그가 없습니다.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, "memoryglass_log.csv", "text/csv")
    st.stop()

# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_memories" not in st.session_state:
    st.session_state.pending_memories = []
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "message_count" not in st.session_state:
    st.session_state.message_count = 0

# 세션 시작 로그 (1회만)
if not st.session_state.session_started:
    log_event(uid, cond, "session_start", {"uid": uid, "condition": cond})
    st.session_state.session_started = True

# ── Condition A: 사이드바 메모리 패널 ────────────────────────────────────────
if cond == "A":
    render_memory_panel(uid, cond)

# ── 메인 화면 ────────────────────────────────────────────────────────────────
st.title("MemoryGlass")

if cond == "A":
    st.caption("이 챗봇은 대화 내용을 기억합니다. 왼쪽 패널에서 기억을 확인하고 삭제할 수 있어요.")
else:
    st.caption("일상 고민이나 이야기를 편하게 나눠보세요.")

# ── 대화 이력 출력 ───────────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Condition A: 메모리 승인 UI ──────────────────────────────────────────────
if cond == "A" and st.session_state.pending_memories:
    result = render_memory_approval(uid, cond, st.session_state.pending_memories)
    if result is not None:
        # 확정 버튼이 눌린 경우 (빈 리스트도 포함)
        if result:
            messages_to_save = [{"role": "user", "content": m} for m in result]
            add_memory(uid, messages_to_save)
        st.session_state.pending_memories = []
        st.rerun()

# ── 사용자 입력 ──────────────────────────────────────────────────────────────
user_input = st.chat_input("메시지를 입력하세요")

if user_input:
    # Condition A: 자연어 메모리 명령 처리
    if cond == "A":
        handled = render_memory_chatcommand(user_input, uid, cond)
        if handled:
            st.stop()

    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(user_input)

    log_event(uid, cond, "message_sent", {"length": len(user_input)})
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # 응답 생성
    with st.chat_message("assistant"):
        with st.spinner(""):
            response = generate_response(uid, user_input, st.session_state.chat_history)
        st.write(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.session_state.message_count += 1

    # ── 메모리 처리 (3턴마다) ────────────────────────────────────────────────
    if st.session_state.message_count % 3 == 0:
        recent_msgs = st.session_state.chat_history[-6:]

        if cond == "A":
            # 저장 전 미리보기 → 사용자 승인 대기
            previews = extract_memories_preview(uid, recent_msgs)
            if previews:
                st.session_state.pending_memories = previews
        else:
            # Condition B: 자동 저장 (사용자에게 알리지 않음)
            add_memory(uid, recent_msgs)

    st.rerun()
