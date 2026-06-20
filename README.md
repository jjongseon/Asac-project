# Asac-ML-project

## 📂프로젝트 폴더 구조 (ERD)
```text
Asac-ML-project/
│
├── src/                    # 실제 실행 가능한 소스 코드
│   ├── crawling/           # 데이터 로드 및 수집
│   ├── ml/                 # 머신러닝 튜닝
│   ├── processed/          # 결측치 처리, 정규화 등 전처리
│   └── test/               # 코드 테스트
│   
│
├── data/                   # 데이터 저장 공간 (업로드 X)
│   ├── raw/                # 원본 데이터 (수정 불가)
│   ├── processed/          # 전처리 완료된 데이터
│   └── main_image/         # 이미지 데이터
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
