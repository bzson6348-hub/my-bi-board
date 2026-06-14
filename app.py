import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide")
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V5)")

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
    st.success("데이터 로드 완료!")
    
    df_sorted = df.sort_values(by=['first_pay_cv', 'roas'], ascending=[False, False]).reset_index(drop=True)
    top_n = min(4, len(df_sorted))
    top_banners = df_sorted.head(top_n)
    
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
        # 3. 분석용 프롬프트 조립 (구분자 강제 삽입)
        # ==========================================
        if analysis_direction == "BI보드 데이터 기반":
            direction_prompt = """
            [BI보드 데이터 기반 분석 지침]
            - 상위 배너들의 시각적 공통점과 핵심 성공 인자(예: 로우앵글 구도, 신비로운 분위기, 특정 색감 등)를 명확히 짚어낼 것.
            - "가독성을 높이세요" 같은 당연한 말은 제외하고 '왜 이런 수정을 해야하는지' 구체적이고 실질적인 가이드를 제공할 것.
            - 기존 카피를 퍼포먼스 마케팅 시점에 맞춰 더 강렬하게 리라이팅하고, 강조할 폰트 스타일과 크기를 구체적으로 지적할 것.
            """
        else:
            direction_prompt = f"""
            [완전히 새로운 시도 분석 지침]
            - 과거 데이터에 얽매이지 말고, 제공된 키워드({specific_hint if specific_hint else '최신 유행 밈, 타사 벤치마킹 스타일, 계절/명절 이벤트'})를 활용해 파격적인 기획을 제안할 것.
            - 예: "여름 시즌에 맞춰 청량한 색감을 쓰고 비키니 일러스트 톤을 강조" 등 구체적이고 근거 있는 제안을 할 것.
            """

        system_prompt = f"""
        너는 퍼포먼스 마케팅 크리에이티브 디렉터다. 첨부된 상위 배너들을 분석하고 짧고 명확한 개조식으로 피드백해라.
        
        [환경 설정]
        - IP 특징: {ip_style}
        - 피드백 방향성: {analysis_direction}
        - 추가 지시사항: {additional_context}
        - 데이터 요약: {banner_data_summary}
        
        [출력 포맷 필수 규칙 - 시스템 파싱용]
        반드시 각 배너의 피드백 시작 부분에 '===TOP 1===', '===TOP 2===' 와 같이 명확한 구분자를 넣어서 출력해라. 
        서론이나 결론 없이 바로 ===TOP 1=== 구분자로 시작해라.
        
        {direction_prompt}
        """
        
       # 전체 배너 분석 실행 (에러 방어 코드 추가)
        with st.spinner("배너 크리에이티브를 정밀 분석 중..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=valid_imgs + [system_prompt]
                )
                
                # 정규표현식으로 ===TOP N=== 기준으로 텍스트 분리
                raw_text = response.text
                feedbacks = re.split(r'===TOP \d+===', raw_text)
                feedbacks = [f.strip() for f in feedbacks if f.strip()] # 빈 공백 필터링
                
                st.markdown("---")
                st.subheader(f"🤖 배너별 상세 피드백 및 시안 프롬프트 ({analysis_direction})")
                
                # ==========================================
                # 4. 피드백 렌더링 및 개별 프롬프트 생성 버튼
                # ==========================================
                for i, feedback in enumerate(feedbacks):
                    st.markdown(f"### 🥇 TOP {i+1} 개선 가이드")
                    st.markdown(feedback)
                    
                    if st.button(f"🎨 TOP {i+1} 시안 러프 프롬프트 생성", key=f"btn_prompt_{i}"):
                        prompt_query = f"""
                        다음 피드백 내용을 토대로, 이 배너의 개선 시안을 시각화할 수 있는 '광고 배너 레이아웃 스케치'용 영문 프롬프트를 작성해.
                        [피드백 내용]: {feedback}
                        [규칙]: 1:1 ratio, keeping the character's original pose, Korean text (Hangul typography). 1~2줄 영문 마크다운 코드블록으로만 출력.
                        """
                        with st.spinner(f"TOP {i+1} 맞춤형 프롬프트 추출 중..."):
                            gen_prompt_res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_query)
                            st.markdown(gen_prompt_res.text)
                    st.markdown("---")
            
            except Exception as e:
                # 스트림릿이 숨긴 진짜 에러 메시지를 화면에 강제로 출력
                st.error(f"API 요청 중 문제가 발생했습니다. (진짜 원인: {e})")
                st.warning("💡 팁: 'Quota exceeded' 등의 단어가 보인다면 1~2분 정도 기다렸다가 다시 시도해 보세요. (무료 API 단기 호출 제한)")
            
            # ==========================================
            # 4. 피드백 렌더링 및 개별 프롬프트 생성 버튼
            # ==========================================
            for i, feedback in enumerate(feedbacks):
                # UI 레이아웃 분리
                st.markdown(f"### 🥇 TOP {i+1} 개선 가이드")
                st.markdown(feedback)
                
                # 버튼 고유 키값(key)을 부여하여 개별 작동하도록 설계
                if st.button(f"🎨 TOP {i+1} 시안 러프 프롬프트 생성", key=f"btn_prompt_{i}"):
                    
                    # 해당 피드백 내용만 콕 집어서 프롬프트 추출 지시
                    prompt_query = f"""
                    다음 피드백 내용을 토대로, 이 배너의 개선 시안을 시각화할 수 있는 '광고 배너 레이아웃 스케치'용 영문 프롬프트를 작성해.
                    
                    [피드백 내용]
                    {feedback}
                    
                    [프롬프트 작성 필수 규칙]
                    1. 위 피드백에서 제안한 구도, 텍스트 위치, 배경 느낌을 이미지 생성 AI가 정확히 그릴 수 있게 1:1 비율(1:1 ratio)의 구체적인 시각 묘사로 변환할 것.
                    2. 반드시 1~2줄의 영문 프롬프트로 완성할 것.
                    3. 원본 배너 인물의 포즈를 그대로 유지하라는 지시("keeping the character's original pose")를 포함할 것.
                    4. 텍스트 요소에는 'Korean text (Hangul typography)'를 적용하라고 명시할 것.
                    
                    [출력 포맷]
                    사용자가 복사하기 쉽도록 반드시 아래 마크다운 형식(코드 블록)으로만 출력할 것. 다른 설명은 절대 금지.
                    ```text
                    (여기에 영문 프롬프트 작성)
                    ```
                    """
                    
                    with st.spinner(f"TOP {i+1} 맞춤형 프롬프트 추출 중..."):
                        gen_prompt_res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_query)
                        st.markdown(gen_prompt_res.text)
                
                st.markdown("---") # 배너 간 구분선
                
    else:
        st.error("CSV 내에서 이미지를 가져오지 못했습니다.")
