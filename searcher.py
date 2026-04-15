"""Google Custom Search API를 통한 웹사이트 URL 수집"""
import httpx
from typing import List, Dict
from .config import get_api_key


GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# 제외할 도메인 (SNS, 뉴스 등 일반 기업 사이트 아닌 곳)
EXCLUDE_DOMAINS = {
    "instagram.com", "facebook.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "linkedin.com", "pinterest.com",
    "naver.com", "daum.net", "nate.com", "kakao.com",
    "wikipedia.org", "namu.wiki",
    "youtube.com", "youtu.be",
    "blogspot.com", "tistory.com", "blog.naver.com",
    "coupang.com", "gmarket.co.kr", "11st.co.kr",
    "google.com", "google.co.kr", "bing.com", "yahoo.com",
}


def _is_valid_url(url: str) -> bool:
    for domain in EXCLUDE_DOMAINS:
        if domain in url:
            return False
    return url.startswith("http")


def search_urls(keyword: str, count: int = 20) -> List[Dict]:
    """
    Google Custom Search API로 키워드 검색 후 URL 목록 반환.
    count: 수집할 URL 수 (최대 100, API 1회 최대 10건)
    """
    api_key = get_api_key("GOOGLE")
    cx_id = get_api_key("GOOGLE_CX")

    if not api_key or not cx_id:
        raise ValueError("Google API 키 또는 CX ID가 설정되지 않았습니다. `webcollect setup` 실행")

    results = []
    collected = 0
    start = 1

    with httpx.Client(timeout=15) as client:
        while collected < count:
            batch = min(10, count - collected)
            params = {
                "key": api_key,
                "cx": cx_id,
                "q": keyword,
                "num": batch,
                "start": start,
                "gl": "kr",    # 한국 결과 우선
                "hl": "ko",
            }
            resp = client.get(GOOGLE_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                url = item.get("link", "")
                if _is_valid_url(url):
                    results.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                    })
                    collected += 1

            if len(items) < batch:
                break
            start += batch

    return results


def search_urls_serpapi(keyword: str, count: int = 20) -> List[Dict]:
    """
    SerpAPI를 통한 Google 검색 (대안 엔진).
    Google Custom Search API 대신 사용 가능.
    """
    api_key = get_api_key("SERPAPI")
    if not api_key:
        raise ValueError("SerpAPI 키가 설정되지 않았습니다.")

    results = []
    page = 0

    with httpx.Client(timeout=15) as client:
        while len(results) < count:
            params = {
                "api_key": api_key,
                "engine": "google",
                "q": keyword,
                "gl": "kr",
                "hl": "ko",
                "num": 10,
                "start": page * 10,
            }
            resp = client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("organic_results", [])
            if not items:
                break

            for item in items:
                url = item.get("link", "")
                if _is_valid_url(url):
                    results.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                    })
                    if len(results) >= count:
                        break
            page += 1

    return results
