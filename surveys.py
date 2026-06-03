"""
surveys.py — 사전/사후 설문 렌더링

render_pre_survey()  → 제출 완료 시 dict 반환, 미제출이면 None
render_post_survey() → 제출 완료 시 dict 반환, 미제출이면 None
"""

import json
import streamlit as st


# ── 헬퍼 ────────────────────────────────────────────────────────────────────
def _parse_events(event_log: list, event_type: str) -> list:
    return [
        json.loads(e["detail"])
        for e in event_log
        if e.get("event_type") == event_type
    ]


def _validate_text(text: str, label: str, errors: list, min_len: int = 10):
    if len(text.strip()) < min_len:
        errors.append(f"'{label}': {min_len}자 이상 입력해주세요. (현재 {len(text.strip())}자)")


# ══════════════════════════════════════════════════════════════════════════════
# 사전 설문
# ══════════════════════════════════════════════════════════════════════════════
def render_pre_survey() -> dict | None:
    st.markdown("## 사전 설문")
    st.caption("모든 질문은 필수 응답입니다. 서술형은 10자 이상 입력해주세요.")
    st.divider()

    # Q1
    st.markdown("**1. 챗봇을 주 몇 회 사용하시나요?**")
    q1 = st.radio("", ["주 1~2회", "주 3~4회", "주 5~7회"],
                  index=None, key="pre_q1", label_visibility="collapsed")

    st.markdown("**2. 어떤 챗봇을 사용하시나요? (복수 선택 가능)**")
    q2 = st.multiselect("", ["ChatGPT", "Claude", "Gemini", "기타"],
                        key="pre_q2", label_visibility="collapsed")
    q2_other = ""
    if "기타" in q2:
        q2_other = st.text_input("기타 챗봇 이름을 입력해주세요.", key="pre_q2_other")

    st.markdown("**3. 챗봇을 사용하는 용도는 무엇인가요? (복수 선택 가능)**")
    q3 = st.multiselect("", ["업무", "학업", "고민 상담", "정보 탐색 (검색, 비교, 조사 등)", "창작", "기타"],
                        key="pre_q3", label_visibility="collapsed")
    q3_other = ""
    if "기타" in q3:
        q3_other = st.text_input("기타 용도를 입력해주세요.", key="pre_q3_other")

    st.markdown("**4. AI 챗봇과 대화하면 본인에 대해 어떤 정보를 기억할 것 같으신가요?**")
    q4 = st.text_area("", key="pre_q4", placeholder="10자 이상 자유롭게 작성해주세요.",
                      label_visibility="collapsed")

    st.markdown("**5. AI 챗봇이 사용자 정보를 기억하는 메모리 기능이 있다는 것을 알고 계셨나요?**")
    q5 = st.radio("", ["예", "아니오"], index=None, key="pre_q5", label_visibility="collapsed")

    st.divider()
    if st.button("설문 제출하기", type="primary", key="pre_submit"):
        errors = []
        if not q1:
            errors.append("Q1: 챗봇 사용 빈도를 선택해주세요.")
        if not q2:
            errors.append("Q2: 사용하는 챗봇을 선택해주세요.")
        if "기타" in q2 and not q2_other.strip():
            errors.append("Q2: 기타 챗봇 이름을 입력해주세요.")
        if not q3:
            errors.append("Q3: 사용 용도를 선택해주세요.")
        if "기타" in q3 and not q3_other.strip():
            errors.append("Q3: 기타 용도를 입력해주세요.")
        _validate_text(q4, "Q4", errors)
        if not q5:
            errors.append("Q5: 메모리 기능 인지 여부를 선택해주세요.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        chatbots = [f"기타({q2_other})" if c == "기타" else c for c in q2]
        usages   = [f"기타({q3_other})" if c == "기타" else c for c in q3]

        return {
            "chatbot_frequency": q1,
            "chatbots_used":     chatbots,
            "usage_purpose":     usages,
            "expected_memory":   q4.strip(),
            "aware_of_memory":   q5,
        }

    return None


# ══════════════════════════════════════════════════════════════════════════════
# 사후 설문
# ══════════════════════════════════════════════════════════════════════════════
def render_post_survey(event_log: list) -> dict | None:
    st.markdown("## 사후 설문")
    st.caption("모든 질문은 필수 응답입니다. 서술형은 10자 이상 입력해주세요.")

    edited_events  = _parse_events(event_log, "memory_edited")
    deleted_events = _parse_events(event_log, "memory_deleted")
    added_events   = _parse_events(event_log, "memory_added")
    topic_events   = _parse_events(event_log, "topic_added")

    answers = {}
    errors  = []

    # ── 메모리 인식 ─────────────────────────────────────────────────────────
    st.markdown("### 📌 메모리 인식")

    st.markdown("**1. 대화하면서 정보가 저장된다고 느꼈나요? 어떤 순간에 느꼈는지 설명해주세요.**")
    q1 = st.text_area("", key="post_q1", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    st.markdown("**2. 저장된 메모리가 예상과 달랐나요?**")
    q2 = st.radio("", ["예", "아니오"], index=None, key="post_q2",
                  label_visibility="collapsed")
    q2_desc = ""
    if q2 == "예":
        st.markdown("어떤 경우가 예상과 달랐는지 설명해주세요.")
        q2_desc = st.text_area("", key="post_q2_desc", placeholder="10자 이상 작성해주세요.",
                               label_visibility="collapsed")

    st.markdown("**3. 잘못 저장된 정보가 있었나요?**")
    q3 = st.radio("", ["예", "아니오"], index=None, key="post_q3",
                  label_visibility="collapsed")
    q3_desc = ""
    if q3 == "예":
        st.markdown("어떤 경우가 잘못 저장되었는지 설명해주세요.")
        q3_desc = st.text_area("", key="post_q3_desc", placeholder="10자 이상 작성해주세요.",
                               label_visibility="collapsed")

    st.markdown("**4. 기존에 사용하는 챗봇에서도 이와 비슷하게 메모리를 쉽게 볼 수 있으면 좋겠나요?**")
    q4 = st.radio("", ["예", "아니오"], index=None, key="post_q4",
                  label_visibility="collapsed")
    st.markdown("이유를 설명해주세요. (예/아니오 모두 필수)")
    q4_reason = st.text_area("", key="post_q4_reason", placeholder="10자 이상 작성해주세요.",
                             label_visibility="collapsed")

    st.divider()

    # ── 통제권 ───────────────────────────────────────────────────────────────
    st.markdown("### 🎛️ 통제권")

    # 수정/삭제 의도 (동적)
    if edited_events or deleted_events:
        st.markdown("**5. 메모리를 수정하거나 삭제하신 항목이 있습니다. 각 항목을 그렇게 하신 이유가 무엇인지 설명해주세요.**")
        if edited_events:
            st.markdown("✏️ **수정하신 항목:**")
            for e in edited_events[:5]:
                st.markdown(f"- 기존: *{e.get('old','')}* → 변경: *{e.get('new','')}*")
        if deleted_events:
            st.markdown("🗑️ **삭제하신 항목:**")
            for e in deleted_events[:5]:
                st.markdown(f"- *{e.get('memory','')}*")
    else:
        st.markdown("**5. 메모리를 수정하거나 삭제하고 싶었던 항목이 있었나요? 있었다면 어떤 이유에서였는지 설명해주세요.**")
    q5 = st.text_area("", key="post_q5", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    # 추가 의도 (동적)
    if topic_events or added_events:
        st.markdown("**6. 새로 추가하신 항목이 있습니다. 각 항목을 추가하신 이유가 무엇인지 설명해주세요.**")
        if topic_events:
            st.markdown("🏷️ **추가하신 토픽:**")
            for e in topic_events[:5]:
                st.markdown(f"- *{e.get('label','')}*")
        if added_events:
            st.markdown("➕ **추가하신 메모리:**")
            for e in added_events[:5]:
                st.markdown(f"- *{e.get('memory','')}*")
    else:
        st.markdown("**6. 챗봇이 기억해줬으면 했는데 저장되지 않은 정보가 있었나요? 있었다면 어떤 내용이었는지, 그리고 왜 기억해주길 바랐는지 설명해주세요.**")
    q6 = st.text_area("", key="post_q6", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    st.markdown("**7. 수정/삭제/추가 기능이 실제로 사용하는 챗봇에 적용된다면 자주 사용할 것 같나요? 이유를 설명해주세요.**")
    q7 = st.text_area("", key="post_q7", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    st.divider()

    # ── 투명성 및 UI 요구사항 ────────────────────────────────────────────────
    st.markdown("### 🖥️ 투명성 및 UI 요구사항")

    st.markdown("**8. 현재 UI에서 유용했던 기능은 무엇인가요? 어떻게 유용했는지 설명해주세요.**")
    q8 = st.text_area("", key="post_q8", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    st.markdown("**9. 불편하거나 부족했던 점은 무엇인가요? 자세히 설명해주세요.**")
    q9 = st.text_area("", key="post_q9", placeholder="10자 이상 작성해주세요.",
                      label_visibility="collapsed")

    st.markdown("**10. 메모리를 어떤 방식으로 보고 싶으세요?**")
    q10 = st.text_area("", key="post_q10", placeholder="예: 목록, 시각화, 타임라인 등 — 10자 이상 작성해주세요.",
                       label_visibility="collapsed")

    st.markdown("**11. 어느 시점에 메모리를 확인하고 싶으세요? (복수 선택 가능) 그 이유도 함께 설명해주세요.**")
    q11_timing = st.multiselect("", ["대화 도중 계속해서 실시간 공개", "내가 원할 때 언제든지", "어느정도 대화를 진행하면 저장 내역 공개 알림", "기타"],
                                key="post_q11_timing", label_visibility="collapsed")
    q11_reason = st.text_area("", key="post_q11_reason", placeholder="이유를 10자 이상 작성해주세요.",
                              label_visibility="collapsed")

    st.markdown("**12. 현재 시스템에 없는 메모리 기능 중 원하는 게 있나요? 그 이유도 설명해주세요.**")
    q12 = st.text_area("", key="post_q12", placeholder="10자 이상 작성해주세요.",
                       label_visibility="collapsed")

    st.divider()
    if st.button("설문 완료하기", type="primary", key="post_submit"):
        _validate_text(q1, "Q1", errors)
        if not q2:
            errors.append("Q2: 예/아니오를 선택해주세요.")
        if q2 == "예":
            _validate_text(q2_desc, "Q2 서술", errors)
        if not q3:
            errors.append("Q3: 예/아니오를 선택해주세요.")
        if q3 == "예":
            _validate_text(q3_desc, "Q3 서술", errors)
        if not q4:
            errors.append("Q4: 예/아니오를 선택해주세요.")
        _validate_text(q4_reason, "Q4 이유", errors)
        _validate_text(q5, "Q5", errors)
        _validate_text(q6, "Q6", errors)
        _validate_text(q7, "Q7", errors)
        _validate_text(q8, "Q8", errors)
        _validate_text(q9, "Q9", errors)
        _validate_text(q10, "Q10", errors)
        if not q11_timing:
            errors.append("Q11: 시점을 하나 이상 선택해주세요.")
        _validate_text(q11_reason, "Q11 이유", errors)
        _validate_text(q12, "Q12", errors)

        if errors:
            for e in errors:
                st.error(e)
            return None

        return {
            "memory_awareness":      q1.strip(),
            "unexpected_memory":     q2,
            "unexpected_desc":       q2_desc.strip(),
            "wrong_memory":          q3,
            "wrong_desc":            q3_desc.strip(),
            "want_easy_memory":      q4,
            "want_reason":           q4_reason.strip(),
            "edit_delete_intent":    q5.strip(),
            "add_intent":            q6.strip(),
            "would_use_crud":        q7.strip(),
            "useful_feature":        q8.strip(),
            "inconvenient":          q9.strip(),
            "preferred_display":     q10.strip(),
            "preferred_timing":      q11_timing,
            "timing_reason":         q11_reason.strip(),
            "wanted_feature":        q12.strip(),
        }

    return None
