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
from logger import log_event, sync_to_sheets, get_log_df, save_pre_survey, save_post_survey
from surveys import render_pre_survey, render_post_survey

st.set_page_config(page_title="MemoryGlass", page_icon="🧠", layout="wide")

# ── URL 파라미터 ─────────────────────────────────────────────────────────────
params    = st.query_params
uid       = params.get("uid", "guest")
admin_key = st.secrets.get("ADMIN_KEY", "researcher2025")
is_admin  = params.get("admin", "") == admin_key

# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
defaults = {
    "screen":             "consent",  # consent|pre_survey|chat|memory_view|post_survey|complete
    "chat_history":       [],
    "message_count":      0,
    "session_started":    False,
    "consent_given":      False,
    "show_task1_intro":   False,
    "show_task2_intro":   False,
    "show_memory_intro":  False,
    "current_task":       "vacation",
    "task2_start_index":  0,
    "conversation_saved": False,
    "memory_clusters":    None,
    "selected_topic":     0,
    "pre_survey_data":       None,
    "post_survey_data":      None,
    "show_pre_survey_intro": True,
    "event_log":             [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.session_started:
    log_event(uid, "session_start", {"uid": uid})
    st.session_state.session_started = True

# ── 동의서 화면 ──────────────────────────────────────────────────────────────
if st.session_state.screen == "consent":
    st.title("🧠 MemoryGlass 연구 참여 동의")
    st.markdown(f"""
**{uid}님 안녕하세요. 본 연구에 참여해 주셔서 감사합니다.**

**연구 목적:** AI 챗봇 인터페이스 설계 연구

**안내 사항:**
- 대화 내용은 연구 목적으로만 사용됩니다.
- 개인 식별 정보는 수집하지 않습니다.
- 언제든지 참여를 중단할 수 있으며, 정보 폐기를 요청할 수 있습니다.
    """)
    if st.button("✅ 동의하고 시작하기", type="primary"):
        st.session_state.consent_given = True
        st.session_state.screen = "pre_survey"
        log_event(uid, "consent_agreed")
        st.rerun()
    st.stop()

# ── 사전 설문 화면 ────────────────────────────────────────────────────────────
@st.dialog("사전 설문 안내")
def pre_survey_intro_dialog():
    st.markdown("시스템을 사용하기 전 사전 설문을 진행해주세요.")
    if st.button("설문 시작하기", type="primary", key="pre_intro_ok"):
        st.session_state.show_pre_survey_intro = False
        st.rerun()

if st.session_state.screen == "pre_survey":
    if st.session_state.show_pre_survey_intro:
        pre_survey_intro_dialog()
    st.title("🧠 MemoryGlass")
    result = render_pre_survey()
    if result is not None:
        st.session_state.pre_survey_data = result
        st.session_state.screen = "chat"
        st.session_state.show_task1_intro = True
        log_event(uid, "pre_survey_submitted", result)
        save_pre_survey(uid, result)
        log_event(uid, "task_started", {"task": "vacation"})
        st.rerun()
    st.stop()

# ── 사후 설문 화면 ────────────────────────────────────────────────────────────
if st.session_state.screen == "post_survey":
    st.title("🧠 MemoryGlass")
    result = render_post_survey(st.session_state.event_log)
    if result is not None:
        st.session_state.post_survey_data = result
        st.session_state.screen = "complete"
        log_event(uid, "post_survey_submitted", result)
        save_post_survey(uid, result)
        sync_to_sheets()
        st.rerun()
    st.stop()

# ── 완료 화면 ─────────────────────────────────────────────────────────────────
if st.session_state.screen == "complete":
    st.title("🧠 MemoryGlass")
    st.success("모든 과정이 완료되었습니다. 참여해 주셔서 감사합니다! 🎉")
    st.markdown(f"""
**{uid}님, 연구에 참여해 주셔서 진심으로 감사드립니다.**

설문과 대화 내용은 안전하게 저장되었습니다.
연구자의 안내에 따라 다음 단계를 진행해주세요.
    """)
    st.stop()

# ── 다이얼로그 ───────────────────────────────────────────────────────────────
@st.dialog("주제 1 안내")
def task1_intro():
    st.markdown("""
**이번 첫 번째 주제는 여름 휴가 계획입니다.**

챗봇과 자유롭게 대화하며 여름 휴가에 대해 이야기해보세요.

- 어디를 가고 싶은지
- 누구와 함께 가고 싶은지
- 어떻게 시간을 보내고 싶은지

최대 10분 동안 대화할 수 있으며, 도중 연구자가 다음 task 전환 안내를 진행할 수 있습니다. 
다음 task로 전환하는 버튼은 반드시 연구자 동의 후 진행 부탁드립니다. 
그럼 편하게 진행 시작해주세요!
    """)
    if st.button("✅ 시작하기", type="primary", key="task1_start"):
        st.session_state.show_task1_intro = False
        st.rerun()


@st.dialog("주제 2 안내")
def task2_intro():
    st.markdown("""
**이제 두 번째 주제로 넘어갑니다.**

이번에는 요즘 관심 있는 것이나 고민에 대해 이야기해보세요.

- 최근 빠져있는 취미나 관심사
- 요즘 신경 쓰이거나 고민되는 일
- 일상에서 즐겁거나 힘든 것들

최대 10분 동안 대화할 수 있으며, 도중 연구자가 다음 task 완료를 부탁할 수 있습니다. 
완료 버튼은 반드시 연구자 동의 후 진행 부탁드립니다. 
첫 번째 주제와 마찬가지로 편하게 이야기해 주시면 됩니다!
    """)
    if st.button("✅ 시작하기", type="primary", key="task2_start"):
        st.session_state.show_task2_intro = False
        st.rerun()


@st.dialog("다음 주제로 넘어가기")
def confirm_next_topic():
    st.write("연구자의 지시 하에 다음 주제 버튼을 누를 수 있습니다. 넘어가시겠습니까?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("예, 넘어갈게요", type="primary", key="next_yes"):
            with st.spinner("대화 내용을 저장하는 중..."):
                task1_user_msgs = [m for m in st.session_state.chat_history if m["role"] == "user"]
                saved = save_conversation(uid, task1_user_msgs)
            st.session_state.task2_start_index = len(st.session_state.chat_history)
            log_event(uid, "task_started", {"task": "concern", "task1_memories": len(saved)})
            st.session_state.current_task = "concern"
            st.session_state.show_task2_intro = True
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
                task2_user_msgs = [
                    m for m in st.session_state.chat_history[st.session_state.task2_start_index:]
                    if m["role"] == "user"
                ]
                save_conversation(uid, task2_user_msgs)
                all_mems = get_all_memories(uid)
                clusters = cluster_memories_with_sources(all_mems, st.session_state.chat_history)
            st.session_state.conversation_saved = True
            st.session_state.memory_clusters    = clusters
            st.session_state.selected_topic     = 0
            st.session_state.show_memory_intro  = True
            log_event(uid, "memory_panel_opened", {"memory_count": len(all_mems)})
            st.session_state.screen = "memory_view"
            st.rerun()
    with c2:
        if st.button("아니오", key="done_no"):
            st.rerun()


# ── 메모리 화면 전용 다이얼로그 ─────────────────────────────────────────────
@st.dialog("저장된 기억 확인 안내")
def memory_intro_dialog():
    st.markdown("""
챗봇이 대화에서 기억한 내용을 확인할 수 있어요.

**이 기억들은 다음에 이 챗봇을 다시 사용할 때 활용됩니다.**

아래 작업을 자유롭게 해보세요:

- ✏️ **수정** — 잘못 저장된 정보가 있다면 직접 고칠 수 있어요
- 🗑️ **삭제** — 챗봇이 기억하지 않았으면 하는 내용은 삭제할 수 있어요
- ➕ **추가** — 챗봇이 기억할 거라 생각했는데 빠진 내용이 있다면 직접 추가할 수 있어요
- 🏷️ **토픽 변경** — 기억을 다른 토픽으로 옮기거나 새 토픽을 만들 수 있어요
    """)
    if st.button("✅ 확인했어요", type="primary", key="memory_intro_ok"):
        st.session_state.show_memory_intro = False
        st.rerun()


@st.dialog("사후 설문으로 이동")
def confirm_post_survey():
    st.warning("정말로 메모리 수정/추가/삭제를 완료하고 사후 설문으로 넘어가시겠습니까?\n\n**이 작업은 되돌릴 수 없습니다.**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("사후 설문 하러가기", type="primary", key="post_survey_yes"):
            log_event(uid, "memory_review_completed")
            st.session_state.screen = "post_survey"
            st.rerun()
    with c2:
        if st.button("취소", key="post_survey_no"):
            st.rerun()


@st.dialog("새 토픽 추가")
def add_topic_dialog():
    topic_name = st.text_input("토픽 이름", placeholder="예: 음식 취향")
    if st.button("추가하기", type="primary", key="add_topic_confirm"):
        if topic_name.strip():
            st.session_state.memory_clusters.append({
                "label": topic_name.strip(),
                "items": [],
                "count": 0,
            })
            st.session_state.selected_topic = len(st.session_state.memory_clusters) - 1
            log_event(uid, "topic_added", {"label": topic_name.strip()})
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 메모리 분석 화면
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.screen == "memory_view":
    clusters = st.session_state.memory_clusters or []

    # 안내 팝업
    if st.session_state.show_memory_intro:
        memory_intro_dialog()

    # 사이드바
    with st.sidebar:
        st.markdown("## 🧠 MemoryGlass")
        st.divider()
        st.success("✅ 대화 완료")
        st.caption("저장된 기억을 확인하고\n자유롭게 수정해보세요.")
        st.divider()
        if st.button("📋 사후 설문으로 이동", type="primary", use_container_width=True):
            confirm_post_survey()

    st.title("🧠 저장된 기억 분석")

    if not clusters:
        st.info("저장된 기억이 없어요.")
        st.stop()

    total = sum(len(c["items"]) for c in clusters)
    st.caption(f"총 {total}개의 기억이 {len(clusters)}개 토픽으로 분류되었어요.")
    st.divider()

    chart_col, detail_col = st.columns([1, 1.4])
    colors = ["#636EFA","#EF553B","#00CC96","#AB63FA","#FFA15A","#19D3F3","#FF6692"]

    # ── 파이차트 ──────────────────────────────────────────────────────────────
    with chart_col:
        labels = [c["label"] for c in clusters]
        values = [max(len(c["items"]), 0) for c in clusters]
        visible = [(l, v) for l, v in zip(labels, values) if v > 0]

        if visible:
            vl, vv = zip(*visible)
            fig = go.Figure(go.Pie(
                labels=list(vl), values=list(vv), hole=0.45,
                marker_colors=colors[:len(vl)],
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value}개 (%{percent})<extra></extra>",
            ))
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20),
                              showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        # 토픽 선택 버튼
        st.markdown("**토픽 선택**")
        for i, cluster in enumerate(clusters):
            cnt   = len(cluster["items"])
            label = f"{cluster['label']}  ({cnt}개)"
            btype = "primary" if st.session_state.selected_topic == i else "secondary"
            if st.button(label, key=f"topic_btn_{i}", type=btype, use_container_width=True):
                st.session_state.selected_topic = i
                st.rerun()

        st.divider()
        if st.button("＋ 토픽 추가하기", use_container_width=True):
            add_topic_dialog()

    # ── 선택된 토픽 세부 메모리 ───────────────────────────────────────────────
    with detail_col:
        sel = st.session_state.selected_topic
        if sel < len(clusters):
            cluster = clusters[sel]
            st.markdown(f"### 💬 {cluster['label']}")
            st.caption(f"{len(cluster['items'])}개의 기억이 저장되어 있어요.")
            st.divider()

            other_topics = [(j, c["label"]) for j, c in enumerate(clusters) if j != sel]

            for item_idx, item in enumerate(cluster["items"]):
                ikey = f"{sel}_{item_idx}"  # unique key per item position
                edit_flag = f"editing_{ikey}"
                if edit_flag not in st.session_state:
                    st.session_state[edit_flag] = False

                with st.container():
                    st.markdown(f"**{item['text']}**")

                    # 원본 발화
                    if item.get("source"):
                        with st.expander("🔍 원본 발화 확인하기"):
                            st.markdown(f"> {item['source']}")

                    # 수정 폼 (토글 방식)
                    if st.session_state[edit_flag]:
                        new_text = st.text_area("수정 내용", value=item["text"],
                                                key=f"ta_{ikey}", height=70)
                        s1, s2 = st.columns(2)
                        with s1:
                            if st.button("저장", key=f"save_{ikey}", type="primary"):
                                old_text = item["text"]
                                if update_memory(item["id"], new_text):
                                    clusters[sel]["items"][item_idx]["text"] = new_text
                                    log_event(uid, "memory_edited",
                                              {"old": old_text, "new": new_text})
                                    sync_to_sheets()
                                st.session_state[edit_flag] = False
                                st.toast("저장되었습니다.", icon="✅")
                                st.rerun()
                        with s2:
                            if st.button("취소", key=f"cancel_{ikey}"):
                                st.session_state[edit_flag] = False
                                st.rerun()
                    else:
                        c1, c2, c3 = st.columns([2, 2, 1])
                        with c1:
                            if st.button("✏️ 수정하기", key=f"editbtn_{ikey}"):
                                st.session_state[edit_flag] = True
                                st.rerun()
                        with c2:
                            if other_topics:
                                with st.expander("🏷️ 토픽 변경"):
                                    for j, tlabel in other_topics:
                                        if st.button(tlabel, key=f"move_{ikey}_{j}"):
                                            moved = clusters[sel]["items"].pop(item_idx)
                                            clusters[j]["items"].append(moved)
                                            log_event(uid, "memory_moved",
                                                      {"memory": item["text"], "to": tlabel})
                                            st.toast(f"'{tlabel}' 토픽으로 이동했어요.", icon="🏷️")
                                            st.rerun()
                        with c3:
                            if st.button("🗑️", key=f"del_{ikey}"):
                                if item["id"]:
                                    delete_memory(item["id"])
                                    log_event(uid, "memory_deleted", {"memory": item["text"]})
                                    sync_to_sheets()
                                clusters[sel]["items"].pop(item_idx)
                                st.toast("삭제되었습니다.", icon="🗑️")
                                st.rerun()

                    st.divider()

            # 이 토픽에 기억 추가
            st.markdown("#### ➕ 이 토픽에 기억 추가")
            st.caption("챗봇이 기억하지 못한 내용을 직접 추가할 수 있어요.")
            add_text = st.text_area("추가할 내용", key=f"add_input_{sel}", height=70,
                                     placeholder="예: 나는 피자보다 파스타를 더 좋아해")
            if st.button("➕ 추가", key=f"add_btn_{sel}"):
                if add_text.strip():
                    if add_manual_memory(uid, add_text.strip()):
                        clusters[sel]["items"].append({
                            "id":     "",
                            "text":   add_text.strip(),
                            "source": "",
                        })
                        log_event(uid, "memory_added", {"memory": add_text.strip()})
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

# 태스크 안내 팝업
if st.session_state.show_task1_intro:
    task1_intro()
if st.session_state.show_task2_intro:
    task2_intro()

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
        "turn": st.session_state.message_count,
        "length": len(user_input),
        "content": user_input
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
