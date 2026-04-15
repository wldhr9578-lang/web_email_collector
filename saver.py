"""수집 결과 CSV / TXT 저장"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .config import get_downloads_dir


def _make_filename(keyword: str, ext: str) -> str:
    safe = keyword.replace(" ", "_").replace("/", "_")[:30]
    date = datetime.now().strftime("%Y%m%d_%H%M")
    return f"webemail_{safe}_{date}.{ext}"


def save_csv(results: List[Dict], keyword: str, out_dir: Path | None = None) -> Path:
    """
    results: crawl_all 반환값
    CSV 컬럼: 번호, 사이트명, URL, 이메일1, 이메일2, ..., 전화번호, 서브페이지수
    """
    out_dir = out_dir or get_downloads_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _make_filename(keyword, "csv")

    # 이메일 최대 갯수 파악 (컬럼 수 결정)
    max_emails = max((len(r.get("emails", [])) for r in results), default=1)
    max_emails = min(max_emails, 10)  # 최대 10개 컬럼

    fieldnames = (
        ["번호", "사이트명", "URL"]
        + [f"이메일{i+1}" for i in range(max_emails)]
        + ["전화번호", "서브페이지수", "비고"]
    )

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for i, r in enumerate(results, 1):
            emails = r.get("emails", [])
            row = {
                "번호": i,
                "사이트명": r.get("title", ""),
                "URL": r.get("url", ""),
                "전화번호": ", ".join(r.get("phones", [])),
                "서브페이지수": r.get("subpages_checked", 0),
                "비고": r.get("error", ""),
            }
            for j, email in enumerate(emails[:max_emails]):
                row[f"이메일{j+1}"] = email

            writer.writerow(row)

    return path


def save_txt(results: List[Dict], keyword: str, out_dir: Path | None = None) -> Path:
    """읽기 편한 TXT 형식으로 저장"""
    out_dir = out_dir or get_downloads_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _make_filename(keyword, "txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"=== 웹 이메일 수집 결과 ===\n")
        f.write(f"키워드: {keyword}\n")
        f.write(f"수집일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"총 사이트: {len(results)}개\n")
        email_count = sum(len(r.get("emails", [])) for r in results)
        f.write(f"총 이메일: {email_count}개\n")
        f.write("=" * 50 + "\n\n")

        for i, r in enumerate(results, 1):
            f.write(f"[{i}] {r.get('title', '(제목없음)')}\n")
            f.write(f"    URL   : {r.get('url', '')}\n")

            emails = r.get("emails", [])
            if emails:
                for email in emails:
                    f.write(f"    이메일: {email}\n")
            else:
                f.write(f"    이메일: (없음)\n")

            phones = r.get("phones", [])
            if phones:
                for phone in phones:
                    f.write(f"    전화  : {phone}\n")

            if r.get("error"):
                f.write(f"    오류  : {r['error']}\n")

            f.write("\n")

    return path


def save_json(results: List[Dict], keyword: str, out_dir: Path | None = None) -> Path:
    """JSON 형식 저장 (개발자용)"""
    out_dir = out_dir or get_downloads_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _make_filename(keyword, "json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "keyword": keyword,
                "collected_at": datetime.now().isoformat(),
                "total_sites": len(results),
                "total_emails": sum(len(r.get("emails", [])) for r in results),
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return path
