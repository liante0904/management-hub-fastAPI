# API Reference — Management Hub

> **목적**: Management Hub API의 전체 엔드포인트 명세. LLM이 코드를 수정하거나 새 기능을 추가할 때 참조.

---

## 공통 사항

| 항목 | 값 |
|------|-----|
| Base URL (prod) | `https://ssh-oci.duckdns.org` |
| Base URL (dev) | `http://localhost:8003` |
| 인증 | JWT Bearer Token (Telegram Login → JWT 발급) |
| Content-Type | `application/json` |

### 인증 방식

모든 관리 API는 `Authorization: Bearer <jwt_token>` 헤더가 필요하며,
DB에서 `is_admin = TRUE`인 사용자만 접근 가능.

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8003/admin/metrics
```

---

## 1. 헬스체크 (인증 불필요)

### `GET /health`

```json
{ "status": "ok", "service": "management-hub" }
```

### `GET /admin/health`

```json
{ "status": "ok", "service": "management-hub", "timestamp": "2025-01-01T12:00:00Z" }
```

---

## 2. 시스템 메트릭 & 로그 (`/admin/*`)

### `GET /admin/metrics`

시스템 리소스 + DB + 레포트 통계. **admin 인증 필요**.

```json
{
  "overall": "online",
  "cpu": { "percent": 12.5, "cores": 4, "frequency_mhz": 2400.0 },
  "memory": { "total_gb": 23.4, "used_gb": 8.2, "percent": 35.0 },
  "disk": { "total_gb": 100.0, "used_gb": 45.0, "percent": 45.0 },
  "oci": {
    "cpu_percent": 12.5,
    "total_gb": 23.4,
    "used_gb": 8.2,
    "percent": 35.0,
    "disk_total_gb": 100.0,
    "disk_used_gb": 45.0,
    "disk_percent": 45.0
  },
  "oci2": {
    "cpu_percent": 10.5,
    "total_gb": 16.0,
    "used_gb": 4.2,
    "percent": 26.3,
    "disk_total_gb": 50.0,
    "disk_used_gb": 12.0,
    "disk_percent": 24
  },
  "database": { "status": "online", "latency_ms": 2.1 },
  "reports": { "total": 280664, "today_inserts": 142 },
  "last_activity": { "last_save_time": "20250101_120000", "last_title": "...", "last_firm": "..." }
}
```

> `oci`는 배포서버(자기자신)의 로컬 psutil 메트릭이며 항상 응답. `oci2`는 프로덕션 서버의 SSH 원격 메트릭 (연결 실패 시 `null`).

### `GET /admin/logs`

로그 디렉토리 목록.

### `GET /admin/logs?path=/host-logs/20250101`

하위 디렉토리/파일 목록.

### `GET /admin/logs/view?file=/host-logs/20250101/scraper.log&lines=500&tail=true`

로그 파일 내용 반환.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | string | (필수) | 로그 파일 절대경로 |
| `lines` | int | 500 | 반환할 라인 수 (10~5000) |
| `offset` | int | 0 | 시작 offset |
| `tail` | bool | false | `true` → 끝에서 N줄 |

---

## 3. DB 테이블 뷰어 (`/admin/db/*`)

### `GET /admin/db/tables`

메인 DB의 테이블 목록 조회.

```json
{ "tables": ["tbl_sec_reports", "tbm_sec_reports_telegram_users", "..."] }
```

### `GET /admin/db/query/{table}?limit=50`

특정 테이블의 데이터 미리보기 (Read-only). JSON 직렬화 불가능한 타입(datetime, Decimal, bytes, UUID, PG array 등)은 자동 변환.

```json
{
  "table": "tbl_sec_reports",
  "columns": ["report_id", "firm_nm", "article_title", "..."],
  "data": [
    { "report_id": 1, "firm_nm": "...", "article_title": "..." }
  ]
}
```

### `POST /admin/db/query`

커스텀 SQL 쿼리 실행 (SELECT only, 읽기 전용).

```json
// Request
{ "query": "SELECT firm_nm, COUNT(*) FROM tbl_sec_reports GROUP BY firm_nm", "limit": 50 }

// Response
{
  "columns": ["firm_nm", "count"],
  "data": [
    { "firm_nm": "하나증권", "count": 15000 }
  ]
}
```

| Rule | Description |
|------|-------------|
| SELECT only | `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE` 차단 |
| LIMIT 강제 | 미지정 시 자동 `LIMIT 50` 추가 |
| Max rows | 200 (limit 파라미터) |
| Error | 400 + 상세 메시지 |

---

## 4. 유저 관리 (`/api/users/*`)

### `GET /api/users`

유저 목록 (페이지네이션 + 검색).

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 항목 (1~100) |
| `status` | string | - | `active` / `blocked` / `inactive` |
| `search` | string | - | 이름 또는 username 검색 |

```json
{
  "users": [
    { "id": 1, "first_name": "John", "last_name": "Doe", "username": "johndoe",
      "photo_url": null, "status": "active", "is_admin": true, "created_at": 1700000000 }
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

### `GET /api/users/{user_id}`

유저 상세.

### `PUT /api/users/{user_id}/status`

```json
{ "status": "blocked" }
```
→ `{ "id": 1, "status": "blocked", "updated": true }`

유효값: `active` | `blocked` | `inactive`

### `PUT /api/users/{user_id}/admin`

```json
{ "is_admin": true }
```
→ `{ "id": 1, "is_admin": true, "updated": true }`

### `DELETE /api/users/{user_id}`

유저 삭제 (관리자 전용).

```json
{ "id": 1, "deleted": true }
```

---

## 5. 레포트 관리 (`/api/reports/*`)

### `GET /api/reports`

레포트 목록 (페이지네이션 + 다중 필터).

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 항목 (1~100) |
| `firm_nm` | string | - | 증권사명 (ILIKE) |
| `reg_dt` | string | - | 등록일자 (YYYYMMDD) |
| `sync_status` | int | - | 0=대기, 1=처리중, 2=완료, -1=실패 |
| `search` | string | - | 제목 검색 (ILIKE) |
| `sort` | string | `save_time DESC` | 정렬 (whitelist: `save_time DESC/ASC`, `reg_dt DESC/ASC`, `report_id DESC/ASC`) |

```json
{
  "reports": [
    { "report_id": 100, "firm_nm": "Test Firm", "article_title": "...",
      "sync_status": 2, "pdf_sync_status": 2, "gemini_summary": "...", ... }
  ],
  "total": 280664, "page": 1, "page_size": 20
}
```

### `GET /api/reports/{report_id}`

레포트 상세.

### `PUT /api/reports/{report_id}/sync`

동기화 상태 재설정 (재처리 트리거).

```json
{ "sync_status": 0, "pdf_sync_status": 0 }
```
→ `{ "report_id": 100, "updated": true }`

### `GET /api/reports/{report_id}/pdf`

PDF 아카이브 상태.

```json
{
  "report_id": 100, "file_path": "/path/to/pdf", "file_size": 1024000,
  "page_count": 10, "archive_status": "archived", "storage_backend": "onedrive",
  "has_text": true, "is_encrypted": false, "created_at": "2025-01-01 12:00:00"
}
```

### `GET /api/reports/fnguide`

FnGuide 요약 목록.

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | 페이지 |
| `page_size` | int | 페이지당 항목 |
| `company_name` | string | 회사명 검색 |
| `report_date` | string | YYYYMMDD |

```json
{
  "summaries": [
    { "summary_id": 1, "company_name": "삼성전자", "company_code": "005930",
      "report_title": "...", "opinion": "BUY", "target_price": "100000", ... }
  ],
  "total": 9086, "page": 1, "page_size": 20
}
```

### `GET /api/reports/send-history`

레포트 발송 이력.

| Param | Type | Description |
|-------|------|-------------|
| `report_id` | int | 특정 레포트 필터 |
| `user_id` | int | 특정 유저 필터 |
| `limit` | int | 최대 반환 (1~500, 기본 100) |

```json
[
  { "id": 1, "report_id": 100, "user_id": 1, "keyword": "삼성전자", "sent_at": "2025-01-01 12:00:00" }
]
```

---

## 6. PDF 아카이브 관리 (`/api/reports/pdf-archive/*`)

### `GET /api/reports/pdf-archive`

PDF 아카이브 목록 (필터 + 페이지네이션 + summary).

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 항목 (1~100) |
| `firm_nm` | string | - | 증권사명 (ILIKE) |
| `archive_status` | string | - | `INIT` / `ARCHIVED` |
| `reg_dt` | string | - | 등록일자 (YYYYMMDD) |
| `sync_status` | int | - | 0=대기, 1=처리중, 2=완료, 9=실패 |
| `pdf_sync_status` | int | - | PDF 동기화 상태 |
| `download_status_yn` | string | - | `Y` / `N` |
| `search` | string | - | 제목 검색 |
| `sort` | string | `report_id DESC` | `report_id`, `created_at`, `reg_dt` (ASC/DESC) |

```json
{
  "items": [
    {
      "report_id": 100, "firm_nm": "하나증권", "title": "...",
      "file_name": "report_100.pdf", "file_size": 1024000, "page_count": 10,
      "archive_status": "ARCHIVED", "storage_backend": "onedrive",
      "sync_status": 2, "pdf_sync_status": 2, "retry_count": 0,
      "has_text": true, "is_encrypted": false,
      "created_at": "2025-01-01 12:00:00", "updated_at": "2025-01-01 12:05:00"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "summary": { "archived": 120, "failed": 30 }
}
```

> `summary`는 전체 DB 기준 archived/failed 카운트. 필터와 무관하게 전체 집계를 반환.

### `GET /api/reports/pdf-archive/stats/daily?days=30`

일별 PDF 아카이브 통계.

```json
[
  { "date": "2025-01-02", "total": 50, "archived": 45, "failed": 5 }
]
```

### `GET /api/reports/pdf-archive/stats/by-firm`

증권사별 PDF 아카이브 통계.

```json
[
  { "firm_nm": "하나증권", "total": 80, "archived": 75, "failed": 5 }
]
```

### `POST /api/reports/pdf-archive/reprocess`

PDF 재처리 — 필터 조건에 맞는 건들의 sync_status를 0으로 초기화.

```json
// Request
{
  "archive_status": "INIT",
  "firm_nm": "하나",
  "sync_status": 9,
  "report_ids": [100, 101],
  "limit": 100
}

// Response
{ "matched": 500, "updated": 100, "message": "100건 재처리 요청 완료 (전체 대상: 500건)" }
```

| Param | Type | Description |
|-------|------|-------------|
| `archive_status` | string | 필터: `INIT` / `ARCHIVED` |
| `firm_nm` | string | 필터: 증권사명 |
| `reg_dt` | string | 필터: 등록일자 |
| `sync_status` | int | 필터: sync_status |
| `pdf_sync_status` | int | 필터: pdf_sync_status |
| `report_ids` | int[] | 특정 report_id 목록 (최대 500개) |
| `limit` | int | 재처리 최대 건수 (100~500) |

---

## 7. 증권사 정보 관리 (`/api/firms/*`)

### `GET /api/firms`

증권사 목록.

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | 증권사명 검색 (ILIKE) |

```json
[
  { "sec_firm_order": 1, "firm_nm": "Test Securities", "telegram_update_yn": "Y", "COMMENT_PDF_URL": null }
]
```

### `GET /api/firms/{sec_firm_order}`

증권사 상세. 없으면 404.

### `POST /api/firms`

증권사 등록.

```json
{ "sec_firm_order": 100, "firm_nm": "New Securities", "telegram_update_yn": "Y" }
```
→ `201 { "sec_firm_order": 100, "created": true }`
중복 시 → `409`

### `PUT /api/firms/{sec_firm_order}`

증권사 정보 수정 (부분 업데이트).

```json
{ "firm_nm": "Updated Name", "telegram_update_yn": "N" }
```
→ `{ "sec_firm_order": 1, "updated": true }`

### `DELETE /api/firms/{sec_firm_order}`

증권사 + 소속 게시판 일괄 삭제.

### `GET /api/firms/{sec_firm_order}/boards`

증권사별 게시판 목록.

```json
[
  { "sec_firm_order": 1, "article_board_order": 1, "board_nm": "Board A", "board_cd": "CD_A", "label_nm": "Label A" }
]
```

### `POST /api/firms/{sec_firm_order}/boards`

게시판 등록. 중복 시 409, 증권사 없으면 404.

### `PUT /api/firms/{sec_firm_order}/boards/{article_board_order}`

게시판 수정.

### `DELETE /api/firms/{sec_firm_order}/boards/{article_board_order}`

게시판 삭제.

---

## 엔드포인트 맵

```
GET    /health
GET    /admin/health
GET    /admin/metrics
GET    /admin/logs
GET    /admin/logs/view
GET    /admin/db/tables
GET    /admin/db/query/{table}
POST   /admin/db/query

GET    /api/users
GET    /api/users/{id}
PUT    /api/users/{id}/status
PUT    /api/users/{id}/admin
DELETE /api/users/{id}

GET    /api/reports
GET    /api/reports/fnguide
GET    /api/reports/send-history
GET    /api/reports/{id}
PUT    /api/reports/{id}/sync
GET    /api/reports/{id}/pdf
GET    /api/reports/pdf-archive
GET    /api/reports/pdf-archive/stats/daily
GET    /api/reports/pdf-archive/stats/by-firm
POST   /api/reports/pdf-archive/reprocess

GET    /api/firms
POST   /api/firms
GET    /api/firms/{order}
PUT    /api/firms/{order}
DELETE /api/firms/{order}
GET    /api/firms/{order}/boards
POST   /api/firms/{order}/boards
PUT    /api/firms/{order}/boards/{b_order}
DELETE /api/firms/{order}/boards/{b_order}
```

---
## 테스트 현황

```
94 passed in 3.5s

test_admin.py    ██████████ 11/11  health, metrics(oci+oci2), logs, db viewer, db sql query
test_users.py    ██████████ 13/13  list, get, status, admin toggle, delete
test_reports.py  ████████████████████████ 28/28  list, get, sync, pdf archive (list/stats/reprocess), fnguide, send-history
test_firms.py    ████████████████ 21/21  firm CRUD + board CRUD
test_auth.py     ██████████ 21/21  auth endpoints
```
