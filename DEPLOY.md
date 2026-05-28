# PPTdesigner AWS 배포 가이드 (GitHub + AWS Console)

> 빌드(`sam build`, `npm run build`)는 콘솔 우상단의 **AWS CloudShell**(브라우저 터미널)에서 실행합니다. SAM CLI, Node, AWS CLI, Git 모두 미리 깔려 있습니다.

전체 흐름:

| 단계 | 화면 | 하는 일 |
|---|---|---|
| 1 | Bedrock 콘솔 | Claude 모델 첫 호출(자동 활성화) + 추론 프로파일 ID 확인 |
| 2 | GitHub 웹 + 로컬 git | 저장소 생성 + 초기 코드 push |
| 3 | CloudShell | `git clone` + `sam build` + `sam deploy` |
| 4 | CloudFormation 콘솔 | 배포 결과 확인 (Outputs) |
| 5 | CloudShell | 프론트엔드 빌드 + S3 sync |
| 6 | CloudFront 콘솔 | 캐시 무효화 |
| 7 | 브라우저 | 동작 테스트 |
| 8 | (반복) 로컬 push → CloudShell pull | 코드 수정 시 재배포 |
| 9 | CloudWatch / SF 콘솔 | 문제 발생 시 디버깅 |

리전은 모두 **서울(ap-northeast-2)**. 콘솔 우상단 리전 선택기에서 `아시아 태평양(서울) ap-northeast-2`로 고정.

---

## 0. 사전 준비

| 항목 | 설명 |
|---|---|
| AWS 계정 | 결제 등록 완료, IAM 사용자에 `AdministratorAccess` 권장 |
| GitHub 계정 | 무료 계정으로 충분. 저장소는 **Public**도 무방 (이 프로젝트엔 비밀이 코드에 없음 — 자격증명은 CloudShell IAM, API URL은 `.env` 분리) |
| Git (로컬 PC) | https://git-scm.com/download/win — 설치만 하면 됨. 설정은 기본값 그대로 Next 연타 |

확인:

```powershell
git --version
# git version 2.x.x 가 나오면 OK
```

> ✋ Git 외 다른 도구(Python, Node, SAM, Docker)는 로컬에 **설치하지 않습니다**. 모두 CloudShell에서 동작합니다.

---

## 1. Bedrock 모델 첫 호출(자동 활성화) + 추론 프로파일 ID 확인

> **⚠️ 변경 사항 (2025년~)**: 기존의 **Model access** 페이지는 **폐기(retired)** 되었습니다. AWS 모든 상용 리전에서 서버리스 파운데이션 모델은 계정에서 **처음 호출하는 순간 자동으로 활성화**됩니다. 별도의 액세스 신청·승인 절차가 없습니다.
>
> 단, **Anthropic 모델은 최초 1회 사용 사례(use case) 정보 제출**이 필요할 수 있습니다. Bedrock 콘솔의 Model catalog에서 Claude 모델을 처음 열 때 폼이 한 번 뜨고, 제출 즉시 사용 가능합니다.

이 단계에서 할 일은 **단 두 가지**:
1. (필요 시) Anthropic Claude 모델의 use case 폼을 한 번 제출해서 첫 호출 가능 상태로 만들기
2. 배포에 입력할 **추론 프로파일 ID** 문자열을 복사해 두기

### 1.1 모델 사용 준비 (use case 폼 제출, 최초 1회)

1. AWS 콘솔 로그인 → 우상단 리전을 **아시아 태평양(서울) ap-northeast-2** 로 변경
2. 상단 검색창에 `Bedrock` → **Amazon Bedrock**
3. 좌측 메뉴 **Model catalog** → 사용할 Anthropic 모델 클릭:
   - **Claude Sonnet 4.6** (이 프로젝트의 권장 모델)
   - Claude Sonnet 4.5 / Claude Sonnet 4 / Claude 3.7 Sonnet (대안)
4. 화면 안내에 따라 **회사/사용 사례 정보 폼**이 뜨면 작성 후 제출 (계정당 1회). 폼이 안 뜨면 이미 사용 가능 상태이므로 그냥 다음 단계로.

> 폼 제출 후에도 계정 관리자는 **IAM 정책 / Service Control Policy**로 모델 호출을 제한할 수 있습니다. `AdministratorAccess`가 아닌 IAM 사용자로 배포한다면 `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` 권한이 있는지 확인하세요.

### 1.2 추론 프로파일 ID — 그냥 기본값 쓰면 됩니다

