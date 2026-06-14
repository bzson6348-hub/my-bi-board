import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from google import genai

st.set_page_config(layout="wide")
st.title("🎯 AI 광고 배너 크리에이티브 분석 보드 (V2)")

# ==========================================
# 1. 사이드바 설정 (인증 및 유저 커스텀 기능)
# ==========================================
st.sidebar.header("🔑 인증 및 기본 설정")
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 분석 프롬프트 세부 설정")

# [요구사항 2] 여러 게임 타이틀 관리를 위한 IP 설정
ip_style = st.sidebar.selectbox(
    "분석할 게임 IP의 주요 분위기",
    ["원작 충실형 (다크 판타지/라이트노벨)", "캐주얼/귀여움", "수집형 RPG/화려함", "직접 입력"]
)
if ip_style == "직접 입력":
    ip_style = st.sidebar.text_input("IP 분위기를 직접 입력하세요", "예: SF 메카닉 일러스트 기반")

# [요구사항 5] 분석 및 최적화 기준 선택
focus_type = st.sidebar.radio(
    "우선 최적화 방향", 
    ["과금 효율 중심 (ROAS/CPA 개선)", "유입 극대화 중심 (CTR/클릭수 개선)"]
)

# [요구사항 5] 새로운 시도에 반영할 트렌드/계절성 키워드 입력
trend_keyword = st.sidebar.text_input("현재 유행하는 밈 또는 계절성 키워드", "예: 무더운 여름 시원한 보상, 한국 유행 밈")

# [요구사항 6] 디폴트를 해치지 않는 선에서의 추가 자유 지시문
additional_context = st.sidebar.text_area("🤖 추가 강조 지시사항 (선택)", placeholder="예: 이번엔 카피를 최대한 줄여줘.")

