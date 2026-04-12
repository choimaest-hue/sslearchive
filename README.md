# ssletv.com

썰/라노벨 2개 메인 주제로 데이터를 수집/정제하고, SEO 친화적인 정적 페이지를 생성하는 프로젝트입니다.

## 포함 기능

- 월간 베스트 기준 상위 N개 수집(기본 페이지당 5개)
- 본문 요약/발췌 + 댓글 정제 저장
- 카테고리 분류
  - 10대 이야기
  - 20대 이야기
  - 30대 이야기
  - 결혼/시집/친정
- 정적 HTML 생성
  - 메인 허브 + 썰 목록 + 라노벨 목록 + 카테고리 + 개별 글 페이지
  - `sitemap.xml`, `robots.txt` 자동 생성
- 목록 페이지네이션 (기본 10개)
- 우측 하단 `모바일/웹` 전환 버튼
- 광고 삽입용 영역 플레이스홀더
- 푸터 광고문의: `choimaest@naver.com`

## 설치

```bash
pip install -r requirements.txt
```

## 데이터 수집

```bash
python scripts/scrape_nate_pann.py --target-count 600 --top-per-page 5 --max-ranking-pages 220
```

라노벨 수집(사용자 사이트 카테고리):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/scrape_ssletv_lanovel.ps1 -TargetCount 40 -OutputPath data/lanovel_posts.json
```

주의:

- 사이트 구조 변경/차단 정책에 따라 수집 결과가 달라질 수 있습니다.
- 저작권/이용약관 리스크를 줄이기 위해 본 프로젝트는 원문 전체 복제 대신 요약/발췌 중심을 기본값으로 둡니다.

## 사이트 생성

```bash
python scripts/build_site.py --site-url https://ssletv.com
```

페이지당 10개 고정/변경:

```bash
python scripts/build_site.py --site-url https://ssletv.com --per-page 10
```

생성 결과:

- `dist/index.html` (메인 허브)
- `dist/ssul.html`
- `dist/lanovel.html`
- `dist/category-*.html`
- `dist/posts/*.html`
- `dist/lanovel-posts/*.html`
- `dist/sitemap.xml`
- `dist/robots.txt`

## 배포 팁

- 정적 호스팅(Vercel, Netlify, Cloudflare Pages, S3+CloudFront) 사용 가능
- Search Console에 `sitemap.xml` 제출
- 광고 도입 시 `ad-slot` 영역에 스크립트 삽입

## GitHub + Vercel CI/CD

이 저장소에는 `main` 브랜치 푸시 시 자동 배포되는 GitHub Actions 워크플로가 포함되어 있습니다.

- 워크플로 파일: `.github/workflows/vercel-deploy.yml`
- 동작: `build_site.py`로 `dist` 생성 -> Vercel 프로덕션 배포

GitHub 저장소 `Settings > Secrets and variables > Actions` 에 아래 시크릿을 추가하세요.

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

시크릿은 아래 명령으로 확인 가능합니다.

```bash
vercel login
vercel link
cat .vercel/project.json
```

`project.json` 안의 `orgId`, `projectId`를 각각 시크릿으로 등록하면 됩니다.