**Sonnet 4.6의 APAC 추론 프로파일 ID는 콘솔에서 찾지 않아도 됩니다.** Bedrock 교차 리전 추론 프로파일 ID는 항상 다음 패턴으로 만들어집니다:

```
<리전prefix>.<모델ID>
```

스크린샷에서 확인한 Sonnet 4.6 모델 ID는 `anthropic.claude-sonnet-4-6` 이므로, APAC 프로파일은 다음과 같이 됩니다:

```
apac.anthropic.claude-sonnet-4-6
```

이 값이 이미 `infra/template.yaml`의 `BedrockModelId` Default로 박혀 있으므로, 3.4단계의 `sam deploy --guided` 프롬프트에서 **그냥 Enter** 만 누르면 됩니다.

> 콘솔에서 직접 확인하고 싶다면: Bedrock 콘솔 좌측에서 **Cross-region inference** / **Inference profiles** 메뉴를 찾으면 되지만, AWS 콘솔 UI 개편으로 위치가 자주 바뀝니다. 모델 상세 페이지의 "추론 유형: 교차 리전 추론" 항목이 보이면 위 패턴이 그대로 적용된다고 보면 됩니다.
>
> 🚨 모델 ID(`anthropic.claude-...`)를 그대로 쓰면 호출 시 `on-demand throughput isn't supported` 에러가 납니다. 반드시 `apac.` 접두사가 붙은 추론 프로파일 ID를 써야 합니다 — 코드 Default 그대로 두면 자동으로 그렇게 됩니다.

---

## 2. GitHub 저장소 만들고 코드 푸시

### 2.1 GitHub에서 빈 저장소 만들기

1. https://github.com/new
2. **Repository name**: `pptdesigner` (원하는 이름)
3. **Public** 또는 **Private** 선택 — 이 프로젝트는 비밀 정보가 코드에 없으므로 **Public**도 안전하고 CloudShell clone이 더 편합니다. 회사 코드라 비공개로 두고 싶으면 Private.
4. **README**, **.gitignore**, **license** 옵션은 **모두 체크 해제** (이미 로컬에 .gitignore 있음)
5. **Create repository** 클릭
6. 다음 화면의 명령 중 `…or push an existing repository from the command line` 블록의 두 줄을 복사해 둠. 형태:
   ```
   git remote add origin https://github.com/<USERNAME>/pptdesigner.git
   git branch -M main
   git push -u origin main
   ```

### 2.2 로컬에서 초기 커밋 + Push (PowerShell)

```powershell
cd C:\Users\USER\Desktop\Workspace\96_개발\PPTdesigner

git init
git add .
git config user.email "you@example.com"
git config user.name "Your Name"
git commit -m "initial commit"

# 2.1에서 복사한 명령 그대로 붙여넣기
git remote add origin https://github.com/<USERNAME>/pptdesigner.git
git branch -M main
git push -u origin main
```

> Push 시 GitHub 계정 인증 창이 뜹니다. **HTTPS + 브라우저 로그인** 흐름이 가장 쉽고, 한 번 인증하면 Windows Credential Manager가 토큰을 저장해 다음번부터 자동입니다.
>
> 2단계 인증 사용자는 OAuth 브라우저 로그인이 안 되면 GitHub → Settings → Developer settings → **Personal access tokens (classic)** → **Generate new token** → `repo` 권한 체크 → 토큰 생성 후, push 시 비밀번호 자리에 그 토큰을 붙여넣으세요.

확인: GitHub 저장소 페이지 새로고침 → `backend/`, `frontend/`, `infra/` 등이 보이면 OK.

### 2.3 CloudShell용 GitHub 토큰 만들기

> **Public 저장소**라면 `git clone`은 토큰 없이 됩니다. CloudShell에서 push까지 할 계획이 없다면(=samconfig.toml을 로컬에서만 커밋한다면) 이 단계를 **건너뛰어도** 됩니다. push도 CloudShell에서 하고 싶다면 아래 절차로 토큰을 만드세요.
>
> **Private 저장소**라면 clone에도 토큰이 필수입니다.

**Fine-grained Personal Access Token** 한 개를 만들어 두면 깔끔합니다.

1. GitHub 우상단 프로필 → **Settings** → 좌측 하단 **Developer settings**
2. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
3. 다음과 같이 설정:
   - **Token name**: `pptdesigner-cloudshell`
   - **Expiration**: 90 days (또는 원하는 기간)
   - **Repository access**: **Only select repositories** → `pptdesigner` 선택
   - **Repository permissions**:
     - **Contents**: **Read and write** (push도 가능하게)
     - **Metadata**: Read-only (자동)
   - 나머지는 그대로
