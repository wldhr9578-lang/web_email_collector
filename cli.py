"""웹 이메일 수집기 CLI"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .config import save_api_key, get_api_key, get_downloads_dir
from .searcher import search_urls, search_urls_serpapi
from .crawler import crawl_all
from .saver import save_csv, save_txt, save_json

app = typer.Typer(
    help="🌐 키워드 기반 기업 웹사이트 이메일 수집기",
    add_completion=False,
)
console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════╗[/]
[bold cyan]║      Web Email Collector  v1.0.0         ║[/]
[bold cyan]║   키워드 → 웹사이트 → 이메일 자동 수집   ║[/]
[bold cyan]╚══════════════════════════════════════════╝[/]
"""


# ── setup 명령어 ─────────────────────────────────────────────
@app.command()
def setup():
    """API 키 초기 설정 (Google Custom Search API)"""
    rprint(BANNER)
    console.print(Panel(
        "[bold]초기 설정[/bold]\n\n"
        "Google Custom Search API가 필요합니다.\n"
        "무료 100건/일 · 유료 플랜 확장 가능\n\n"
        "[cyan]발급 방법:[/cyan]\n"
        "1. console.cloud.google.com 접속 → API 사용 설정\n"
        "   'Custom Search API' 검색 후 활성화\n"
        "2. '사용자 인증 정보' → API 키 생성\n"
        "3. cse.google.com → 새 검색엔진 생성 → CX ID 복사\n\n"
        "[dim]대안: SerpAPI (serpapi.com) 도 지원합니다.[/dim]",
        title="설정 안내",
        border_style="cyan",
    ))

    engine = Prompt.ask(
        "검색 엔진 선택",
        choices=["google", "serpapi"],
        default="google",
    )

    if engine == "google":
        api_key = Prompt.ask("Google API Key (AIza...)")
        cx_id = Prompt.ask("Custom Search Engine ID (cx)")
        save_api_key("GOOGLE", api_key)
        save_api_key("GOOGLE_CX", cx_id)
        console.print("[green]✓ Google API 설정 완료[/green]")
    else:
        api_key = Prompt.ask("SerpAPI Key")
        save_api_key("SERPAPI", api_key)
        console.print("[green]✓ SerpAPI 설정 완료[/green]")

    console.print("\n[bold green]설정이 완료되었습니다![/bold green]")
    console.print("이제 [cyan]webcollect search \"키워드\" 20[/cyan] 으로 수집을 시작하세요.\n")


