"""
app.py — MemoryGlass 메인 앱

URL 파라미터:
    ?uid=P001                        → 참가자 접속
    ?uid=P001&admin=researcher2025   → 연구자 데이터 패널
"""

import streamlit as st
import plotly.graph_objects as go
from chat_engine import generate_response
from memory_engine import (
    save_conversation, get_all_memories,
    cluster_memories_with_sources,
    delete_memory, update_memory, add_manual_memory,
)
from logger import log_event, sync_to_sheets, get_log_df

st.set_page_config(page_title="MemoryGlass", page_icon="🧠", layout="wide")

# ── URL 파라미터 ─────────────────────────────────────────────────────────────
params    = st.query_params
uid       = params.get("uid", "guest")
admin_key = st.secrets.get("ADMIN_KEY", "researcher2025")
is_admin  = params.get("admin", "") == admin_key

# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
defaults = {
    "screen":             "chat",   # "chat" | "memory_view"
    "chat_history":       [],
    "message_count":      0,
    "session_started":    False,
    "consent_given":      False,
    "current_task":       "vacation",
    "task2_start_index":  0,
    "conversation_saved": False,
    "memory_clusters":    None,
    "selected_topic":     0,
    "event_log":          [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.session_started:
    log_event(uid, "session_start", {"uid": uid})
    st.session_state.session_started = True

# ── Phase 0: 동의서 ──────────────────────────────────────────────────────────
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

# ── 다이얼로그 ───────────────────────────────────────────────────────────────
@st.dialog("다음 주제로 넘어가기")
def confirm_next_topic():
    st.write("연구자의 지시 하에 다음 주제 버튼을 누를 수 있습니다. 넘어가시겠습니까?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("예, 넘어갈게요", type="primary", key="next_yes"):
            with st.spinner("대화 내용을 저장하는 중..."):
                saved = save_conversation(uid, st.session_state.chat_history)
            st.session_state.task2_start_index = len(st.session_state.chat_history)
            log_event(uid, "task_started", {"task": "concern", "task1_memories": len(saved)})
            st.session_state.current_task = "concern"
            st.rerun()
    with c2:
        if st.button("아니오", key="next_no"):
            st.rerun()


@st.dialog("대화 완료")
def confirm_complete():
    st.write("연구자의 지시 하에 완료 버튼을 누를 수 있습니다. 완료하시겠습니까?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("예, 완료할게요", type="primary", key="done_yes"):
            with st.spinner("대화 내용을 저장하고 분석하는 중..."):
                task2_msgs = st.session_state.chat_history[st.session_state.task2_start_index:]
                save_conversation(uid, task2_msgs)
                all_mems = get_all_memories(uid)
                clusters = cluster_memories_with_sources(all_mems, st.session_state.chat_history)
            st.session_state.conversation_saved = True
            st.session_state.memory_clusters    = clusters
            st.session_state.selected_topic     = 0
            log_event(uid, "memory_panel_opened", {"memory_count": len(all_mems)})
            st.session_state.screen = "memory_view"
            st.rerun()
    with c2:
        if st.button("아니오", key="done_no"):
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 메모리 분석 화면
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.screen == "memory_view":
    clusters = st.session_state.memory_clusters or []

    # 사이드바
    with st.sidebar:
        st.markdown("## 🧠 MemoryGlass")
        st.divider()
        st.success("✅ 대화 완료")
        st.caption("저장된 기억을 확인하고\n자유롭게 수정해보세요.")

    st.title("🧠 저장된 기억 분석")

    if not clusters:
        st.info("저장된 기억이 없어요.")
        st.stop()

    total = sum(c["count"] for c in clusters)
    st.caption(f"총 {total}개의 기억이 {len(clusters)}개 토픽으로 분류되었어요.")
    st.divider()

    chart_col, detail_col = st.columns([1, 1.4])

    # ── 파이차트 ──────────────────────────────────────────────────────────────
    with chart_col:
        labels  = [c["label"] for c in clusters]
        values  = [c["count"] for c in clusters]
        colors  = ["#636EFA","#EF553B","#00CC96","#AB63FA","#FFA15A"]

        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker_colors=colors[:len(labels)],
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value}개 (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 토픽 선택 버튼
        st.markdown("**토픽 선택**")
        for i, cluster in enumerate(clusters):
            label = f"{cluster['label']}  ({cluster['count']}개)"
            btn_type = "primary" if st.session_state.selected_topic == i else "secondary"
            if st.button(label, key=f"topic_btn_{i}", type=btn_type, use_container_width=True):
                st.session_state.selected_topic = i
                st.rerun()

    # ── 선택된 토픽 세부 메모리 ───────────────────────────────────────────────
    with detail_col:
        sel = st.session_state.selected_topic
        if sel < len(clusters):
            cluster = clusters[sel]
            st.markdown(f"### 💬 {cluster['label']}")
            st.caption(f"{cluster['count']}개의 기억이 저장되어 있어요.")
            st.divider()

            for item in cluster["items"]:
                with st.container():
                    st.markdown(f"**{item['text']}**")
                    if item.get("source"):
                        with st.expander("원본 발화 확인하기"):
                            st.markdown(f"> {item['source']}")

                    c1, c2 = st.columns([3, 1])
                    with c1:
                        with st.expander("✏️ 수정하기"):
                            new_text = st.text_area("", value=item["text"],
                                                     key=f"edit_{item['id']}", height=70)
                            s1, s2 = st.columns(2)
                            with s1:
                                if st.button("저장", key=f"save_{item['id']}"):
                                    if update_memory(item["id"], new_text):
                                        log_event(uid, "memory_edited",
                                                  {"old": item["text"], "new": new_text})
                                        sync_to_sheets()
                                        st.success("수정됨")
                                        st.rerun()
                            with s2:
                                if st.button("취소", key=f"cancel_{item['id']}"):
                                    log_event(uid, "edit_cancelled", {"memory": item["text"]})
                                    st.rerun()
                    with c2:
                        if st.button("🗑️ 삭제", key=f"del_{item['id']}"):
                            if delete_memory(item["id"]):
                                log_event(uid, "memory_deleted", {"memory": item["text"]})
                                sync_to_sheets()
                                st.success("삭제됨")
                                st.rerun()
                    st.divider()

            # 직접 추가
            st.markdown("#### ➕ 기억 직접 추가")
            st.caption("챗봇이 기억했으면 하는 내용을 직접 추가할 수 있어요.")
            add_text = st.text_area("추가할 내용", key="add_input", height=70,
                                     placeholder="예: 나는 피자보다 파스타를 더 좋아해")
            if st.button("➕ 추가"):
                if add_text.strip():
                    if add_manual_memory(uid, add_text):
                        log_event(uid, "memory_added", {"memory": add_text})
                        sync_to_sheets()
                        st.success("추가됨")
                        st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 채팅 화면
# ══════════════════════════════════════════════════════════════════════════════

# 사이드바
with st.sidebar:
    st.markdown("## 🧠 MemoryGlass")
    st.divider()
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

# 메인 채팅
st.title("🧠 MemoryGlass")
st.divider()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("메시지를 입력하세요 💬")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.message_count += 1
    log_event(uid, "message_sent", {
        "turn": st.session_state.message_count, "length": len(user_input)
    })
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner(""):
            response = generate_response(uid, user_input, st.session_state.chat_history[:-1])
        st.write(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()

# ── 연구자 데이터 패널 ────────────────────────────────────────────────────────
if is_admin:
    st.divider()
    st.markdown("## 🔬 연구자 데이터 패널")
    df = get_log_df()
    if df.empty:
        st.info("아직 로그가 없습니다.")
    else:
        summary = df.groupby(["user_id", "event_type"]).size().reset_index(name="count")
        st.dataframe(summary, use_container_width=True)
        with st.expander("전체 로그 보기"):
            st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 CSV 다운로드", csv,
                           f"memoryglass_log_{uid}.csv", "text/csv")