4. **Generate token** → 화면에 한 번만 보이는 토큰 문자열(예: `github_pat_...`) 복사
5. 안전한 곳에 임시 저장 (3.2에서 사용)

---

## 3. CloudShell에서 백엔드 빌드 & 배포

### 3.1 CloudShell 열기

1. AWS 콘솔 우상단 **`>_` 아이콘** 클릭 → 하단 패널에 CloudShell이 열림
2. 처음이면 1~2분 후 프롬프트 나타남
3. 리전 확인:
   ```bash
   aws configure get region
   # ap-northeast-2 가 아니면 콘솔 리전을 서울로 바꾸고 CloudShell 새로고침
   ```

### 3.2 저장소 Clone

**Public 저장소 (권장, 토큰 불필요):**

```bash
git clone https://github.com/<USERNAME>/pptdesigner.git
cd pptdesigner
```

**Private 저장소 (토큰 필요):**

```bash
git clone https://<USERNAME>:<TOKEN>@github.com/<USERNAME>/pptdesigner.git
cd pptdesigner
```

> Private 저장소: `<USERNAME>`, `<TOKEN>` 두 자리를 실제 값으로 채워서 한 줄로 실행. 토큰은 셸 히스토리에 남으니, 한 번 clone한 뒤 `history -c && history -w` 로 지우면 더 안전합니다.
>
> CloudShell에서 push까지 할 계획이라면(예: 3.5단계 samconfig.toml 커밋), 매번 토큰을 안 박게:
> ```bash
> git config --global credential.helper 'store --file ~/.git-credentials'
> # 다음 번 push 시 입력한 인증 정보가 ~/.git-credentials에 저장됨 (CloudShell 홈은 영구 보존)
> ```

### 3.3 SAM 버전 확인

```bash
sam --version
# SAM CLI, version 1.x.x 가 나오면 OK
```

없거나 오래되면:
```bash
pip3 install --user --upgrade aws-sam-cli
export PATH=$HOME/.local/bin:$PATH
```

### 3.4 빌드 + 첫 배포 (대화형)

```bash
cd infra
sam build
```

처음 한 번은 의존성 다운로드로 2~4분.

```bash
sam deploy --guided
```

다음과 같이 답합니다:

```
Stack Name [sam-app]:                          pptdesigner
AWS Region [ap-northeast-2]:                   [Enter]
Parameter BedrockModelId [apac.anthropic.claude-sonnet-4-6]: [Enter] (콘솔 ID와 일치하면 그대로, 다르면 복사한 값 붙여넣기)
Parameter CorsOrigin [*]:                      [Enter]
Confirm changes before deploy [y/N]:           y
Allow SAM CLI IAM role creation [Y/n]:         y
Disable rollback [y/N]:                        n
RetrySlideFn may not have authorization defined ... [y/N]: y
GetJobFn ...:                                  y
CreateJobFn ...:                               y
StartJobFn ...:                                y
Save arguments to configuration file [Y/n]:    y
SAM configuration file [samconfig.toml]:       [Enter]
SAM configuration environment [default]:       [Enter]
```

이후 SAM이 CloudFormation **changeset(변경 예정 리소스 목록)** 을 출력하고 마지막으로 한 번 더 묻습니다:

```
Previewing CloudFormation changeset before deployment
======================================================
... (생성/수정/삭제될 리소스 목록이 표 형태로 출력됨)

Deploy this changeset? [y/N]:                  y
```

첫 배포면 모든 리소스가 `Add`로 표시되는 게 정상입니다. `y` 입력하면 실제 배포가 시작됩니다.

> 이 한 번 더 묻는 단계는 위에서 `Confirm changes before deploy`에 `y`로 답했기 때문에 나타납니다. 다음번부터 `samconfig.toml`에 그 답이 저장돼 있어 같은 흐름이 반복됩니다 — 매번 changeset을 눈으로 확인할 수 있어 안전합니다. 자동 배포 흐름을 원하면 `samconfig.toml`에서 `confirm_changeset = false`로 바꾸세요.

5~10분 후 `Successfully created/updated stack - pptdesigner` 메시지.

### 3.5 samconfig.toml을 GitHub에 같이 올리기 (선택, 강력 추천)

방금 생성된 `samconfig.toml`을 커밋해 두면, 다음에 다른 PC/다른 CloudShell에서 clone해도 `sam deploy` 한 줄로 재배포 가능합니다. 다음 단계의 `git pull` 흐름이 더 깔끔해집니다.

