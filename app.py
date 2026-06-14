import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 0. 다크모드 및 UI 커스텀 CSS (요구사항 2, 3 반영)
# ==========================================
dark_mode = st.sidebar.toggle("🌙 다크 모드 (Dark Mode)", value=False)

# 프롬프트 결과창을 시각적으로 완전히 분리하는 커스텀 CSS
custom_css = """
<style>
    /* 프롬프트 결과 박스 스타일 (시인성 강화) */
    .prompt-box {
        background-color: #2b303b;
        color: #a3be8c;
        padding: 20px;
        border-radius: 8px;
        border-left: 5px solid #ebcb8b;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
        margin-top: 15px;
        margin-bottom: 15px;
        white-space: pre-wrap;
    }
</style>
"""

if dark_mode:
    custom_css += """
    <style>
        /* 전체 다크모드 강제 적용 */
        .stApp { background-color: #121212; color: #E0E0E0; }
        .stMarkdown, .stText, h1, h2, h3, h4, p, label { color: #E0E0E0 !important; }
        .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
            background-color: #2A2A2A !important; color: white !important; 
        }
    </style>
    """

st.markdown(custom_css, unsafe_allow_html=True)
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V7)")

# ==========================================
# 1. 사이드바 설정 및 메모리 초기화
# ==========================================
if "feedbacks" not in st.session_state:
    st.session_state.feedbacks = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

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
# 2. 데이터 처리 및 상위 배너 추출 (요구사항 4 반영)
# ==========================================
uploaded_file = st.file_uploader("BI 보드 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file and api_key:
    client = genai.Client(api_key=api_key)
    raw_df = pd.read_csv(uploaded_file)
    
    # [요구사항 4] 완전히 같은 디자인(url)이되, 해외(language)는 다르게 분리하여 그룹화
    group_cols = ['url', 'language'] if 'language' in raw_df.columns else ['url']
    
    # 중복 이미지 합산 (CV는 더하고, ROAS는 평균)
    df = raw_df.groupby(group_cols, as_index=False).agg({
        'first_pay_cv': 'sum',
        'roas': 'mean',
        'name': 'first'
    })
    
    # 첫결제 기준 내림차순 정렬
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

    st.subheader(f"🏆 성과 최상위 TOP {top_n} 배너 (중복 디자인 합산 / 첫결제 건수 우선)")
    cols = st.columns(top_n)
    valid_imgs = []
    
    with st.spinner("이미지를 불러오는 중..."):
        for i, row in enumerate(top_banners.itertuples()):
            img = download_image(row.url)
            with cols[i]:
                if img:
                    st.image(img, use_container_width=True)
                    valid_imgs.append(img)
                # 언어/국가 표시 추가
                lang_str = f" | 국가: {row.language}" if 'language' in df.columns else ""
                st.caption(f"**TOP {i+1}**{lang_str}\n\nCV 합계: {row.first_pay_cv} | ROAS: {row.roas:.2f}")

    if valid_imgs:
        banner_data_summary = "\n".join([f"- TOP {idx+1}: CV {row.first_pay_cv}건, ROAS {row.roas:.2f} (언어: {row.language if 'language' in df.columns else '알수없음'})" for idx, row in enumerate(top_banners.itertuples())])
        
        # ==========================================
        # 3. 분석 실행 버튼 (요구사항 5, 6, 7 반영)
        # ==========================================
        st.markdown("---")
        if st.button("🚀 AI 피드백 분석 실행 (설정이 바뀌면 다시 누르세요)", use_container_width=True):
            
            system_prompt = f"""
            너는 퍼포먼스 마케팅 크리에이티브 디렉터다. 첨부된 상위 배너들을 분석하고 짧고 명확한 개조식으로 피드백해라.
            
            [환경 설정]
            - IP 특징: {ip_style}
            - 피드백 방향성: {analysis_direction}
            - 타겟 밈/시즌: {specific_hint}
            - 데이터 요약: {banner_data_summary}
            - 추가 지시사항: {additional_context}
            
            [✨ 피드백 필수 작성 규칙 (매우 중요)]
            1. [배경 상세 묘사]: 새 배너에 적용할 배경을 아주 구체적으로 제안해라. (예: 단순히 '밝은 배경'이 아니라 '네온 핑크빛 광원이 들어간 사이버펑크 질감의 어두운 배경')
            2. [텍스트 스타일링]: 텍스트를 넣을 경우, 어떤 폰트(고딕, 명조, 캘리그라피 등), 어떤 색상, 어떤 이펙트(테두리, 드롭섀도우, 발광 효과 등)를 쓸지 명확히 제시해라.
            3. [해외 소재 대응]: 만약 분석하는 배너가 한국(ko) 외의 해외 소재(언어)라면, 언어적 카피(텍스트) 분석은 최소화하고 '시각적 디자인(그래픽, 오브젝트 배치, 색감, 이펙트)' 위주로 피드백을 작성해라.
            
            [출력 포맷 필수 규칙]
            반드시 각 배너의 피드백 시작 부분에 '===TOP 1===', '===TOP 2===' 와 같이 명확한 구분자를 넣어서 출력해라. 
            서론이나 결론 없이 바로 구분자로 시작해라.
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
                    st.session_state.analysis_done = True
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

        # ==========================================
        # 4. 분석 결과 출력 및 부분 렌더링(Fragment) 적용
        # ==========================================
        if st.session_state.analysis_done:
            st.markdown("---")
            st.subheader("🤖 배너별 상세 피드백 및 시안 프롬프트")
            
            # [요구사항 1] st.fragment를 사용하여 이 함수 내의 버튼 클릭 시 화면 전체가 불투명해지는 것을 막음
            @st.fragment
            def prompt_generator_fragment(i, feedback, valid_img):
                if st.button(f"🎨 TOP {i+1} 맞춤 러프 프롬프트 생성", key=f"btn_prompt_{i}"):
                    prompt_query = f"""
                    [핵심 지시사항]
                    1. 첨부된 원본 배너 이미지를 관찰하여 캐릭터의 외형(머리색, 옷, 포즈)을 상세히 영어로 묘사해라.
                    2. 아래 [피드백 내용]에서 지시한 구도, 배경, 텍스트 스타일을 결합하여 완벽한 '이미지 생성형 AI 프롬프트'를 작성해라.
                    [피드백 내용]: {feedback}
                    [규칙]: 1:1 ratio. 텍스트 영역은 'Korean text typography' 명시. 부가 설명 없이 프롬프트만 출력.
                    """
                    
                    with st.spinner("프롬프트 추출 중... (다른 피드백을 읽으셔도 됩니다)"):
                        try:
                            gen_prompt_res = client.models.generate_content(
                                model='gemini-2.5-flash', 
                                contents=[valid_img, prompt_query]
                            )
                            # [요구사항 2] 커스텀 CSS를 적용한 세련된 결과 박스 렌더링
                            st.markdown(f'<div class="prompt-box">{gen_prompt_res.text}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"프롬프트 생성 중 오류 발생: {e}")

            # 피드백 리스트 출력 및 fragment 함수 호출
            for i, feedback in enumerate(st.session_state.feedbacks):
                st.markdown(f"### 🥇 TOP {i+1} 개선 가이드")
                st.markdown(feedback)
                
                # 버튼과 프롬프트 생성 과정을 격리된 Fragment로 실행
                if i < len(valid_imgs):
                    prompt_generator_fragment(i, feedback, valid_imgs[i])
                
                st.markdown("---")

    else:
        st.error("CSV 내에서 이미지를 가져오지 못했습니다.")
