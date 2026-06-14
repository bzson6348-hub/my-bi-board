import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide")
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V6)")

# ==========================================
# 0. 세션 상태(메모리) 초기화 - 전체 로딩 방지용
# ==========================================
if "feedbacks" not in st.session_state:
    st.session_state.feedbacks = []
if "prompts" not in st.session_state:
    st.session_state.prompts = {}
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# ==========================================
# 1. 사이드바 설정
# ==========================================
st.sidebar.header("🔑 인증 및 기본 설정")
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 분석 세부 설정")

ip_style = st.sidebar.selectbox(
    "게임 IP의 주요 분위기",
    ["원작 충실형 (다크 판타지/라이트노벨)", "캐주얼/귀여움", "수집형 RPG/화려함", "직접 입력"]
)
if ip_style == "직접 입력":
    ip_style = st.sidebar.text_input("IP 분위기를 직접 입력하세요", "예: SF 메카닉 일러스트 기반")

analysis_direction = st.sidebar.radio(
    "🧭 피드백 집중 방향성 선택", 
    ["BI보드 데이터 기반", "완전히 새로운 시도"]
)

specific_hint = ""
if analysis_direction == "완전히 새로운 시도":
    specific_hint = st.sidebar.text_input(
        "🎯 타겟 시즌/이벤트/밈 (선택 입력)", 
        placeholder="예: 여름 비키니, 추석/설날 연휴, 최신 유행 밈"
    )

additional_context = st.sidebar.text_area("🤖 추가 강조 지시사항 (선택)", placeholder="예: 이번엔 카피를 최대한 줄여줘.")