CloudShell에서:
```bash
cd ~/pptdesigner
git add infra/samconfig.toml
git -c user.email=cloudshell@local -c user.name=cloudshell commit -m "add samconfig.toml"
git push
```

---

## 4. CloudFormation에서 배포 결과 확인

배포 끝에 출력된 5개 값(`ApiEndpoint`, `AssetsBucketName`, `FrontendBucketName`, `FrontendUrl`, `JobsTableName`)을 메모해 둡니다. 콘솔에서도 다시 볼 수 있습니다:

1. 콘솔 → **CloudFormation** → 스택 `pptdesigner` 클릭 → **Outputs** 탭

---

## 5. 프론트엔드 빌드 & S3 업로드 (CloudShell)

### 5.1 API 엔드포인트를 .env에 박기

```bash
cd ~/pptdesigner/frontend
cp .env.example .env
nano .env
# VITE_API_BASE=https://xxxxxxx.execute-api.ap-northeast-2.amazonaws.com
# Ctrl+O → Enter → Ctrl+X
```

### 5.2 빌드 + 업로드

```bash
npm install
npm run build

# 4단계의 FrontendBucketName 값으로:
aws s3 sync dist s3://pptdesigner-web-123456789012-ap-northeast-2 --delete
```

> .env 파일은 빌드 결과에 박혀 들어가는 값이라 GitHub에 commit하지 않습니다 (이미 `.gitignore`에 `.env` 포함되어 있음).

---

## 6. CloudFront 캐시 무효화

1. 콘솔 → **CloudFront** → Distributions 목록에서 `FrontendUrl`의 도메인(예: `d123abcdef.cloudfront.net`)을 가진 행 클릭
2. **Invalidations** 탭 → **Create invalidation**
3. Path 입력란에 `/*` → **Create invalidation**
4. 상태가 `Completed`로 바뀌면 (1~3분) 끝

---

## 7. 동작 테스트

1. 새 탭에서 `FrontendUrl` 열기
2. PPT 드래그앤드롭
3. 화면이 `대기 → 시작 중 → 디자인 중 → 완료` 로 진행
4. **PPTX 다운로드** 버튼 → 결과 확인
5. 슬라이드 카드의 **🔄 재시도** → 피드백(선택) → 실행 → 해당 슬라이드만 재디자인 후 PPTX 재조립

---

## 8. 재배포 (GitHub 방식의 핵심 장점)

코드를 수정한 후 배포하는 흐름이 가장 큰 차이입니다.

### 8.1 백엔드 코드 수정 시

**로컬:**
```powershell
cd C:\Users\USER\Desktop\Workspace\96_개발\PPTdesigner
# (수정 후)
git add -A
git commit -m "fix: tweak design prompt"
git push
```

**CloudShell:**
```bash
cd ~/pptdesigner
git pull
cd infra
sam build && sam deploy
```

질문 없이 바로 배포됩니다 (`samconfig.toml` 덕분).

### 8.2 프론트엔드 코드 수정 시

**로컬:** push (위와 동일)

**CloudShell:**
```bash
cd ~/pptdesigner
git pull
cd frontend
npm run build
aws s3 sync dist s3://pptdesigner-web-... --delete
```

그 후 6단계(캐시 무효화) 반복.

### 8.3 GitHub 웹 에디터로 간단히 고치고 싶을 때

GitHub 저장소 페이지에서 파일을 직접 누르면 연필 아이콘으로 브라우저에서 편집·커밋 가능 — 작은 수정에 편리합니다 (예: 디자인 시스템 색상 바꾸기).

수정 후 CloudShell에서 `git pull` 만 하면 동일하게 재배포 가능.

---

## 9. 디버깅

### 9.1 Step Functions 실행 상태

1. 콘솔 → **Step Functions** → State machines → `pptdesigner-MainStateMachine-...` 클릭
2. **Executions** 탭 → 최근 실행 클릭 → **Graph view**
3. 빨간색(실패) 노드 클릭 → 우측 패널에서 입출력/에러 메시지 확인

### 9.2 Lambda 로그

1. 콘솔 → **CloudWatch** → Log groups
2. 검색창에 `pptdesigner` → 의심되는 함수의 로그 그룹 클릭 (디자인 실패면 보통 `/aws/lambda/pptdesigner-DesignFn-...`)
3. 최근 Log stream → 에러 확인

흔한 에러:

