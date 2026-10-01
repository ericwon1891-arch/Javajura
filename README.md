# 자바주라 일정표

게임원 경기 일정과 팀 연습을 한 페이지에 보여주는 정적 사이트입니다 (GitHub Pages).

## 처음 한 번 설정
1. 게임원 팀 번호는 36818 (워크플로에 기본값으로 들어 있음, 바꾸려면 Actions 변수 `GAMEONE_CLUB_IDX`)
2. Settings → Pages → Source: `Deploy from a branch`, 브랜치 `main` / 폴더 `/ (root)`
3. Actions → "게임원 일정 가져오기" → Run workflow 로 첫 수집

## 연습 올리기
Issues → New issue → **연습 추가** 양식에 날짜, 시간, 장소, 인원을 채워 제출하면 1~2분 뒤 일정표에 나옵니다.
저장소 주인과 공동작업자가 올린 것만 반영됩니다. 고치려면 이슈를 수정하고, 지우려면 `data/practices.json` 에서 해당 항목을 지우세요.

## 파일
- `index.html` 일정표 페이지
- `data/games.json` 게임원에서 자동 수집 (하루 3번: 07시, 12시, 18시)
- `data/practices.json` 연습 일정
- `scripts/fetch_gameone.py`, `scripts/add_practice.py` 수집/추가 스크립트
