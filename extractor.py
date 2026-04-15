"""이메일, 전화번호 추출 정규식 엔진"""
import re
from typing import Set

# ── 이메일 패턴 ──────────────────────────────────────────────
# RFC 5322 기반 실용적 패턴 (너무 엄격하지 않게)
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# 제외할 이메일 패턴 (이미지 파일명, 예시 등)
IGNORE_EMAIL_DOMAINS = {
    "example.com", "test.com", "domain.com", "email.com",
    "yourname.com", "company.com", "sentry.io", "sentry.wixpress.com",
    "wix.com", "cloudflare.com", "amazonaws.com",
}

IGNORE_EMAIL_USERS = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "mailer-daemon", "postmaster",
}

# ── 전화번호 패턴 (한국) ──────────────────────────────────────
KR_PHONE_PATTERN = re.compile(
    r"(?:0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})"
    r"|(?:\+82[-.\s]?\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})",
)

# ── 국제 전화번호 패턴 ────────────────────────────────────────
INTL_PHONE_PATTERN = re.compile(
    r"\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{4,9}",
)

# mailto: 링크에서 추출
MAILTO_PATTERN = re.compile(
    r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE,
)

# 난독화된 이메일 복원 패턴
OBFUSCATED_PATTERNS = [
    # "user [at] domain [dot] com"
    (re.compile(r'([a-zA-Z0-9._%+\-]+)\s*[\[\(]?at[\]\)]?\s*([a-zA-Z0-9.\-]+)\s*[\[\(]?dot[\]\)]?\s*([a-zA-Z]{2,})', re.IGNORECASE),
     lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
    # "user(at)domain.com"
    (re.compile(r'([a-zA-Z0-9._%+\-]+)\(at\)([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
     lambda m: f"{m.group(1)}@{m.group(2)}"),
]


def _clean_email(email: str) -> str | None:
    email = email.strip().lower()
    if len(email) > 254:
        return None
    local, _, domain = email.partition("@")
    if not local or not domain:
        return None
    if domain in IGNORE_EMAIL_DOMAINS:
        return None
    if local in IGNORE_EMAIL_USERS:
        return None
    # 파일 확장자처럼 생긴 것 제외 (예: something.png@...)
    if re.search(r'\.(png|jpg|gif|svg|webp|css|js|json)$', local):
        return None
    return email


def extract_emails(text: str) -> Set[str]:
    """HTML 텍스트에서 이메일 주소 추출"""
    found: Set[str] = set()

    # 1. mailto: 링크 우선 (가장 신뢰도 높음)
    for m in MAILTO_PATTERN.finditer(text):
        cleaned = _clean_email(m.group(1))
        if cleaned:
            found.add(cleaned)

    # 2. 일반 이메일 패턴
    for m in EMAIL_PATTERN.finditer(text):
        cleaned = _clean_email(m.group(0))
        if cleaned:
            found.add(cleaned)

    # 3. 난독화 이메일 복원
    for pattern, replacer in OBFUSCATED_PATTERNS:
        for m in pattern.finditer(text):
            try:
                email = replacer(m)
                cleaned = _clean_email(email)
                if cleaned:
                    found.add(cleaned)
            except Exception:
                pass

    return found


def extract_phones(text: str, include_international: bool = False) -> Set[str]:
    """전화번호 추출"""
    found: Set[str] = set()
    for m in KR_PHONE_PATTERN.finditer(text):
        phone = re.sub(r'[\s]', '-', m.group(0).strip())
        found.add(phone)
    if include_international:
        for m in INTL_PHONE_PATTERN.finditer(text):
            found.add(m.group(0).strip())
    return found
