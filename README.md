# 북 허브 (Book Hub)

AlphaFlow 플러그인 — 전자책·실물책·오디오북을 한 곳에서 관리하고, 다른 플러그인이 신뢰할 수 있는 검증 자료로 활용할 수 있게 한다.

## 데이터 범위

| 모델 | 범위 | 설명 |
|---|---|---|
| `Book` | 플랫폼(공용) | 누구나 볼 수 있는 책 메타데이터. ISBN으로 식별. |
| `BookTag` | 플랫폼(공용) | 책 분류 태그. |
| `BookVerification` | 플랫폼(공용) | 책에 대한 검증 자료(출처, 신뢰도, 메모). 다른 플러그인이 근거로 삼는다. |
| `PersonalBook` | 개인 | 사용자가 실제 소유/관리하는 책. `owner`로 격리. |

## 주요 기능

- 책 메타데이터 등록/검색 (ISBN-13, ISBN-10, 제목, 저자, 출판사 등)
- **ISBN 조회**: OpenLibrary, 네이버 책 API, 카카오 책 검색 API 지원. ISBN-13 ↔ ISBN-10 자동 변환
- 전자책/실물책/오디오북 형태 관리
- **file_hub 연동**: 표지/전자책 파일을 `filehub://` URI로 관리, picker 모달 지원
- 개인 서재: 읽고 싶음 / 읽는 중 / 완독 / 하차 상태 관리 + 진행률 업데이트
- 검증 자료 추가: 다른 플러그인이 "이 책을 근거로 삼아도 되는가"를 확인
- **공개 API**: 다른 플러그인/에이전트가 JSON으로 책을 검색·조회·검증·내 서재에 담기
- **LLM 에이전트 도구**: `book_hub__search_books`, `book_hub__get_book`, `book_hub__add_verification`
- CSV 낼 수(export) — 검색 필터 적용 가능

## 설치

AlphaFlow 관리자 페이지(`/plugins/`)에서 Git URL로 설치하거나, `plugins/book_hub/`에 클론한다.

```bash
# 외부 저장소로 배포할 경우 예시
git clone https://github.com/azxcv24/AF-book-hub.git plugins/book_hub
```

이후 플러그인 관리 페이지에서 활성화한다.

## 환경변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `BOOK_HUB_NAVER_CLIENT_ID` | 아니오 | 네이버 책 API (ISBN 조회) |
| `BOOK_HUB_NAVER_CLIENT_SECRET` | 아니오 | 네이버 책 API |
| `BOOK_HUB_KAKAO_REST_API_KEY` | 아니오 | 카카오 책 검색 API |

## API 예시

```bash
# ISBN 조회
GET /plugins/book_hub/api/isbn-lookup/?isbn=9780134685991&provider=openlibrary

# 책 검색
GET /plugins/book_hub/api/books/?q=Effective&verified_only=1

# 책 상세
GET /plugins/book_hub/api/books/1/

# 검증 자료 추가
POST /plugins/book_hub/api/books/1/verify/
{"source_url": "...", "source_title": "...", "reliability": "high", "notes": "..."}

# 내 서재에 담기
POST /plugins/book_hub/api/books/1/add-to-library/
{"format": "ebook", "status": "reading"}

# 내 책 상태/진행률 변경
POST /plugins/book_hub/api/my-books/1/status/
{"status": "completed", "progress_percent": 100}
```

## 개발 참고

- `plugin.py`의 `identifier`는 `book_hub`로, 디렉토리명과 동일.
- `urls.py`의 `app_name`은 `book_hub`.
- `apps.py`의 `name`은 `plugins.book_hub`, `label`은 `book_hub`.
- 템플릿은 `templates/book_hub/` 하위에 위치.

## TODO

- [ ] CSV 가져오기(import)
- [ ] 개인 서재 공개 범위(친구/팀) 확장
- [ ] ISBN 조회 결과 후처리(저자 누락 시 보완)
