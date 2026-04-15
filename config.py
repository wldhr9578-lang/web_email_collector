"""설정 관리 모듈"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

CONFIG_DIR = Path.home() / ".web_email_collector"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / ".env"


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict:
    load_dotenv(ENV_FILE)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(data: dict) -> None:
    get_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_api_key(service: str) -> str | None:
    """환경변수 또는 config 파일에서 API 키 조회"""
    env_key = f"{service.upper()}_API_KEY"
    val = os.environ.get(env_key)
    if val:
        return val
    cfg = load_config()
    return cfg.get(env_key)


def save_api_key(service: str, key: str) -> None:
    """API 키를 .env 파일에 저장"""
    get_config_dir()
    lines = []
    env_key = f"{service.upper()}_API_KEY"
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
    filtered = [l for l in lines if not l.startswith(env_key)]
    filtered.append(f"{env_key}={key}\n")
    with open(ENV_FILE, "w") as f:
        f.writelines(filtered)
    # config.json에도 저장
    cfg = load_config()
    cfg[env_key] = key
    save_config(cfg)


def get_downloads_dir() -> Path:
    """플랫폼별 다운로드 폴더 반환"""
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "다운로드",
        home / "Desktop",
        home,
    ]
    for p in candidates:
        if p.exists():
            return p
    return home