# ==========================================
# 2. 파일 업로드 및 데이터 처리
# ==========================================
uploaded_file = st.file_uploader("BI 보드에서 다운받은 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file and api_key:
    client = genai.Client(api_key=api_key)
    df = pd.read_csv(uploaded_file)
    st.success("데이터 로드 완료!")
    
    # 성과 기준 추출 (사이드바 선택 반영)
    target_metric = 'roas' if "과금 효율" in focus_type else 'first_pay_cv'
    best_row = df.loc[df[target_metric].idxmax()]
    worst_row = df.loc[df[target_metric].idxmin()]
    
    # 이미지 다운로드 함수
    def download_image(url):
        try:
            response = requests.get(url, timeout=5)
            return Image.open(BytesIO(response.content))
        except:
            return None

    with st.spinner("배너 이미지를 불러오는 중..."):
        best_img = download_image(best_row['url'])
        worst_img = download_image(worst_row['url'])

    if best_img and worst_img:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏆 성과 우수 배너")
            st.image(best_img, use_container_width=True)
            st.caption(f"이름: {best_row['name']} | ROAS: {best_row['roas']}")
        with col2:
            st.subheader("❌ 성과 저조 배너")
            st.image(worst_img, use_container_width=True)
            st.caption(f"이름: {worst_row['name']} | ROAS: {worst_row['roas']}")
            
        # ==========================================
        # 3. 유저 요구사항이 반영된 시스템 프롬프트 조립
        # ==========================================
        prompt = f"""
        너는 퍼포먼스 마케팅 배너 분석가이자 크리에이티브 디렉터야. 
        첨부된 두 배너 이미지를 시각적으로 직접 비교하고, 제시된 데이터를 기반으로 분석 보고서를 작성해줘.
        
        [게임 IP 및 분석 환경]
        - 이 게임의 IP 특징: {ip_style} (반드시 이 세계관과 톤앤매너를 존중하여 분석할 것)
        - 최적화 우선순위: {focus_type}
        - 현재 트렌드/계절성 키워드: {trend_keyword}
        - 추가 요청사항: {additional_context}
        
        [데이터 정보]
        - Best 배너: {best_row['name']} (비용: {best_row['cost']}, ROAS: {best_row['roas']})
        - Worst 배너: {worst_row['name']} (비용: {worst_row['cost']}, ROAS: {worst_row['roas']})
        
        [필수 분석 지침]
        1. [인물 일러스트 고정]: 우리 회사는 인물 일러스트 자체를 변경할 수 없다(밝기만 수정 가능). 따라서 피드백 시 인물 교체를 요구하지 말고, '배경, 구도, 레이아웃, 텍스트 디자인 및 위치'를 변경하여 다른 분위기를 만드는 방향으로 제안해라.
        2. [광고 문구 전략]: 문구 삽입을 추천한다면 구체적인 예시 카피와 이유를 작성해라. 만약 데이터상 문구가 없는 깔끔한 배너가 유리하다고 판단되면, 무리해서 넣지 말고 문구를 빼야 하는 이유와 '대체 제안(예: 로고 배치 및 일러스트 표정에 맞는 배경 연출)'을 구체적으로 제시해라.
        
        [출력 포맷]
        반드시 아래 2가지 기준으로 크게 분류해서 답변해줘:
        
        ■ 1. 미조정 배너안 (Fine-Tuning)
        - 회사 내 기존 성공 데이터나 이 IP의 기존 성공 법칙을 토대로, 현재 배너에서 레이아웃이나 색감 등을 '살짝만 미조정'하여 안정적으로 성과를 올릴 수 있는 가이드를 구체적으로 제시해줘.
        
        ■ 2. 완전히 새로운 시도 (New Trend & Strategy)
        - 데이터에만 의존하지 말고, 언급된 트렌드/계절성 키워드({trend_keyword})나 한국의 최신 유행 밈, 심리학적 크리에이티브 기법을 활용하여 완전히 새로운 관점에서 시도해볼 수 있는 파격적인 배너 기획안을 제시해줘.
        
        ■ 3. [중요] 디자이너 전달용 이미지 생성 프롬프트
        - 위 분석 내용을 바탕으로, 디자이너에게 레이아웃 스케치를 그려줄 수 있도록 '배너 레이아웃 가이드 영어 프롬프트'를 작성해줘. 
        - 프롬프트 서두에는 반드시 "A rough blueprint wireframe sketch layout for an ad banner, simple prototype style, ..."을 포함하여 러프한 구도 위주로 나오게 짜줘.
        """
        
        # 제미나이 텍스트/시각 분석 실행
        with st.spinner("제미나이가 배너를 직접 보며 분석하는 중입니다..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[best_img, worst_img, prompt]
            )
            
            st.markdown("---")
            st.subheader("🤖 제미나이 크리에이티브 시각 분석 보고서")
            st.markdown(response.text)
            
            # ==========================================
            # 4. [요구사항 3] 디자이너용 러프 스케치 자동 생성 기능
            # ==========================================
            st.markdown("---")
            st.subheader("🎨 디자이너 전달용 레이아웃 스케치 생성")
            st.info("위 분석 결과를 바탕으로 디자이너가 구도를 직관적으로 이해할 수 있는 러프한 프로토타입 스케치 이미지를 생성합니다.")
            
            if st.button("🖼️ 러프 스케치 이미지 생성하기 (최저용량/고속)"):
                with st.spinner("Imagen 모델이 레이아웃 스케치를 그리는 중..."):
                    # 텍스트 결과에서 영문 프롬프트 부분을 추출하거나 제미나이에게 다시 요청하여 스케치 생성
                    sketch_prompt_query = f"다음 분석 내용을 토대로, 디자이너에게 구도(인물위치, 텍스트위치, 로고위치)만 대략적으로 보여줄 수 있는 간단한 광고 배너 와이어프레임 스케치용 영어 프롬프트 딱 한 문장만 출력해줘. 분석 내용: {response.text}"
                    sketch_prompt_res = client.models.generate_content(model='gemini-2.5-flash', contents=sketch_prompt_query)
                    
                    # 최저 용량 및 빠른 생성을 위해 생성 옵션 최적화
                    result = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=sketch_prompt_res.text,
                        config=dict(
                            number_of_images=1,
                            aspect_ratio="1:1",
                            output_mime_type="image/jpeg" # 용량이 작은 jpeg 선택
                        )
                    )
                    
                    generated_image = Image.open(BytesIO(result.generated_images[0].image.image_bytes))
                    st.image(generated_image, caption="디자이너 참고용 러프 레이아웃 가이드 (프로토타입)", width=500)
    else:
        st.error("CSV 내 이미지 URL에서 이미지를 가져오지 못했습니다. URL 주소를 확인해주세요.")
