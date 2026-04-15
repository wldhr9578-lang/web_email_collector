# 🌐 Web Email Collector

키워드로 Google에서 기업 웹사이트를 검색하고, 각 사이트에서 이메일 주소를 자동 수집하는 CLI 도구입니다.
Windows / Mac 모두 지원합니다.

---

## 설치

`uv`와 `Git`이 설치되어 있어야 합니다.
처음이라면 기존 수집기 가이드의 1~2단계를 먼저 진행하세요.

### 1단계: 수집기 설치

터미널(PowerShell 또는 Terminal)을 열고 아래 명령어를 붙여넣으세요.

```
uv tool install git+https://github.com/YOUR_USERNAME/web-email-collector
```

### 2단계: 초기 설정

```
webcollect setup
```

| 항목 | 설명 | 링크 |
|------|------|------|
| Google Custom Search API Key (필수) | 검색 엔진 키, 무료 100건/일 | [Google Cloud Console](https://console.cloud.google.com) |
| Google CX ID (필수) | 커스텀 검색엔진 ID | [CSE 관리](https://cse.google.com) |
| SerpAPI Key (선택) | 대안 검색엔진, 유료 | [SerpAPI](https://serpapi.com) |

#### Google API 키 발급 절차

1. [console.cloud.google.com](https://console.cloud.google.com) 접속 → 로그인
2. 새 프로젝트 생성 → **Custom Search API** 검색 후 사용 설정
3. **사용자 인증 정보** → **API 키 만들기** → `AIza...` 형태 키 복사
4. [cse.google.com](https://cse.google.com) → **새 검색엔진 추가**
   - 검색할 사이트: `*.com` 입력 (전체 웹 검색)
   - 생성 후 **검색엔진 ID(cx)** 복사

---

## 사용법

### 기본 검색

```
webcollect search "스킨케어 기업" 20
```

키워드로 20개 사이트 검색 + 이메일 수집 + 다운로드 폴더에 CSV/TXT 자동 저장

### 멀티 키워드

```
webcollect search "스킨케어,뷰티,화장품" 10
```

키워드별 10개씩 수집, CSV 파일 각각 저장

### 단일 URL 직접 크롤링 (검색 없이)

```
webcollect crawl https://example.com
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--engine google` | google | 검색 엔진 선택 (google / serpapi) |
| `--no-deep` | deep 켜짐 | 서브페이지(연락처 페이지) 탐색 끔 |
| `--no-phone` | phone 켜짐 | 전화번호 수집 끔 |
| `--delay 1.5` | 1.0 | 요청 간 대기시간(초) |
| `--out ./결과` | Downloads | 저장 폴더 지정 |
| `--json` | 끔 | JSON 형식 추가 저장 |

### 환경 점검

```
webcollect doctor
```

---

## 저장 위치

다운로드 폴더에 자동 저장됩니다.

| 파일 | 설명 |
|------|------|
| `webemail_키워드_날짜.csv` | 결과 목록 (Excel 용) |
| `webemail_키워드_날짜.txt` | 결과 목록 (읽기 용) |

---

## 수집 정보

| 항목 | 설명 |
|------|------|
| 사이트명 | `<title>` 태그 또는 OG 태그 |
| URL | 검색 결과 원본 URL |
| 이메일 | mailto 링크 + 정규식 + 난독화 복원 |
| 전화번호 | 한국 번호 패턴 |
| 서브페이지수 | 탐색한 연락처/소개 페이지 수 |

---

## 주의사항

- **개인정보보호법**: 수집한 이메일은 반드시 관련 법령을 준수하여 사용하세요.
- **robots.txt**: 크롤러는 표준 HTTP 헤더를 사용하며, 과도한 요청을 피하기 위해 딜레이가 적용됩니다.
- Google Custom Search API 무료 한도는 **100건/일**입니다. 초과 시 SerpAPI를 사용하세요.