| 에러 | 원인 / 해결 |
|---|---|
| `AccessDeniedException ... bedrock:InvokeModel` | (a) Anthropic 모델 use case 폼 미제출 — 1.1단계 수행, (b) IAM/SCP에서 `bedrock:InvokeModel`이 거부됨, (c) `BedrockModelId`가 추론 프로파일이 아님. (c)는 CloudFormation 콘솔 → 스택 → **Update** → **Use existing template** → Parameters에서 ID 수정 |
| `ValidationException ... on-demand throughput isn't supported` 또는 `model identifier is invalid` | 추론 프로파일 ID가 잘못됨. 모델 ID(`anthropic.claude-...`)를 그대로 썼거나, Bedrock 콘솔의 실제 프로파일 ID와 철자가 다른 경우. CloudFormation 콘솔 → 스택 → **Update** → **Use existing template** → Parameters에서 `BedrockModelId`를 콘솔의 실제 ID(`apac.anthropic.claude-sonnet-4-6` 등)로 수정 |
| `Could not find module functions...` | `sam build`를 건너뛰고 `sam deploy`만 했음. `cd ~/pptdesigner/infra && sam build && sam deploy` |
| 프론트에서 CORS 에러 | `CorsOrigin` 파라미터를 도메인으로 좁혔는데 도메인이 정확하지 않음. `*` 로 일단 되돌려 테스트 |
| 빈 PPTX 다운로드 | `pptdesigner-AssembleFn-*` 로그. 보통 슬라이드 스펙 파싱 실패 — `DesignFn` 로그에서 Claude의 raw 응답 확인 |

### 9.3 DynamoDB에서 작업 상태 직접 보기

1. 콘솔 → **DynamoDB** → Tables → `pptdesigner-JobsTable-...`
2. **Explore table items** → `pk=JOB#xxx`, `sk=META` 행 클릭 → `status`, `error` 확인

---

## 10. 운영 시 좁히기 (선택)

### 10.1 CORS 좁히기

CloudFormation 콘솔 → 스택 `pptdesigner` → **Update** → **Use existing template** → Parameters에서 `CorsOrigin`을 `https://d123abcdef.cloudfront.net` 로 변경 → Update stack.

### 10.2 인증

지금은 누구나 호출 가능. 운영 전:
- API Gateway HTTP API에 **Cognito JWT authorizer** 추가
- 또는 API Key + Usage Plan

### 10.3 GitHub Actions로 자동 배포 (다음 단계)

`.github/workflows/deploy.yml`을 만들고 OIDC로 AWS 권한을 주면, `git push` 만으로 자동 배포 가능합니다. 본 가이드 범위 밖이지만 GitHub 기반이라 자연스럽게 확장됩니다.

---

## 11. 정리 (모두 삭제)

S3 버킷이 비어있어야 스택 삭제가 됩니다.

1. **S3 콘솔** → `pptdesigner-assets-...` 버킷 → **Empty**
2. 같은 방법으로 `pptdesigner-web-...` Empty
3. **CloudFormation 콘솔** → 스택 `pptdesigner` → **Delete**
4. 5~10분 후 스택 삭제 완료
5. (선택) GitHub 저장소도 정리하려면 GitHub Settings → Danger Zone → Delete repository

---

## 자주 마주치는 에러 모음

**스택 시작부터 `Stack ... is in ROLLBACK_COMPLETE state`**
→ 같은 이름의 실패 스택 잔재. CloudFormation 콘솔에서 그 스택을 먼저 Delete 후 재배포.

**`Authentication failed for 'https://github.com/...'` (CloudShell)**
→ Private 저장소 clone 시 토큰 누락/만료, 또는 Public/Private 무관하게 **push 시도** 시 토큰 미설정. 2.3에서 새 토큰 발급.

**`fatal: refusing to merge unrelated histories` (`git pull`)**
→ CloudShell과 로컬에서 따로 commit이 생긴 경우. `git pull --rebase` 시도, 충돌 나면 둘 중 한쪽을 정리.

**`samconfig.toml` 없다고 매번 `--guided` 질문이 뜸**
→ 3.5단계를 건너뛰었음. 한 번 `--guided` 실행해 생성된 `samconfig.toml`을 commit & push.

**`sam build` 시 `EACCES` / 권한 에러**
→ 이전 빌드 잔재. `rm -rf .aws-sam` 후 재시도.

**CloudShell이 끊겨도 데이터는 남나?**
→ 사용자 홈(`~/`)은 **영구 보존**입니다. 20분 유휴 시 환경만 stop 됩니다. 다시 열면 파일과 git 상태 그대로.

**여러 사람이 같은 저장소로 배포하면?**
→ 같은 AWS 스택을 두 명이 동시에 `sam deploy` 하면 충돌. 한 명만 배포 담당, 나머지는 PR만.