# ==========================================
# 2. 데이터 처리 및 상위 배너 추출
# ==========================================
uploaded_file = st.file_uploader("BI 보드 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file and api_key:
    client = genai.Client(api_key=api_key)
    df = pd.read_csv(uploaded_file)
    
    df_sorted = df.sort_values(by=['first_pay_cv', 'roas'], ascending=[False, False]).reset_index(drop=True)
    top_n = min(4, len(df_sorted))
    top_banners = df_sorted.head(top_n)
    
    @st.cache_data(show_spinner=False)
    def download_image(url):
        try:
            response = requests.get(url, timeout=5)
            return Image.open(BytesIO(response.content))
        except:
            return None

    st.subheader(f"🏆 성과 최상위 TOP {top_n} 배너 (첫결제 건수 우선)")
    cols = st.columns(top_n)
    valid_imgs = []
    
    with st.spinner("이미지를 불러오는 중..."):
        for i, row in enumerate(top_banners.itertuples()):
            img = download_image(row.url)
            with cols[i]:
                if img:
                    st.image(img, use_container_width=True)
                    valid_imgs.append(img)
                st.caption(f"**TOP {i+1}** | 첫결제: {row.first_pay_cv} | ROAS: {row.roas}")

    if valid_imgs:
        banner_data_summary = "\n".join([f"- TOP {idx+1}: 첫결제 {row.first_pay_cv}건, ROAS {row.roas}" for idx, row in enumerate(top_banners.itertuples())])
        
        # ==========================================
        # 3. [개선] 분석 실행 버튼 (설정 변경 시에만 누르기)
        # ==========================================
        st.markdown("---")
        if st.button("🚀 AI 피드백 분석 실행 (설정이 바뀌면 다시 누르세요)", use_container_width=True):
            if analysis_direction == "BI보드 데이터 기반":
                direction_prompt = """
                [BI보드 데이터 기반 분석 지침]
                - 상위 배너들의 시각적 공통점과 핵심 성공 인자를 명확히 짚어낼 것.
                - "가독성을 높이세요" 같은 당연한 말은 제외하고 '왜 이런 수정을 해야하는지' 구체적이고 실질적인 가이드를 제공할 것.
                - 기존 카피를 퍼포먼스 마케팅 시점에 맞춰 더 강렬하게 리라이팅하고, 강조할 폰트 스타일과 크기를 구체적으로 지적할 것.
                """
            else:
                direction_prompt = f"""
                [완전히 새로운 시도 분석 지침]
                - 과거 데이터에 얽매이지 말고, 제공된 키워드({specific_hint if specific_hint else '최신 유행 밈, 타사 벤치마킹 스타일, 계절/명절 이벤트'})를 활용해 파격적인 기획을 제안할 것.
                """

            system_prompt = f"""
            너는 퍼포먼스 마케팅 크리에이티브 디렉터다. 첨부된 상위 배너들을 분석하고 짧고 명확한 개조식으로 피드백해라.
            
            [환경 설정]
            - IP 특징: {ip_style}
            - 데이터 요약: {banner_data_summary}
            - 추가 지시사항: {additional_context}
            
            [출력 포맷 필수 규칙 - 시스템 파싱용]
            반드시 각 배너의 피드백 시작 부분에 '===TOP 1===', '===TOP 2===' 와 같이 명확한 구분자를 넣어서 출력해라. 
            서론이나 결론 없이 바로 구분자로 시작해라.
            
            {direction_prompt}
            """
            
            with st.spinner("배너 크리에이티브를 정밀 분석 중..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=valid_imgs + [system_prompt]
                    )
                    
                    raw_text = response.text
                    feedbacks_split = re.split(r'===TOP \d+===', raw_text)
                    st.session_state.feedbacks = [f.strip() for f in feedbacks_split if f.strip()]
                    st.session_state.prompts = {} # 분석이 새로 돌면 프롬프트 초기화
                    st.session_state.analysis_done = True
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

        # ==========================================
        # 4. 분석 결과 출력 및 비동기(개별) 프롬프트 생성
        # ==========================================
        if st.session_state.analysis_done:
            st.markdown("---")
            st.subheader(f"🤖 배너별 상세 피드백 및 시안 프롬프트")
            
            for i, feedback in enumerate(st.session_state.feedbacks):
                st.markdown(f"### 🥇 TOP {i+1} 개선 가이드")
                st.markdown(feedback)
                
                # 프롬프트 생성 영역 컨테이너화 (개별 로딩을 위해)
                prompt_container = st.container()
                with prompt_container:
                    if i not in st.session_state.prompts:
                        if st.button(f"🎨 TOP {i+1} 맞춤 러프 프롬프트 생성", key=f"btn_prompt_{i}"):
                            
                            # [핵심] 텍스트 길이 제한 해제 및 원본 이미지 재참조 지시
                            prompt_query = f"""
                            [핵심 지시사항]
                            1. 첨부된 원본 배너 이미지를 다시 한 번 깊게 관찰해라. 이미지 속 '캐릭터의 외형(머리색, 헤어스타일, 눈매, 의상 디테일)'과 '자세(포즈, 시선 방향, 손동작, 표정)'를 영어로 아주 상세하고 길게 묘사해라.
                            2. 그 상세 묘사를 바탕으로, 아래 [피드백 내용]에서 지시한 구도/배경/텍스트 변경사항을 결합하여 완벽한 '이미지 생성형 AI 프롬프트'를 작성해라.
                            
                            [피드백 내용]
                            {feedback}
                            
                            [프롬프트 작성 규칙]
                            - 프롬프트 텍스트 길이 제한 없음. 원본 캐릭터와 똑같은 포즈와 느낌이 나오도록 캐릭터 묘사에 가장 많은 문장을 할애할 것.
                            - 배너 비율은 1:1 ratio.
                            - 텍스트가 배치될 영역은 'Korean text (Hangul typography)'로 명시할 것.
                            - 부가 설명 없이 오직 영문 프롬프트만 마크다운 코드 블록(```text ... ```)으로 출력할 것.
                            """
                            
                            with st.spinner(f"TOP {i+1} 원본 캐릭터 분석 및 프롬프트 추출 중... (다른 피드백을 계속 읽으셔도 됩니다)"):
                                try:
                                    # [핵심] 프롬프트 생성 시 해당 배너 이미지(valid_imgs[i])를 같이 던져주어 눈으로 보고 묘사하게 만듦
                                    gen_prompt_res = client.models.generate_content(
                                        model='gemini-2.5-flash', 
                                        contents=[valid_imgs[i], prompt_query]
                                    )
                                    st.session_state.prompts[i] = gen_prompt_res.text
                                    st.rerun() # 해당 부분만 갱신
                                except Exception as e:
                                    st.error(f"프롬프트 생성 중 오류 발생: {e}")
                    else:
                        st.markdown(st.session_state.prompts[i])
                st.markdown("---")

    else:
        st.error("CSV 내에서 이미지를 가져오지 못했습니다.")
