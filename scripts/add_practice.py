"""'연습 추가' 이슈 양식 본문을 읽어 data/practices.json 에 연습 일정을 추가한다.

GitHub 이슈 양식 본문은 '### 라벨\n\n값' 형태다. ISSUE_BODY, ISSUE_NUMBER 환경변수로 받는다.
"""
import datetime as dt
import json
import os
import re
import sys

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "practices.json")


def fields(body):
    out = {}
    for label, value in re.findall(r"^###\s*(.+?)\s*\n(.*?)(?=^###|\Z)", body, re.M | re.S):
        value = value.strip()
        out[label.strip()] = "" if value == "_No response_" else value
    return out


def main():
    f = fields(os.environ.get("ISSUE_BODY", ""))
    date = f.get("날짜", "")
    m = re.match(r"^(20\d\d)[.\-/](\d{1,2})[.\-/](\d{1,2})$", date)
    if not m:
        sys.exit(f"날짜 형식이 올바르지 않습니다: '{date}' (예: 2026-10-12)")
    date = dt.date(*map(int, m.groups())).isoformat()
    headcount = re.sub(r"\D", "", f.get("인원", ""))

    practice = {
        "type": "practice",
        "date": date,
        "time": f.get("시간", ""),
        "place": f.get("장소", ""),
        "headcount": int(headcount) if headcount else None,
        "memo": f.get("메모", ""),
        "issue": int(os.environ.get("ISSUE_NUMBER") or 0) or None,
    }

    data = {"practices": []}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fp:
            data = json.load(fp)
    # 같은 이슈를 다시 처리하면(수정 후 재실행) 덮어쓴다.
    data["practices"] = [p for p in data["practices"] if not practice["issue"] or p.get("issue") != practice["issue"]]
    data["practices"].append(practice)
    data["practices"].sort(key=lambda p: (p["date"], p["time"]))
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    print(f"연습 추가: {date} {practice['time']} {practice['place']} ({practice['headcount'] or '?'}명)")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as gh:
            gh.write(f"summary={date} {practice['time']} {practice['place']}\n")


if __name__ == "__main__":
    main()
