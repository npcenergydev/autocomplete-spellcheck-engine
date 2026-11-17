"""
Interactive Terminal Autocomplete & Spell Correction CLI.

Features:
- Real-time keystroke processing (on POSIX terminals)
- Microsecond timing display
- Top-5 suggestions with dynamic selection to boost frequency
- Automatic fallback 'Did you mean?' spell corrections
- Simulation mode for headless or script-driven demonstrations
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys
import time
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine import AutocompleteEngine


ANSI_CLEAR_SCREEN = "\033[2J\033[H"
ANSI_CYAN = "\033[96m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED = "\033[91m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"


def render_ui(
    query: str,
    engine: AutocompleteEngine,
    selected_msg: Optional[str] = None,
) -> None:
    print(ANSI_CLEAR_SCREEN, end="")
    print(f"{ANSI_BOLD}{ANSI_CYAN}=== DSA Autocomplete & Spell Correction Engine (CLI Demo) ==={ANSI_RESET}")
    print(f"{ANSI_DIM}Dictionary Size: {len(engine):,} words | Exit: Ctrl+C or Esc{ANSI_RESET}\n")

    t0 = time.perf_counter()
    result = engine.suggest(query, k=5)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000.0

    print(f"Search Query: {ANSI_BOLD}{ANSI_GREEN}{query}{ANSI_RESET}█")
    print(f"{ANSI_DIM}Lookup Time: {elapsed_us:8.2f} µs ({elapsed_us / 1000.0:.4f} ms){ANSI_RESET}\n")

    if selected_msg:
        print(f"{ANSI_YELLOW}★ {selected_msg}{ANSI_RESET}\n")

    if result.suggestions:
        print(f"{ANSI_BOLD}Top Suggestions:{ANSI_RESET}")
        for idx, (word, freq) in enumerate(result.suggestions, start=1):
            print(f"  {ANSI_CYAN}[{idx}]{ANSI_RESET} {word:<25} {ANSI_DIM}(freq: {freq:,}){ANSI_RESET}")
        print(f"\n{ANSI_DIM}Tip: Press number [1-{len(result.suggestions)}] to select & boost frequency.{ANSI_RESET}")
    else:
        print(f"{ANSI_DIM}No direct prefix matches found.{ANSI_RESET}")

    if result.fell_back and result.corrections:
        best_cand = result.corrections[0]
        print(f"\n{ANSI_YELLOW}{ANSI_BOLD}Did you mean:{ANSI_RESET} {ANSI_BOLD}{best_cand[0]}{ANSI_RESET} "
              f"{ANSI_DIM}(dist={best_cand[1]}, freq={best_cand[2]:,}){ANSI_RESET}")
        print(f"{ANSI_DIM}Other spell corrections:{ANSI_RESET}")
        for idx, (c_word, dist, freq) in enumerate(result.corrections[1:5], start=2):
            print(f"  - {c_word:<20} {ANSI_DIM}(dist={dist}, freq={freq:,}){ANSI_RESET}")


def run_simulation(engine: AutocompleteEngine, simulated_text: str = "data sc") -> None:
    """Simulate user typing each character sequentially with delay."""
    print(f"Running keystroke simulation for query: '{simulated_text}'\n")
    buffer = ""
    for char in simulated_text:
        buffer += char
        t0 = time.perf_counter()
        res = engine.suggest(buffer, k=5)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
        words = [w for w, _ in res.suggestions]
        correction = f" | Did you mean: {res.did_you_mean}" if res.fell_back and res.did_you_mean else ""
        print(f"Keystroke '{char}' -> Query: '{buffer:<12}' | {elapsed_us:7.1f} µs | Top: {words[:3]}{correction}")
        time.sleep(0.08)

    print("\nDemonstrating Selection & Frequency Boosting:")
    print("Pre-selection top suggestions for 'data':")
    for w, f in engine.suggest("data", k=4).suggestions:
        print(f"  {w}: {f:,}")

    target = "data science"
    print(f"\n>>> Calling engine.select('{target}', delta=500_000)...")
    new_freq = engine.select(target, delta=500_000)
    print(f"New frequency for '{target}': {new_freq:,}")

    print("\nPost-selection top suggestions for 'data':")
    for w, f in engine.suggest("data", k=4).suggestions:
        print(f"  {w}: {f:,}")


def run_interactive(engine: AutocompleteEngine) -> None:
    """Run POSIX raw terminal interactive loop for true keystroke-by-keystroke input."""
    try:
        import termios
        import tty
    except ImportError:
        # Fallback to standard input prompt if termios is unavailable
        fallback_input_loop(engine)
        return

    buffer = ""
    selected_msg: Optional[str] = None
    render_ui(buffer, engine)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            char = sys.stdin.read(1)
            selected_msg = None

            # Ctrl+C or Esc (exit)
            if char in ("\x03", "\x1b"):
                break

            # Backspace / Delete
            elif char in ("\x08", "\x7f"):
                if buffer:
                    buffer = buffer[:-1]

            # Enter
            elif char in ("\r", "\n"):
                # Select the top suggestion if available
                res = engine.suggest(buffer, k=1)
                if res.suggestions:
                    top_word = res.suggestions[0][0]
                    new_f = engine.select(top_word, delta=100)
                    selected_msg = f"Boosted '{top_word}' frequency to {new_f:,}"
                buffer = ""

            # Number keys 1-5 for immediate item selection
            elif char in ("1", "2", "3", "4", "5") and buffer:
                idx = int(char) - 1
                res = engine.suggest(buffer, k=5)
                if idx < len(res.suggestions):
                    chosen_word = res.suggestions[idx][0]
                    new_f = engine.select(chosen_word, delta=100)
                    selected_msg = f"Boosted '{chosen_word}' frequency to {new_f:,}"
                else:
                    buffer += char

            # Printable characters
            elif char.isprintable():
                buffer += char

            render_ui(buffer, engine, selected_msg=selected_msg)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print(f"\n{ANSI_RESET}Exited interactive mode.")


def fallback_input_loop(engine: AutocompleteEngine) -> None:
    print("Interactive raw mode unavailable; falling back to line-based input.")
    while True:
        try:
            query = input("\nEnter prefix query (or 'quit' to exit): ").strip()
            if query.lower() in ("quit", "exit"):
                break
            t0 = time.perf_counter()
            res = engine.suggest(query, k=5)
            elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
            print(f"Latency: {elapsed_us:.2f} µs")
            print("Suggestions:", res.suggestions)
            if res.fell_back:
                print(f"Did you mean: {res.did_you_mean}")
        except (KeyboardInterrupt, EOFError):
            break


def main():
    parser = argparse.ArgumentParser(description="Autocomplete & Spell Correction CLI Demo")
    parser.add_argument("--simulate", type=str, default=None, help="Run simulation typing given text")
    parser.add_argument("--words", type=str, default="data/words.txt", help="Path to words dataset")
    parser.add_argument("--limit", type=int, default=100_000, help="Max words to load")
    args = parser.parse_args()

    print(f"Loading dictionary from {args.words} (limit: {args.limit:,} words)...")
    t0 = time.perf_counter()
    engine = AutocompleteEngine(args.words, max_words=args.limit)
    print(f"Loaded {len(engine):,} words in {(time.perf_counter() - t0):.3f}s.\n")

    if args.simulate:
        run_simulation(engine, args.simulate)
    else:
        # If running in an interactive terminal, launch raw mode; otherwise run simulation
        if sys.stdin.isatty():
            run_interactive(engine)
        else:
            print("Standard input is not a TTY. Running default simulation on 'algoritm' and 'data st'...")
            run_simulation(engine, "data st")
            print("\nSimulation for typo 'algoritm':")
            run_simulation(engine, "algoritm")


if __name__ == "__main__":
    main()
