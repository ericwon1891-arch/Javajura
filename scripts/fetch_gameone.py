"""게임원(gameone.kr) 팀 일정 페이지에서 경기 일정을 가져와 data/games.json 으로 저장한다.

표준 라이브러리만 사용한다. 게임원 표 구조가 바뀌어도 머리글 이름으로 열을 찾도록 느슨하게 파싱한다.
환경변수:
  GAMEONE_CLUB_IDX  팀 번호 (gameone.kr/club/?club_idx=숫자)
  GAMEONE_SEASONS   가져올 시즌, 쉼표 구분 (기본: 올해)
"""
import datetime as dt
import html
import json
import os
import re
import ssl
import sys
import urllib.request
from html.parser import HTMLParser

BASE = "https://www.gameone.kr"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "games.json")
UA = "Mozilla/5.0 (team-schedule-bot; +https://github.com)"

COLUMN_KEYS = {
    "date": ["일시", "일자", "날짜", "경기일"],
    "time": ["시간"],
    "place": ["구장", "장소", "경기장"],
    "league": ["리그", "대회"],
    "opponent": ["상대", "대진", "VS", "vs"],
    "result": ["결과", "스코어", "점수"],
}


class TableParser(HTMLParser):
    """페이지의 모든 <table>을 [행][셀] 텍스트로 모은다. 셀 안의 링크도 함께 기록한다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack = [], []
        self._row = self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = {"text": "", "links": [], "th": tag == "th"}
        elif tag == "a" and self._cell is not None:
            href = dict(attrs).get("href")
            if href:
                self._cell["links"].append(html.unescape(href))
        elif tag == "br" and self._cell is not None:
            self._cell["text"] += " "

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._cell["text"] = re.sub(r"\s+", " ", self._cell["text"]).strip()
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row and self._stack:
                self._stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data


# 게임원 서버는 오래된 DH 키를 써서 기본 보안 수준(SECLEVEL=2)에서는 접속이 거부된다.
# 인증서 검증은 그대로 두고 이 접속에서만 보안 수준을 1로 낮춘다.
SSL_CTX = ssl.create_default_context()
SSL_CTX.set_ciphers("DEFAULT:@SECLEVEL=1")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko"})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")


def find_column(headers, field):
    for i, h in enumerate(headers):
        if any(k in h for k in COLUMN_KEYS[field]):
            return i
    return None


def parse_date(text, season):
    """'2026-10-05', '2026.10.05 (일) 08:00', '10.05(일)', '10/05' 등을 (YYYY-MM-DD, HH:MM|None)으로."""
    m = re.search(r"(20\d\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"(?<!\d)(\d{1,2})\s*[.\-/월]\s*(\d{1,2})(?!\d)", text)
        if not m:
            return None, None
        y, (mo, d) = season, map(int, m.groups())
    try:
        date = dt.date(y, mo, d).isoformat()
    except ValueError:
        return None, None
    t = re.search(r"(\d{1,2})\s*:\s*(\d{2})", text[m.end():])
    return date, (f"{int(t.group(1)):02d}:{t.group(2)}" if t else None)


def parse_time(text):
    t = re.search(r"(\d{1,2})\s*:\s*(\d{2})", text)
    return f"{int(t.group(1)):02d}:{t.group(2)}" if t else None


def games_from_tables(tables, season, club_idx):
    games = []
    for table in tables:
        header_row = next((r for r in table if any(c["th"] for c in r)), table[0] if table else None)
        if not header_row:
            continue
        headers = [c["text"] for c in header_row]
        col = {f: find_column(headers, f) for f in COLUMN_KEYS}
        if col["date"] is None:
            continue
        for row in table:
            if row is header_row or len(row) < len(headers) - 1:
                continue
            cells = [c["text"] for c in row]
            get = lambda f: cells[col[f]] if col[f] is not None and col[f] < len(cells) else ""
            date, time = parse_date(get("date"), season)
            if not date:
                continue
            link = next((l for c in row for l in c["links"] if "game_idx" in l), None)
            games.append({
                "type": "game",
                "date": date,
                "time": time or parse_time(get("time")),
                "place": get("place"),
                "league": get("league"),
                "opponent": get("opponent"),
                "result": get("result"),
                "url": (BASE + link if link and link.startswith("/") else link)
                       or f"{BASE}/club/info/schedule/table?club_idx={club_idx}&season={season}",
            })
    return games


def main():
    club_idx = os.environ.get("GAMEONE_CLUB_IDX", "").strip()
    if not club_idx.isdigit():
        sys.exit("GAMEONE_CLUB_IDX 가 설정되지 않았습니다 (gameone.kr/club/?club_idx=숫자).")
    this_year = dt.date.today().year
    seasons = [int(s) for s in os.environ.get("GAMEONE_SEASONS", str(this_year)).split(",") if s.strip()]

    games, debug = [], os.environ.get("GAMEONE_DEBUG") == "1"
    for season in seasons:
        url = f"{BASE}/club/info/schedule/table?club_idx={club_idx}&season={season}"
        page = fetch(url)
        if debug:
            os.makedirs("debug", exist_ok=True)
            with open(f"debug/table_{season}.html", "w", encoding="utf-8") as f:
                f.write(page)
        p = TableParser()
        p.feed(page)
        found = games_from_tables(p.tables, season, club_idx)
        print(f"{season}: 표 {len(p.tables)}개, 경기 {len(found)}개 ({url})")
        if debug:
            for t in p.tables:
                for r in t:
                    print("   ", " | ".join(c["text"] for c in r))
                m = re.search(r"BOX SCORE", page)
                if m:
                    print("   RAW:", re.sub(r"\s+", " ", page[max(0, m.start() - 2500):m.start() + 200]))
                print("   ---")
        games += found

    if not games:
        sys.exit("경기를 하나도 찾지 못했습니다. 게임원 페이지 구조가 바뀌었는지 GAMEONE_DEBUG=1 로 확인하세요.")

    seen, unique = set(), []
    for g in sorted(games, key=lambda g: (g["date"], g["time"] or "")):
        key = (g["date"], g["time"], g["opponent"])
        if key not in seen:
            seen.add(key)
            unique.append(g)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes"),
                   "club_idx": int(club_idx), "games": unique}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"저장: 경기 {len(unique)}개 -> data/games.json")


if __name__ == "__main__":
    main()
