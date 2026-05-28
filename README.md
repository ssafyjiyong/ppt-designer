# PPTdesigner

텍스트 초안만 들어있는 PPT를 업로드하면 Claude(Bedrock)가 슬라이드별로 레이아웃을 디자인해 완성된 PPTX를 돌려주는 웹 서비스.

## 구조

```
PPTdesigner/
├── backend/                  # Lambda 함수 (Python 3.12)
│   ├── functions/
│   │   ├── api_create_job.py     # POST /jobs → presigned upload URL
│   │   ├── api_start_job.py      # POST /jobs/{id}/start → 메인 워크플로 시작
│   │   ├── api_get_job.py        # GET /jobs/{id} → 상태/슬라이드/다운로드 URL
│   │   ├── api_retry_slide.py    # POST /jobs/{id}/slides/{n}/retry
│   │   ├── sf_extract_slides.py  # 업로드 PPT → 슬라이드별 텍스트 추출
│   │   ├── sf_design_slide.py    # Bedrock 호출 → 슬라이드 JSON 스펙 생성
│   │   ├── sf_assemble_pptx.py   # 스펙 모아 python-pptx로 PPTX 빌드
│   │   └── sf_mark_failed.py     # 에러 마킹
│   ├── shared/
│   │   ├── bedrock_client.py     # Claude 호출 + 디자인 시스템 프롬프트
│   │   ├── ddb_client.py         # DynamoDB CRUD
│   │   └── pptx_builder.py       # 슬라이드 스펙 → PPTX 렌더링
│   └── requirements.txt
├── infra/
│   ├── template.yaml             # SAM (Lambda + API Gateway + S3 + DDB + Step Functions + CloudFront)
│   ├── statemachine_main.asl.json
│   └── statemachine_retry.asl.json
├── frontend/                  # Vite + React + TS
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   ├── SlidePreview.tsx      # SVG로 슬라이드 미리보기
│   │   └── styles.css
│   └── package.json
└── DEPLOY.md                  # AWS 배포 단계별 가이드
```

## 동작 흐름

```
[브라우저]                  [API Gateway]              [Step Functions]                [Bedrock]
   |                            |                              |
   |--- POST /jobs ------------>|                              |
   |<-- {job_id, upload_url} ---|                              |
   |                            |                              |
   |--- PUT (S3 presigned) ---> S3                             |
   |                            |                              |
   |--- POST /jobs/{id}/start ->|--- StartExecution ---------->|
   |                                                           |--- ExtractSlides (Lambda)
   |                                                           |--- Map: DesignSlide (Lambda → Bedrock)
   |                                                           |--- AssemblePptx (Lambda → S3)
   |                                                           |
   |--- GET /jobs/{id} (3초마다 폴링) ---------------------->  DynamoDB
   |<-- {status, slides[], download_url} ----                  |
   |                                                           |
   |--- POST /jobs/{id}/slides/N/retry --------- StartExecution (retry workflow) ---|
```

## 핵심 결정

- **카탈로그 매칭 없음.** Claude가 매번 슬라이드 레이아웃을 JSON 스펙으로 생성. `bedrock_client.py`의 `DESIGN_SYSTEM`에 컬러/폰트/그리드 제약만 박혀있음.
- **렌더링은 `python-pptx`** 가 담당. 13.333 × 7.5 inch (16:9). 좌표 단위는 inch.
- **재시도는 슬라이드 단위.** 사용자가 슬라이드를 골라 피드백 텍스트를 함께 전달하면 그 슬라이드만 다시 디자인 후 PPTX 재조립.
- **비동기 처리:** Step Functions Standard + Map(MaxConcurrency=5). 슬라이드 개수가 많아도 5개씩 병렬로 Bedrock 호출.
- **상태 저장:** 단일 DDB 테이블, `pk=JOB#<id>` / `sk=META | SLIDE#<3자리>` 패턴.

## 배포

`DEPLOY.md` 참조. 요약:

```powershell
cd infra
sam build --use-container
sam deploy --guided

cd ..\frontend
Copy-Item .env.example .env  # VITE_API_BASE를 ApiEndpoint로 수정
npm install
npm run build
aws s3 sync .\dist s3://pptdesigner-web-<ACCOUNT_ID>-ap-northeast-2 --delete
```

## 모델 변경

`BedrockModelId` 파라미터를 다른 모델 ID로 바꿔 재배포:

```powershell
cd infra
sam deploy --parameter-overrides BedrockModelId=apac.anthropic.claude-sonnet-4-20250514-v1:0
```
