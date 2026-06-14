import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide")
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V3)")

# ==========================================
# 1. 사이드바 설정 (인증 및 유저 커스텀 기능)
# ==========================================
st.sidebar.header("🔑 인증 및 기본 설정")
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 분석 프롬프트 세부 설정")

ip_style = st.sidebar.selectbox(
    "분석할 게임 IP의 주요 분위기",
    ["원작 충실형 (다크 판타지/라이트노벨)", "캐주얼/귀여움", "수집형 RPG/화려함", "직접 입력"]
)
if ip_style == "직접 입력":
    ip_style = st.sidebar.text_input("IP 분위기를 직접 입력하세요", "예: SF 메카닉 일러스트 기반")

trend_keyword = st.sidebar.text_input("현재 유행하는 밈 또는 계절성 키워드", "예: 무더운 여름 시원한 보상, 한국 유행 밈")
additional_context = st.sidebar.text_area("🤖 추가 강조 지시사항 (선택)", placeholder="예: 이번엔 카피를 최대한 줄여줘.")

# ==========================================
# 2. 파일 업로드 및 데이터 처리 (성과 기준 고도화)
# ==========================================
uploaded_file = st.file_uploader("BI 보드에서 다운받은 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file and api_key:
    client = genai.Client(api_key=api_key)
    df = pd.read_csv(uploaded_file)
    st.success("데이터 로드 완료!")
    
    # [요구사항 4] first_pay_cv(첫결제 건수)를 최우선 기준으로 정렬 (동률일 경우 roas 정렬)
    df_sorted = df.sort_values(by=['first_pay_cv', 'roas'], ascending=[False, False]).reset_index(drop=True)
    
    # [요구사항 3] 상위 3~4개 배너만 추천 화면에 노출
    top_n = min(4, len(df_sorted))
    top_banners = df_sorted.head(top_n)
    
    def download_image(url):
        try:
            response = requests.get(url, timeout=5)
            return Image.open(BytesIO(response.content))
        except:
            return None

    # 상위 배너 가로 정렬 출력
    st.subheader(f"🏆 현재 성과 최상위 TOP {top_n} 배너 추천")
    cols = st.columns(top_n)
    valid_imgs = []
    
    with st.spinner("상위 배너 이미지를 불러오는 중..."):
        for i, row in enumerate(top_banners.itertuples()):
            img = download_image(row.url)
            with cols[i]:
                if img:
                    st.image(img, use_container_width=True)
                    valid_imgs.append(img)
                st.caption(f"**🥇 TOP {i+1}**\n\n이름: {row.name}\n\n첫결제(CV): {row.first_pay_cv}건 | ROAS: {row.roas}")

    if valid_imgs:
        # ==========================================
        # 3. [요구사항 1,2,5] 속도 및 가독성 최적화 프롬프트
        # ==========================================
        banner_data_summary = "\n".join([f"- TOP {idx+1}: {row.name} (첫결제: {row.first_pay_cv}건, ROAS: {row.roas})" for idx, row in enumerate(top_banners.itertuples())])
        
        prompt = f"""
        너는 퍼포먼스 마케팅 배너 분석가이자 크리에이티브 디렉터야.
        첨부된 상위 성과 배너 이미지들을 시각적으로 분석하고, 아래 데이터를 기반으로 피드백해줘.
        불필요한 미사여구나 서론은 생략하고, 디자이너가 바로 읽고 적용할 수 있게 '핵심만 짧고 간결하게' 작성해줘.
        
        [환경 정보]
        - IP 특징: {ip_style}
        - 트렌드 키워드: {trend_keyword}
        - 추가 요청사항: {additional_context}
        
        [추천 배너 데이터]
        {banner_data_summary}
        
        [필수 가이드라인]
        1. [인물 일러스트 고정]: 인물 일러스트 자체 변경은 불가능함(밝기 조절만 가능). '배경, 구도, 레이아웃, 텍스트 디자인 및 위치'를 변경하여 다른 분위기를 만드는 방향으로만 제안할 것.
        2. [광고 문구 전략]: 카피 삽입을 추천한다면 뭘 넣을지 예시와 이유를 제안하고, 텍스트가 없는 배너가 성과가 좋다면 무리하게 넣지 말고 로고와 분위기 연출법 위주의 대체 제안을 줄 것.
        3. [1:1 규격 고정]: 모든 레이아웃 가이드 및 디자인 제안은 1:1 정방형 사이즈를 기준으로 작성할 것.
        
        [출력 포맷 - 짧고 간결한 개조식 문장으로 작성]
        ■ 1. 상위 배너 성공 요인 요약 (2~3줄 요약)
        ■ 2. 미조정 배너안 (기존 데이터 기반으로 레이아웃/색감만 미세하게 조정하여 디자이너가 바로 변형할 수 있는 시안 가이드)
        ■ 3. 완전히 새로운 시도 (트렌드/밈/계절성 키워드({trend_keyword})를 반영하여 1:1 사이즈로 과감하게 시도해볼 새로운 관점의 배너 기획안)
        """
        
        with st.spinner("제미나이가 상위 배너들을 시각 분석하는 중입니다..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=valid_imgs + [prompt]
            )
            
            st.markdown("---")
            st.subheader("🤖 제미나이 크리에이티브 시각 분석 보고서")
            st.markdown(response.text)
            
            # ==========================================
            # 4. [요구사항 6,7] 이미지 생성 에러 해결 및 완전 자동화
            # ==========================================
            st.markdown("---")
            st.subheader("🎨 디자이너 전달용 레이아웃 스케치 생성")
            st.info("위 분석 결과를 바탕으로 인물, 로고, 텍스트의 배치 위치만 대략적으로 보여주는 1:1 러프 와이어프레임 스케치를 생성합니다.")
            
            if st.button("🖼️ 러프 스케치 이미지 생성하기 (최저용량/고속)"):
                with st.spinner("Imagen 모델이 레이아웃 스케치를 그리는 중..."):
                    # [에러 해결] 제미나이에게 순수하게 영어로만 된 한 줄 프롬프트를 뽑아내도록 완전 격리 요청
                    sketch_prompt_query = (
                        "Based on the recommended banner analysis, write a ONE-LINE pure English prompt for an image generation model "
                        "to create a simple wireframe/blueprint layout sketch for a 1:1 ad banner. "
                        "It must only show rough boxes or layouts indicating where to put the character illustration, logo, and text text placeholder. "
                        "Do NOT include any Korean, markdown, conversational filler, or quotes. Output ONLY the raw English text."
                    )
                    sketch_prompt_res = client.models.generate_content(model='gemini-2.5-flash', contents=sketch_prompt_query)
                    
                    # 텍스트 클리닝 및 안전 장치
                    clean_prompt = sketch_prompt_res.text.strip().replace("`", "").replace('"', '')
                    if not clean_prompt.lower().startswith("a rough blueprint"):
                        clean_prompt = f"A rough blueprint wireframe sketch layout for a 1:1 ad banner, simple prototype style, showing placement boxes for character, logo, and text. " + clean_prompt
                    
                    # Imagen 호출
                    result = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=clean_prompt,
                        config=dict(
                            number_of_images=1,
                            aspect_ratio="1:1",
                            output_mime_type="image/jpeg"
                        )
                    )
                    
                    generated_image = Image.open(BytesIO(result.generated_images[0].image.image_bytes))
                    st.image(generated_image, caption="디자이너 참고용 러프 레이아웃 가이드 (1:1 프로토타입)", width=500)
    else:
        st.error("CSV 내 이미지 URL에서 이미지를 가져오지 못했습니다. URL 주소를 확인해주세요.")
