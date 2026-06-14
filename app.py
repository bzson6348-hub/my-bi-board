import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide")
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V4)")

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

# 방향성 선택지로 변경
analysis_direction = st.sidebar.radio(
    "🧭 피드백 집중 방향성 선택", 
    ["BI보드 데이터 기반", "완전히 새로운 시도"]
)

# 새로운 시도 선택 시에만 활성화되는 구체적 힌트 창
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
    
    # 첫결제(first_pay_cv) 최우선 정렬, 동률시 ROAS 정렬
    df_sorted = df.sort_values(by=['first_pay_cv', 'roas'], ascending=[False, False]).reset_index(drop=True)
    
    # 상위 4개 배너 추출
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
        # 3. 방향성에 맞춘 고도화된 프롬프트 조립
        # ==========================================
        if analysis_direction == "BI보드 데이터 기반":
            direction_prompt = """
            [BI보드 데이터 기반 분석 지침]
            - 상위 배너들의 시각적 공통점과 핵심 성공 인자(예: 로우앵글 구도, 보일듯 말듯한 신비로운 분위기, 특정 색감 등)를 명확히 짚어낼 것.
            - "가독성을 높이세요" 같은 당연한 말은 제외하고 구체적이고 실질적인 가이드를 제공할 것.
            - 분석을 토대로 '이러이러하기 때문에 이렇게 수정하라'는 명확한 인과관계를 설명할 것.
            - 기존 카피를 퍼포먼스 마케팅 시점에 맞춰 더 강렬하게 리라이팅하고, 강조할 폰트 스타일과 크기를 구체적으로 지적할 것.
            """
        else:
            direction_prompt = f"""
            [완전히 새로운 시도 분석 지침]
            - 과거 데이터에 얽매이지 말고, 마케팅 트렌드에 맞춘 파격적인 1:1 배너 기획을 제안할 것.
            - 제공된 키워드({specific_hint if specific_hint else '최신 유행 밈, 타사 벤치마킹 스타일, 계절/명절 이벤트'})를 활용할 것.
            - 예: "여름 시즌에 맞춰 청량한 색감을 쓰고 비키니 일러스트 톤을 강조", "추석 연휴를 타겟으로 텍스트를 빼고 캐릭터 표정만 강조" 등 구체적이고 근거 있는 제안을 할 것.
            """

        system_prompt = f"""
        너는 퍼포먼스 마케팅 크리에이티브 디렉터다. 첨부된 상위 배너들을 분석하고 짧고 명확한 개조식으로 피드백해라.
        
        [환경 설정]
        - IP 특징: {ip_style}
        - 피드백 방향성: {analysis_direction}
        - 추가 지시사항: {additional_context}
        - 데이터 요약: {banner_data_summary}
        
        [필수 규칙]
        1. 인물 일러스트는 교체 불가(밝기만 조절 가능). 구도, 배경, 텍스트, 색감 등의 변형으로만 해결책을 제시할 것.
        2. 모든 디자인 가이드는 '1:1 정방형 사이즈'를 기준으로 할 것.
        
        {direction_prompt}
        """
        
        with st.spinner("배너 크리에이티브를 정밀 분석 중..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=valid_imgs + [system_prompt]
            )
            
            st.markdown("---")
            st.subheader(f"🤖 크리에이티브 분석 보고서 ({analysis_direction})")
            st.markdown(response.text)
            
           # ==========================================
            # 4. 러프 프롬프트 생성
            # ==========================================
            st.markdown("---")
            st.subheader("🎨 러프 프롬프트 생성")
            st.info("아래 3가지 패턴의 영문 프롬프트 중 하나를 복사하여 이미지 생성 AI에 붙여넣으세요. 원본 인물의 포즈를 유지하면서 한글 타이포그래피가 적용된 1:1 구도 이미지를 생성합니다.")
            
            prompt_query = (
                f"Based on this analysis:\n{response.text}\n\n"
                "Write 3 different ONE-LINE English prompts to generate a 1:1 ratio rough layout sketch for this banner. "
                "CRITICAL RULES: "
                "1. The character's POSE MUST perfectly match the original banner's character pose. "
                "2. Explicitly command the AI to use 'Korean text (Hangul typography)' for any text placeholders. "
                "3. Create 3 distinct aesthetic patterns: "
                "Pattern 1: Simple UI Wireframe Blueprint. "
                "Pattern 2: Flat Minimalist Vector. "
                "Pattern 3: Rough Pencil Storyboard Sketch. "
                "Output format: Add a Korean title like '[패턴 1: 심플 와이어프레임]' followed by the pure English prompt on the next line. Separate each pattern with an empty line. Do not use markdown code blocks."
            )
            
            with st.spinner("3가지 패턴의 프롬프트 추출 중..."):
                gen_prompt_res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_query)
                clean_ai_prompt = gen_prompt_res.text.strip().replace("`", "")
                
                st.text_area("▼ 1:1 러프 프롬프트 3종 (원하는 패턴을 복사하세요)", value=clean_ai_prompt, height=250)
    else:
        st.error("CSV 내에서 이미지를 가져오지 못했습니다.")
