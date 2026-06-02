"""
app.py — MemoryGlass 메인 앱

실행: streamlit run app.py

URL 파라미터:
    ?uid=P001                        → 참가자 접속
    ?uid=P001&admin=researcher2025   → 연구자 데이터 패널 접속
"""

import streamlit as st
from datetime import datetime
from chat_engine import generate_response
from memory_engine import save_conversation, get_all_memories, delete_memory, update_memory, add_manual_memory
from logger import log_event, sync_to_sheets, get_log_df

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MemoryGlass", page_icon="🧠", layout="wide")

# ── URL 파라미터 파싱 ────────────────────────────────────────────────────────
params    = st.query_params
uid       = params.get("uid", "guest")
admin_key = st.secrets.get("ADMIN_KEY", "researcher2025")
is_admin  = params.get("admin", "") == admin_key

# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
defaults = {
    "chat_history":       [],
    "message_count":      0,
    "session_started":    False,
    "consent_given":      False,
    "current_task":       "vacation",
    "memory_panel_open":  False,
    "memory_open_time":   None,
    "conversation_saved": False,
    "event_log":          [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 세션 시작 로그 (1회만)
if not st.session_state.session_started:
    log_event(uid, "session_start", {"uid": uid})
    st.session_state.session_started = True

# ── Phase 0: 동의서 화면 ─────────────────────────────────────────────────────
if not st.session_state.consent_given:
    st.title("🧠 MemoryGlass 연구 참여 동의")

    st.markdown("""
본 연구에 참여해 주셔서 감사합니다.

**연구 목적:** AI 챗봇 인터페이스 설계 연구

**안내 사항:**
- 대화 내용은 연구 목적으로만 사용됩니다.
- 개인 식별 정보는 수집하지 않습니다.
- 언제든지 참여를 중단할 수 있으며, 정보 폐기를 요청할 수 있습니다.
    """)

    if st.button("✅ 동의하고 시작하기", type="primary"):
        st.session_state.consent_given = True
        log_event(uid, "consent_agreed")
        log_event(uid, "task_started", {"task": "vacation"})
        st.rerun()

    st.stop()

# ── 다이얼로그 정의 ──────────────────────────────────────────────────────────
@st.dialog("다음 주제로 넘어가기")
def confirm_next_topic():
    st.write("연구자의 지시 하에 다음 주제 버튼을 누를 수 있습니다. 넘어가시겠습니까?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("예, 넘어갈게요", type="primary", key="confirm_next_yes"):
            with st.spinner("대화 내용을 저장하는 중..."):
                saved = save_conversation(uid, st.session_state.chat_history)
            log_event(uid, "task_started", {"task": "concern", "task1_memories": len(saved)})
            st.session_state.current_task = "concern"
            st.rerun()
    with col2:
        if st.button("아니오", key="confirm_next_no"):
            st.rerun()


@st.dialog("대화 완료")
def confirm_complete():
    st.write("연구자의 지시 하에 완료 버튼을 누를 수 있습니다. 완료하시겠습니까?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("예, 완료할게요", type="primary", key="confirm_done_yes"):
            with st.spinner("대화 내용을 저장하는 중..."):
                saved = save_conversation(uid, st.session_state.chat_history)
            st.session_state.conversation_saved = True
            st.session_state.memory_panel_open = True
            st.session_state.memory_open_time = datetime.now()
            log_event(uid, "memory_panel_opened", {"memory_count": len(saved)})
            st.rerun()
    with col2:
        if st.button("아니오", key="confirm_done_no"):
            st.rerun()


# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 MemoryGlass")
    st.divider()

    if not st.session_state.memory_panel_open:
        # 현재 태스크 표시
        if st.session_state.current_task == "vacation":
            st.markdown("**현재 주제**")
            st.info("💬 주제 1\n\n여름 휴가 계획")
            st.caption("어디를 가고 싶은지, 누구와 갈지,\n어떻게 보내고 싶은지 편하게 이야기해보세요.")
            st.divider()
            if st.button("📌 다음 주제로 넘어가기", use_container_width=True):
                confirm_next_topic()
        else:
            st.markdown("**현재 주제**")
            st.info("💬 주제 2\n\n요즘 관심사 / 고민")
            st.caption("요즘 관심 있는 것이나\n신경 쓰이는 일을 편하게 이야기해보세요.")
            st.divider()
            if st.button("✅ 대화 완료", type="primary", use_container_width=True):
                confirm_complete()
    else:
        st.success("✅ 대화 완료")
        st.caption("오른쪽에서 저장된 기억을\n확인하고 수정해보세요.")


# ── 레이아웃: 패널 열림 여부에 따라 컬럼 분할 ────────────────────────────────
if st.session_state.memory_panel_open:
    chat_col, mem_col = st.columns([1.1, 1])
else:
    chat_col = st.container()
    mem_col  = None

# ══════════════════════════════════════════════════════════════════════════════
# 채팅 영역
# ══════════════════════════════════════════════════════════════════════════════
with chat_col:
    st.title("🧠 MemoryGlass")

    st.divider()

    # 대화 이력 출력
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 메모리 패널 열린 후 입력창 비활성화
    if st.session_state.memory_panel_open:
        st.info("💾 대화가 종료되었습니다. 오른쪽에서 저장된 기억을 확인해보세요.")
    else:
        user_input = st.chat_input("메시지를 입력하세요 💬")

        if user_input:
            with st.chat_message("user"):
                st.write(user_input)

            st.session_state.message_count += 1
            log_event(uid, "message_sent", {
                "turn":   st.session_state.message_count,
                "length": len(user_input)
            })

            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )

            with st.chat_message("assistant"):
                with st.spinner(""):
                    response = generate_response(
                        uid,
                        user_input,
                        st.session_state.chat_history[:-1]
                    )
                st.write(response)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": response}
            )

            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 메모리 패널 (완료 후)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.memory_panel_open and mem_col:
    with mem_col:
        st.markdown("## 🧠 저장된 기억")
        st.caption("챗봇이 대화에서 기억한 내용입니다. 자유롭게 확인하고 수정해보세요.")

        if st.button("🔄 새로고침"):
            if st.session_state.memory_open_time:
                duration = (datetime.now() - st.session_state.memory_open_time).seconds
                log_event(uid, "memory_viewed", {"duration_sec": duration})
            st.rerun()

        memories = get_all_memories(uid)

        if not memories:
            st.info("저장된 기억이 없어요.")
        else:
            st.caption(f"총 {len(memories)}개의 기억이 저장되어 있어요.")
            st.divider()

            for mem in memories:
                mid   = mem.get("id", "")
                mtext = mem.get("memory", "")
                if not mtext:
                    continue

                with st.container():
                    st.markdown(f"**{mtext}**")

                    c1, c2 = st.columns([3, 1])

                    with c1:
                        with st.expander("✏️ 수정하기"):
                            new_text = st.text_area(
                                "내용 수정",
                                value=mtext,
                                key=f"edit_{mid}",
                                height=70
                            )
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                if st.button("저장", key=f"save_{mid}"):
                                    if update_memory(mid, new_text):
                                        log_event(uid, "memory_edited",
                                                  {"old": mtext, "new": new_text})
                                        sync_to_sheets()
                                        st.success("수정됨")
                                        st.rerun()
                            with sc2:
                                if st.button("취소", key=f"cancel_{mid}"):
                                    log_event(uid, "edit_cancelled", {"memory": mtext})
                                    st.rerun()

                    with c2:
                        if st.button("🗑️ 삭제", key=f"del_{mid}"):
                            if delete_memory(mid):
                                log_event(uid, "memory_deleted", {"memory": mtext})
                                sync_to_sheets()
                                st.success("삭제됨")
                                st.rerun()

                    st.divider()

        # 직접 추가
        st.markdown("#### ➕ 기억 직접 추가")
        st.caption("챗봇이 기억했으면 하는 내용을 직접 추가할 수 있어요.")
        add_text = st.text_area(
            "추가할 내용",
            key="add_input",
            height=70,
            placeholder="예: 나는 피자보다 파스타를 더 좋아해"
        )
        if st.button("➕ 추가"):
            if add_text.strip():
                if add_manual_memory(uid, add_text):
                    log_event(uid, "memory_added", {"memory": add_text})
                    sync_to_sheets()
                    st.success("추가됨")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 연구자 데이터 패널 (관리자만, 별도 URL로 접속)
# ══════════════════════════════════════════════════════════════════════════════
if is_admin:
    st.divider()
    st.markdown("## 🔬 연구자 데이터 패널")

    df = get_log_df()
    if df.empty:
        st.info("아직 로그가 없습니다.")
    else:
        summary = df.groupby(["user_id", "event_type"]).size().reset_index(name="count")
        st.markdown("### 이벤트 요약")
        st.dataframe(summary, use_container_width=True)

        with st.expander("전체 로그 보기"):
            st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 CSV 다운로드",
            data=csv,
            file_name=f"memoryglass_log_{uid}.csv",
            mime="text/csv"
        )
