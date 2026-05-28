# PPTdesigner

텍스트 초안만 들어있는 PPT를 업로드하면 Claude(Bedrock)가 슬라이드별로 레이아웃을 디자인해 완성된 PPTX를 돌려주는 웹 서비스.

## 기술 스택

### 백엔드 — 서버리스 (서버 프레임워크 없음)

| 영역 | 기술 |
|---|---|
| 런타임 | **AWS Lambda** (Python 3.13) — FastAPI/Flask 같은 웹 프레임워크 사용 안 함. 각 엔드포인트가 독립된 Lambda 함수 |
| API | **API Gateway HTTP API** — 라우팅 + CORS 처리 |
| LLM | **AWS Bedrock** + Claude Opus 4.7 (글로벌 교차 리전 추론) |
| 오케스트레이션 | **Step Functions** Standard + Map(MaxConcurrency=5) — 슬라이드 병렬 디자인 |
| 데이터 | **DynamoDB** 단일 테이블 (`pk=JOB#<id>` / `sk=META \| SLIDE#<n>`) |
| 파일 저장 | **S3** — 업로드 PPT, 디자인 결과 PPTX (presigned URL로 직접 업/다운로드) |
| PPTX 생성 | **python-pptx** 라이브러리 |

### 프론트엔드

| 영역 | 기술 |
|---|---|
| 빌드 | **Vite 5** |
| UI | **React 18** + **TypeScript 5** |
| 미리보기 | **SVG** (`foreignObject` + HTML 텍스트) |
| 호스팅 | **S3 정적 호스팅** + **CloudFront** CDN |

### 인프라 / 배포

| 영역 | 기술 |
|---|---|
| IaC | **AWS SAM** (CloudFormation 확장) — 모든 리소스를 `infra/template.yaml`에 선언 |
| 배포 | `sam build` + `sam deploy` (CloudShell에서 실행) |
| 리전 | `ap-northeast-2` (서울) |

## 구조

```
PPTdesigner/
├── backend/                  # Lambda 함수 (Python 3.13)
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

`BedrockModelId` 파라미터를 다른 모델의 **추론 프로파일 ID**로 바꿔 재배포. 사용 가능한 ID는 `aws bedrock list-inference-profiles --region <리전>` 으로 확인:

```powershell
cd infra
# Opus 4.7 (현재 권장, 기본값 — 글로벌 프로파일)
sam deploy --parameter-overrides BedrockModelId=global.anthropic.claude-opus-4-7
# Sonnet 4.6 (대안 — 글로벌 프로파일)
sam deploy --parameter-overrides BedrockModelId=global.anthropic.claude-sonnet-4-6
```