# ── search 명령어 ─────────────────────────────────────────────
@app.command()
def search(
    keywords: str = typer.Argument(..., help="검색 키워드 (쉼표로 멀티 검색: \"스킨케어,화장품\")"),
    count: int = typer.Argument(20, help="수집할 사이트 수"),
    engine: str = typer.Option("google", "--engine", "-e", help="검색 엔진: google | serpapi"),
    deep: bool = typer.Option(True, "--deep/--no-deep", help="서브페이지(연락처 페이지) 탐색 여부"),
    phone: bool = typer.Option(True, "--phone/--no-phone", help="전화번호 수집 여부"),
    delay: float = typer.Option(1.0, "--delay", "-d", help="요청 간 대기시간(초)"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="저장 폴더 (기본: Downloads)"),
    json_out: bool = typer.Option(False, "--json", help="JSON 추가 저장"),
    no_save: bool = typer.Option(False, "--no-save", help="파일 저장 없이 화면만 출력"),
):
    """키워드로 웹사이트 검색 후 이메일 수집"""
    rprint(BANNER)

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    out_dir = out or get_downloads_dir()

    for keyword in keyword_list:
        console.print(f"\n[bold cyan]🔍 키워드: {keyword}[/bold cyan]")
        console.print(f"   검색엔진: {engine} | 수집목표: {count}개 사이트 | 딥크롤: {'예' if deep else '아니오'}\n")

        # ── 1단계: URL 수집 ──────────────────────────────────
        with console.status("[cyan]검색 중...[/cyan]"):
            try:
                if engine == "serpapi":
                    sites = search_urls_serpapi(keyword, count)
                else:
                    sites = search_urls(keyword, count)
            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                console.print("[yellow]webcollect setup 을 먼저 실행하세요.[/yellow]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]✗ 검색 실패: {e}[/red]")
                raise typer.Exit(1)

        if not sites:
            console.print("[yellow]검색 결과가 없습니다.[/yellow]")
            continue

        console.print(f"[green]✓ {len(sites)}개 사이트 URL 수집 완료[/green]")

        # ── 2단계: 이메일 크롤링 ─────────────────────────────
        results = []
        completed = 0

        def on_progress(current, total, res):
            nonlocal completed
            completed = current
            emails = res.get("emails", [])
            status = f"[green]이메일 {len(emails)}개[/green]" if emails else "[dim]이메일 없음[/dim]"
            err = f"[red] ({res['error']})[/red]" if res.get("error") else ""
            console.print(f"  [{current:2d}/{total}] {res.get('title', res['url'])[:40]}  {status}{err}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"크롤링 중... (delay={delay}s)", total=len(sites))

            async def run():
                nonlocal results

                def cb(cur, tot, res):
                    on_progress(cur, tot, res)
                    progress.update(task, completed=cur)

                results = await crawl_all(
                    sites,
                    delay=delay,
                    deep=deep,
                    include_phone=phone,
                    concurrency=3,
                    progress_cb=cb,
                )

            asyncio.run(run())

        # ── 3단계: 결과 출력 ─────────────────────────────────
        _print_summary(results, keyword)

        # ── 4단계: 저장 ──────────────────────────────────────
        if not no_save:
            csv_path = save_csv(results, keyword, out_dir)
            txt_path = save_txt(results, keyword, out_dir)
            console.print(f"\n[bold green]✓ 저장 완료[/bold green]")
            console.print(f"   CSV : {csv_path}")
            console.print(f"   TXT : {txt_path}")
            if json_out:
                json_path = save_json(results, keyword, out_dir)
                console.print(f"   JSON: {json_path}")

    console.print("\n[bold]수집이 완료되었습니다. 😊[/bold]\n")


def _print_summary(results: list, keyword: str):
    """수집 결과 요약 테이블 출력"""
    total_sites = len(results)
    sites_with_email = sum(1 for r in results if r.get("emails"))
    total_emails = sum(len(r.get("emails", [])) for r in results)

    # 요약 패널
    console.print(Panel(
        f"[green]사이트[/green] {total_sites}개  |  "
        f"[green]이메일 있는 사이트[/green] {sites_with_email}개  |  "
        f"[green]총 이메일[/green] {total_emails}개",
        title=f"수집 결과 요약 — {keyword}",
        border_style="green",
    ))

    # 이메일이 있는 결과만 테이블로 표시
    found = [r for r in results if r.get("emails")]
    if not found:
        console.print("[yellow]이메일을 찾지 못했습니다.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("사이트명", max_width=30)
    table.add_column("이메일", max_width=40)
    table.add_column("전화", max_width=20)

    for i, r in enumerate(found[:30], 1):
        emails = "\n".join(r["emails"][:3])
        phones = "\n".join(r.get("phones", [])[:2])
        table.add_row(str(i), r.get("title", "")[:30], emails, phones)

    console.print(table)
    if len(found) > 30:
        console.print(f"[dim]... 외 {len(found)-30}개 (저장 파일에서 확인)[/dim]")


# ── doctor 명령어 ─────────────────────────────────────────────
@app.command()
def doctor():
    """환경 점검 - API 키 설정 상태 확인"""
    rprint(BANNER)
    console.print("[bold]환경 점검[/bold]\n")

    checks = [
        ("Google API Key", get_api_key("GOOGLE")),
        ("Google CX ID", get_api_key("GOOGLE_CX")),
        ("SerpAPI Key", get_api_key("SERPAPI")),
    ]

    all_ok = False
    for name, val in checks:
        if val:
            masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "****"
            console.print(f"  [green]✓[/green] {name}: {masked}")
            all_ok = True
        else:
            console.print(f"  [dim]–[/dim] {name}: 미설정")

    console.print()
    if all_ok:
        console.print("[green]✓ 수집기 사용 준비가 완료되었습니다.[/green]")
    else:
        console.print("[yellow]! API 키가 설정되지 않았습니다. webcollect setup 을 실행하세요.[/yellow]")

    console.print(f"\n저장 폴더: {get_downloads_dir()}\n")


# ── url 명령어 (단일 URL 직접 크롤링) ─────────────────────────
@app.command()
def crawl(
    url: str = typer.Argument(..., help="직접 크롤링할 URL"),
    deep: bool = typer.Option(True, "--deep/--no-deep"),
):
    """단일 URL에서 직접 이메일 수집 (검색 없이)"""
    from .crawler import crawl_site

    console.print(f"\n[cyan]크롤링: {url}[/cyan]\n")

    async def run():
        return await crawl_site(url, deep=deep)

    result = asyncio.run(run())

    if result.get("error"):
        console.print(f"[red]✗ {result['error']}[/red]")
    else:
        console.print(f"사이트명: {result.get('title', '')}")
        console.print(f"URL    : {result['url']}")
        emails = result.get("emails", [])
        if emails:
            for e in emails:
                console.print(f"이메일 : [green]{e}[/green]")
        else:
            console.print("[yellow]이메일을 찾지 못했습니다.[/yellow]")
        phones = result.get("phones", [])
        for p in phones:
            console.print(f"전화   : {p}")
    console.print()


if __name__ == "__main__":
    app()
