#!/usr/bin/env python3
"""
Earnings Call Transcript Downloader
Interactive tool to download earnings calls and investor presentations for Indian companies.
"""

import sys
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from config import config
from sources import ScreenerSource, CompanyIRSource
from downloader import Downloader
from utils import EarningsCall, deduplicate_calls


console = Console()


def print_banner():
    """Print welcome banner."""
    console.print(Panel.fit(
        "[bold blue]Earnings Call Transcript Downloader[/bold blue]\n"
        "[dim]Download transcripts & presentations for Indian companies[/dim]",
        border_style="blue"
    ))
    console.print()


def get_companies() -> List[str]:
    """Get company names from user."""
    console.print("[bold]Enter company name(s)[/bold] [dim](comma-separated for multiple)[/dim]")
    raw = Prompt.ask("[cyan]Companies[/cyan]")
    companies = [c.strip() for c in raw.split(",") if c.strip()]
    return companies


def show_menu() -> str:
    """Show options menu and get choice."""
    console.print()
    console.print("[bold]Options:[/bold]")
    console.print(f"  [cyan][1][/cyan] Download transcripts only")
    console.print(f"  [cyan][2][/cyan] Download transcripts + investor presentations")
    console.print(f"  [cyan][3][/cyan] Change output directory [dim](current: {config.output_dir})[/dim]")
    console.print(f"  [cyan][4][/cyan] Change transcript count [dim](current: {config.transcripts_per_company})[/dim]")
    console.print(f"  [cyan][5][/cyan] Exit")
    console.print()

    return Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5"], default="1")


def change_output_dir():
    """Change the output directory."""
    new_dir = Prompt.ask(
        "[cyan]New output directory[/cyan]",
        default=config.output_dir
    )
    config.output_dir = new_dir
    console.print(f"[green]Output directory set to: {config.output_dir}[/green]")


def change_transcript_count():
    """Change number of transcripts to download."""
    count = Prompt.ask(
        "[cyan]Number of transcripts per company[/cyan]",
        default=str(config.transcripts_per_company)
    )
    try:
        config.transcripts_per_company = int(count)
        console.print(f"[green]Will download {config.transcripts_per_company} transcripts per company[/green]")
    except ValueError:
        console.print("[red]Invalid number, keeping current setting[/red]")


def search_and_download(companies: List[str], include_presentations: bool):
    """Search for companies and download their earnings calls."""
    ir_source = CompanyIRSource()
    screener_source = ScreenerSource()
    downloader = Downloader()
    all_calls: List[EarningsCall] = []

    console.print()
    console.print("[bold]Searching for earnings calls...[/bold]")

    for company in companies:
        console.print(f"\n[cyan]Searching:[/cyan] {company}")

        # Try company IR website first
        calls = ir_source.get_earnings_calls(
            company,
            count=config.transcripts_per_company,
            include_presentations=include_presentations
        )

        # Fall back to Screener.in if not enough documents found
        if len(calls) < config.transcripts_per_company:
            if calls:
                console.print(f"  [dim]Found {len(calls)} on IR site, checking Screener.in for more...[/dim]")
            screener_calls = screener_source.get_earnings_calls(
                company,
                count=config.transcripts_per_company,
                include_presentations=include_presentations
            )
            calls.extend(screener_calls)

        if calls:
            console.print(f"  [green]Found {len(calls)} document(s)[/green]")
            all_calls.extend(calls)
        else:
            console.print(f"  [yellow]No documents found[/yellow]")

    if not all_calls:
        console.print("\n[red]No documents found for any company.[/red]")
        return

    # Deduplicate
    all_calls = deduplicate_calls(all_calls)

    # Show what will be downloaded
    console.print()
    table = Table(title="Documents to Download")
    table.add_column("Company", style="cyan")
    table.add_column("Quarter")
    table.add_column("Type")
    table.add_column("Source", style="dim")

    for call in all_calls:
        table.add_row(
            call.company[:30],
            f"{call.quarter} {call.year}",
            call.doc_type,
            call.source
        )

    console.print(table)

    # Confirm download
    if not Confirm.ask(f"\n[cyan]Download {len(all_calls)} file(s)?[/cyan]", default=True):
        console.print("[yellow]Download cancelled.[/yellow]")
        return

    # Download
    console.print()
    results = []
    for company in set(c.company for c in all_calls):
        company_calls = [c for c in all_calls if c.company == company]
        output_dir = config.get_output_path(company)
        console.print(f"[bold]Downloading to: {output_dir}[/bold]")
        results.extend(downloader.download_sync(company_calls, output_dir))

    # Summary
    success_count = sum(1 for _, success, _ in results if success)
    console.print()
    console.print(Panel(
        f"[green]Downloaded: {success_count}[/green] | "
        f"[red]Failed: {len(results) - success_count}[/red]",
        title="Summary",
        border_style="green" if success_count == len(results) else "yellow"
    ))


def main():
    """Main interactive loop."""
    print_banner()

    while True:
        companies = get_companies()
        if not companies:
            console.print("[yellow]No companies entered. Please try again.[/yellow]")
            continue

        choice = show_menu()

        if choice == "1":
            search_and_download(companies, include_presentations=False)
        elif choice == "2":
            search_and_download(companies, include_presentations=True)
        elif choice == "3":
            change_output_dir()
            continue
        elif choice == "4":
            change_transcript_count()
            continue
        elif choice == "5":
            console.print("[dim]Goodbye![/dim]")
            sys.exit(0)

        # Ask if user wants to continue
        console.print()
        if not Confirm.ask("[cyan]Download more?[/cyan]", default=True):
            console.print("[dim]Goodbye![/dim]")
            break


if __name__ == "__main__":
    main()
