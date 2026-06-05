# Asac-ML-project

## 📊 데이터베이스 구조 (ERD)
```mermaid
erDiagram
    PROJECT ||--o{ REWARD : "contains"

    PROJECT {
        int projectID PK "프로젝트 고유 ID"
        string name "프로젝트명"
        string creator "창작자명"
        int creatorID "창작자 ID"
        string homeUrl "홈페이지 URL"
        string currencySymbol "통화 기호"
        float campaignGoal "캠페인 목표 금액"
        float fundsGathered "모인 금액"
        int backersCount "후원자 수"
        string campaignStart "캠페인 시작일"
        string campaignEnd "캠페인 종료일"
        string phaseLabel "진행 단계"
        boolean enableBoardGameProperties "보드게임 속성 활성화 여부"
        float minPlayers "최소 인원 (Null 가능)"
        float maxPlayers "최대 인원 (Null 가능)"
        float minAge "최소 연령 (Null 가능)"
        float playTime "플레이 시간 (Null 가능)"
        int playTimeUnit "플레이 시간 단위"
        int fundedInSeconds "펀딩 성공 소요 시간(초)"
        string imageUrl "이미지 URL"
        string pledgeManagerSoftCloseDeadline "PM 마감일 (Null 가능)"
        string projectTags "프로젝트 태그"
        int originalType "원본 타입"
    }

    REWARD {
        int productID PK "리워드/상품 고유 ID"
        int projectID FK "소속 프로젝트 ID"
        string main_name "리워드명"
        string anchorRelativeUrl "리워드 상대 경로 URL"
        float price "가격"
        boolean isDiscounted "할인 여부"
        float effectivePrice "실제 판매 가격"
        boolean isFeatured "추천 여부"
        int purchasedCopiesCount "판매된 수량"
        string backgroundUrl "배경 이미지 URL"
        float installmentCost "할부 비용 (Null 가능)"
        float installmentMinPayment "최소 할부 금액 (Null 가능)"
        boolean hasLimitedStock "수량 제한 여부"
        boolean productCanBePurchased "구매 가능 여부"
        float remainingStockLimit "잔여 수량 (Null 가능)"
    }
```
## 📂프로젝트 폴더 구조 (ERD)
```text
Asac-ML-project/
│
├── src/                    # 실제 실행 가능한 소스 코드
│   ├── data_loader.py      # 데이터 로드 및 수집 스크립트
│   ├── preprocessing.py    # 결측치 처리, 정규화 등 전처리 모듈
│   ├── feature.py          # 피처 엔지니어링 관련 모듈
│   ├── model.py            # 모델 정의 및 학습 스크립트
│   └── utils.py            # 공통 유틸리티 함수 (로깅, 시간 계산 등)
│
├── data/                   # 데이터 저장 공간 (Git에 업로드 금지)
│   ├── raw/                # 원본 데이터 (수정 불가)
│   ├── processed/          # 전처리 완료된 데이터
│
├── doc/                    # 문서 및 보고서
│   ├── images/             # 발표 자료나 리드미에 들어갈 이미지
│   ├── meeting-notes/      # 회의록
│   └── reports/            # 최종 보고서 및 중간 발표 자료
│
│
├── etc/                    # 그 외 기타 파일
│   ├── notebooks/          # EDA 및 프로토타입 테스트용 Jupyter Notebook (.ipynb)
│   └── templates/          # 참고용 템플릿 파일
│
└── README.md              # 프로젝트 개요 및 실행 방법 설명서
```
