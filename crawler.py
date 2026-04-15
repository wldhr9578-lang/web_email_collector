"""비동기 웹 크롤러 - 사이트에서 이메일 수집"""
import asyncio
import time
import re
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .extractor import extract_emails, extract_phones

# 연락처 관련 페이지 키워드 (우선 탐색)
CONTACT_KEYWORDS = [
    "contact", "about", "info", "reach", "connect",
    "문의", "연락", "소개", "about-us", "contact-us",
    "company", "회사", "기업", "team",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _get_base_domain(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _get_page_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    if tag:
        return tag.get_text(strip=True)[:100]
    og = soup.find("meta", property="og:site_name")
    if og:
        return og.get("content", "")[:100]
    return ""


def _find_contact_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """연락처 관련 링크 우선 탐색"""
    links = []
    seen: Set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").lower()
        text = tag.get_text(strip=True).lower()

        is_contact = any(kw in href or kw in text for kw in CONTACT_KEYWORDS)
        if not is_contact:
            continue

        full_url = urljoin(base_url, tag["href"])
        # 같은 도메인만
        if urlparse(full_url).netloc != urlparse(base_url).netloc:
            continue
        if full_url not in seen and full_url != base_url:
            seen.add(full_url)
            links.append(full_url)

    return links[:5]  # 최대 5개 서브페이지


async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """단일 페이지 비동기 fetch, 실패 시 None 반환"""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=12)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type or "html" in content_type:
                return resp.text
        return None
    except Exception:
        return None


async def crawl_site(
    url: str,
    delay: float = 1.0,
    deep: bool = True,
    include_phone: bool = True,
) -> Dict:
    """
    단일 사이트 크롤링 후 이메일/전화 추출.

    Returns:
        {
            "url": str,
            "title": str,
            "emails": list[str],
            "phones": list[str],
            "subpages_checked": int,
            "error": str | None,
        }
    """
    result = {
        "url": url,
        "title": "",
        "emails": [],
        "phones": [],
        "subpages_checked": 0,
        "error": None,
    }

    all_emails: Set[str] = set()
    all_phones: Set[str] = set()

    async with httpx.AsyncClient(headers=HEADERS, timeout=12) as client:
        # 메인 페이지 크롤링
        html = await _fetch_page(client, url)
        if not html:
            result["error"] = "페이지 로드 실패"
            return result

        soup = BeautifulSoup(html, "lxml")
        result["title"] = _get_page_title(soup)
        text = soup.get_text(" ", strip=True)

        all_emails |= extract_emails(html)      # HTML 원문 (mailto 포함)
        all_emails |= extract_emails(text)       # 텍스트 추출본
        if include_phone:
            all_phones |= extract_phones(text)

        # 서브페이지 탐색 (연락처 페이지)
        if deep:
            contact_links = _find_contact_links(soup, url)
            for sub_url in contact_links:
                await asyncio.sleep(delay)
                sub_html = await _fetch_page(client, sub_url)
                if sub_html:
                    sub_soup = BeautifulSoup(sub_html, "lxml")
                    sub_text = sub_soup.get_text(" ", strip=True)
                    all_emails |= extract_emails(sub_html)
                    all_emails |= extract_emails(sub_text)
                    if include_phone:
                        all_phones |= extract_phones(sub_text)
                    result["subpages_checked"] += 1

    result["emails"] = sorted(all_emails)
    result["phones"] = sorted(all_phones)
    return result


async def crawl_all(
    sites: List[Dict],
    delay: float = 1.0,
    deep: bool = True,
    include_phone: bool = True,
    concurrency: int = 3,
    progress_cb=None,
) -> List[Dict]:
    """
    여러 사이트 동시 크롤링 (concurrency 제한).
    progress_cb(current, total, result): 진행상황 콜백
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    total = len(sites)

    async def _crawl_one(site: Dict, idx: int) -> Dict:
        async with semaphore:
            await asyncio.sleep(delay * (idx % concurrency))  # 스태거링
            res = await crawl_site(
                site["url"],
                delay=delay,
                deep=deep,
                include_phone=include_phone,
            )
            # 검색 결과의 title이 더 좋을 수 있으면 유지
            if not res["title"] and site.get("title"):
                res["title"] = site["title"]
            res["snippet"] = site.get("snippet", "")
            if progress_cb:
                progress_cb(idx + 1, total, res)
            return res

    tasks = [_crawl_one(site, i) for i, site in enumerate(sites)]
    results = await asyncio.gather(*tasks)
    return list(results)
