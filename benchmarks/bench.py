"""
Comprehensive Benchmarking Suite for Autocomplete & Spell Correction Engine.

Compares:
1. Prefix Search:
   (a) Sorted Array + Bisect Prefix Range
   (b) Hash Map (dict with linear prefix scan)
   (c) Trie + Top-K Min-Heap
   Evaluated at sizes 10k, 25k, 50k, 100k over 1,000 random prefix queries.
2. Memory consumption via tracemalloc.
3. Spell Correction:
   Trie-pruned backtracking search vs. Brute-force linear scan.

Generates:
- benchmarks/results.csv
- benchmarks/correction_results.csv
- benchmarks/plots/prefix_latency_comparison.png
- benchmarks/plots/memory_usage_comparison.png
- benchmarks/plots/correction_latency_comparison.png
"""

from __future__ import annotations
import bisect
import csv
import gc
import heapq
from pathlib import Path
import random
import sys
import time
import tracemalloc
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt

from src.loader import load_dictionary
from src.trie import Trie
from src.topk import top_k, Candidate
from src.corrector import correct_trie, correct_brute_force


# ==========================================
# Baseline Implementations for Comparison
# ==========================================

class BisectPrefixIndex:
    """Sorted array baseline using binary search (bisect)."""

    def __init__(self, items: list[tuple[str, int]]) -> None:
        self.sorted_items = sorted(items, key=lambda x: x[0])
        self.words = [w for w, _ in self.sorted_items]
        self.freq_map = {w: f for w, f in self.sorted_items}

    def top_k(self, prefix: str, k: int = 5) -> list[tuple[str, int]]:
        start_idx = bisect.bisect_left(self.words, prefix)
        n = len(self.words)
        heap: list[Candidate] = []

        for i in range(start_idx, n):
            word = self.words[i]
            if not word.startswith(prefix):
                break
            candidate = Candidate(word, self.freq_map[word])
            if len(heap) < k:
                heapq.heappush(heap, candidate)
            elif heap[0] < candidate:
                heapq.heappushpop(heap, candidate)

        heap.sort(key=lambda c: (-c.freq, c.word))
        return [(c.word, c.freq) for c in heap]


class DictLinearPrefixIndex:
    """Hash Map baseline using linear scan over keys."""

    def __init__(self, items: list[tuple[str, int]]) -> None:
        self.dict_items = dict(items)

    def top_k(self, prefix: str, k: int = 5) -> list[tuple[str, int]]:
        heap: list[Candidate] = []
        for word, freq in self.dict_items.items():
            if word.startswith(prefix):
                candidate = Candidate(word, freq)
                if len(heap) < k:
                    heapq.heappush(heap, candidate)
                elif heap[0] < candidate:
                    heapq.heappushpop(heap, candidate)

        heap.sort(key=lambda c: (-c.freq, c.word))
        return [(c.word, c.freq) for c in heap]


# ==========================================
# Benchmark Helpers
# ==========================================

def sample_prefixes(words: list[str], count: int = 1000, seed: int = 42) -> list[str]:
    """Generate a stable, representative list of prefix queries."""
    rng = random.Random(seed)
    chosen_words = rng.choices(words, k=count)
    prefixes = []
    for w in chosen_words:
        max_l = min(5, len(w))
        min_l = min(2, max_l)
        length = rng.randint(min_l, max(min_l, max_l))
        prefixes.append(w[:length])
    return prefixes


def measure_memory_and_build(builder_func) -> tuple[Any, float]:
    """Build a structure and measure peak memory delta in megabytes (MB)."""
    gc.collect()
    tracemalloc.reset_peak()
    tracemalloc.start()
    
    obj = builder_func()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()
    mb = peak / (1024 * 1024)
    return obj, mb


def run_prefix_benchmark(dataset_path: str = "data/words.txt") -> list[dict[str, Any]]:
    sizes = [10_000, 25_000, 50_000, 100_000]
    results: list[dict[str, Any]] = []

    print("\n" + "=" * 70)
    print("RUNNING PREFIX SEARCH BENCHMARKS (1,000 queries per configuration)")
    print("=" * 70)

    for size in sizes:
        print(f"\n--- Loading {size:,} words ---")
        _, full_dict = load_dictionary(dataset_path, max_words=size)
        items = list(full_dict.items())
        words_list = [w for w, _ in items]
        prefixes = sample_prefixes(words_list, count=1000)

        # 1. Build Bisect Index
        bisect_idx, mem_bisect = measure_memory_and_build(lambda: BisectPrefixIndex(items))
        
        # 2. Build Dict Index
        dict_idx, mem_dict = measure_memory_and_build(lambda: DictLinearPrefixIndex(items))

        # 3. Build Trie Index
        def build_trie():
            t = Trie()
            for w, f in items:
                t.insert(w, f)
            return t
        trie_idx, mem_trie = measure_memory_and_build(build_trie)

        # Benchmark Query Timing
        # Warm-up
        for p in prefixes[:20]:
            bisect_idx.top_k(p, k=5)
            dict_idx.top_k(p, k=5)
            top_k(trie_idx, p, k=5)

        # Bisect Time
        t0 = time.perf_counter()
        for p in prefixes:
            bisect_idx.top_k(p, k=5)
        t_bisect = (time.perf_counter() - t0) / len(prefixes) * 1000.0  # ms

        # Dict Linear Time
        t0 = time.perf_counter()
        for p in prefixes:
            dict_idx.top_k(p, k=5)
        t_dict = (time.perf_counter() - t0) / len(prefixes) * 1000.0  # ms

        # Trie Time
        t0 = time.perf_counter()
        for p in prefixes:
            top_k(trie_idx, p, k=5)
        t_trie = (time.perf_counter() - t0) / len(prefixes) * 1000.0  # ms

        # Verify sub-millisecond
        sub_ms_str = "YES" if t_trie < 1.0 else "NO"

        print(f"Size: {size:,}")
        print(f"  Bisect Array:  Avg Latency = {t_bisect:8.4f} ms | Memory = {mem_bisect:6.2f} MB")
        print(f"  Dict Linear:   Avg Latency = {t_dict:8.4f} ms | Memory = {mem_dict:6.2f} MB")
        print(f"  Trie (Ours):   Avg Latency = {t_trie:8.4f} ms | Memory = {mem_trie:6.2f} MB | Sub-ms: {sub_ms_str}")

        results.append({
            "size": size,
            "bisect_latency_ms": t_bisect,
            "dict_latency_ms": t_dict,
            "trie_latency_ms": t_trie,
            "bisect_memory_mb": mem_bisect,
            "dict_memory_mb": mem_dict,
            "trie_memory_mb": mem_trie,
            "trie_sub_millisecond": t_trie < 1.0,
        })

    return results


def run_correction_benchmark(
    trie: Trie,
    items: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    """Benchmark Trie-based Levenshtein pruning vs Brute Force."""
    print("\n" + "=" * 70)
    print("RUNNING SPELL CORRECTION BENCHMARK (Trie Backtracking vs Brute Force)")
    print("=" * 70)

    test_queries = [
        ("algoritm", 1),
        ("databaes", 1),
        ("pythn", 1),
        ("structur", 2),
        ("machin", 2),
        ("recursn", 2),
        ("grapg", 1),
        ("binaary", 1),
    ]

    results: list[dict[str, Any]] = []

    print(f"{'Query':<12} | {'MaxDist':<7} | {'Trie (ms)':<10} | {'Brute (ms)':<10} | {'Speedup':<8}")
    print("-" * 55)

    for query, max_d in test_queries:
        # Trie timing (average over 5 runs)
        t_trie_runs = []
        for _ in range(5):
            t0 = time.perf_counter()
            res_trie = correct_trie(trie, query, max_dist=max_d, limit=5)
            t_trie_runs.append((time.perf_counter() - t0) * 1000.0)
        trie_ms = sum(t_trie_runs) / len(t_trie_runs)

        # Brute force timing (single run is typically slower)
        t0 = time.perf_counter()
        res_brute = correct_brute_force(items, query, max_dist=max_d, limit=5)
        brute_ms = (time.perf_counter() - t0) * 1000.0

        # Verify agreement of top candidates
        top_trie_words = [w for w, _, _ in res_trie]
        top_brute_words = [w for w, _, _ in res_brute]
        assert top_trie_words == top_brute_words, f"Mismatch on {query}: {top_trie_words} vs {top_brute_words}"

        speedup = brute_ms / trie_ms if trie_ms > 0 else 1.0

        print(f"{query:<12} | {max_d:<7} | {trie_ms:10.2f} | {brute_ms:10.2f} | {speedup:7.1f}x")

        results.append({
            "query": query,
            "max_dist": max_d,
            "trie_ms": trie_ms,
            "brute_ms": brute_ms,
            "speedup": speedup,
        })

    return results


def save_csv_results(
    prefix_results: list[dict[str, Any]],
    correction_results: list[dict[str, Any]],
) -> None:
    # 1. Save prefix search results
    prefix_csv = Path("benchmarks/results.csv")
    with open(prefix_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "size",
            "bisect_latency_ms",
            "dict_latency_ms",
            "trie_latency_ms",
            "bisect_memory_mb",
            "dict_memory_mb",
            "trie_memory_mb",
            "trie_sub_millisecond",
        ])
        writer.writeheader()
        writer.writerows(prefix_results)
    print(f"\nSaved prefix search benchmark results to {prefix_csv}")

    # 2. Save correction results
    corr_csv = Path("benchmarks/correction_results.csv")
    with open(corr_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "query",
            "max_dist",
            "trie_ms",
            "brute_ms",
            "speedup",
        ])
        writer.writeheader()
        writer.writerows(correction_results)
    print(f"Saved correction benchmark results to {corr_csv}")


def generate_plots(
    prefix_results: list[dict[str, Any]],
    correction_results: list[dict[str, Any]],
) -> None:
    plots_dir = Path("benchmarks/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    sizes_k = [r["size"] // 1000 for r in prefix_results]
    trie_lat = [r["trie_latency_ms"] for r in prefix_results]
    bisect_lat = [r["bisect_latency_ms"] for r in prefix_results]
    dict_lat = [r["dict_latency_ms"] for r in prefix_results]

    trie_mem = [r["trie_memory_mb"] for r in prefix_results]
    bisect_mem = [r["bisect_memory_mb"] for r in prefix_results]
    dict_mem = [r["dict_memory_mb"] for r in prefix_results]

    # --- Plot 1: Prefix Lookup Latency (Log Scale) ---
    plt.figure(figsize=(9, 5.5))
    plt.plot(sizes_k, dict_lat, marker="s", color="#e74c3c", linewidth=2.2, label="Hash Map (Dict Linear Scan)")
    plt.plot(sizes_k, bisect_lat, marker="^", color="#f39c12", linewidth=2.2, label="Sorted Array + Bisect")
    plt.plot(sizes_k, trie_lat, marker="o", color="#27ae60", linewidth=2.5, label="Trie + Top-K (Ours)")

    plt.axhline(y=1.0, color="#7f8c8d", linestyle="--", alpha=0.8, label="Sub-Millisecond Threshold (1.0 ms)")
    plt.yscale("log")
    plt.title("Prefix Search Latency vs Dictionary Size (1,000 Queries)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Dictionary Size (in thousands of words)", fontsize=11)
    plt.ylabel("Average Query Latency (ms) [Log Scale]", fontsize=11)
    plt.xticks(sizes_k, [f"{s}k" for s in sizes_k])
    plt.grid(True, which="both", linestyle=":", alpha=0.6)
    plt.legend(frameon=True, facecolor="#f8f9fa", edgecolor="#ced4da", fontsize=10)
    plt.tight_layout()
    p1 = plots_dir / "prefix_latency_comparison.png"
    plt.savefig(p1, dpi=300)
    plt.close()
    print(f"Generated plot: {p1}")

    # --- Plot 2: Memory Usage Comparison (Bar Chart) ---
    plt.figure(figsize=(9, 5.5))
    import numpy as np
    x = np.arange(len(sizes_k))
    width = 0.26

    plt.bar(x - width, bisect_mem, width, label="Sorted Array + Bisect", color="#f39c12", alpha=0.9)
    plt.bar(x, dict_mem, width, label="Hash Map (Dict)", color="#e74c3c", alpha=0.9)
    plt.bar(x + width, trie_mem, width, label="Trie (Prefix Tree)", color="#2980b9", alpha=0.9)

    plt.title("Memory Consumption by Data Structure Across Scales", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Dictionary Size", fontsize=11)
    plt.ylabel("Peak Memory Usage (MB)", fontsize=11)
    plt.xticks(x, [f"{s}k words" for s in sizes_k])
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.legend(frameon=True, facecolor="#f8f9fa", edgecolor="#ced4da", fontsize=10)
    plt.tight_layout()
    p2 = plots_dir / "memory_usage_comparison.png"
    plt.savefig(p2, dpi=300)
    plt.close()
    print(f"Generated plot: {p2}")

    # --- Plot 3: Correction Speedup (Trie vs Brute Force) ---
    plt.figure(figsize=(10, 5.5))
    queries = [f"{r['query']} (d={r['max_dist']})" for r in correction_results]
    trie_times = [r["trie_ms"] for r in correction_results]
    brute_times = [r["brute_ms"] for r in correction_results]

    y_pos = np.arange(len(queries))
    bar_height = 0.35

    plt.barh(y_pos - bar_height / 2, brute_times, bar_height, label="Brute-Force Linear Scan", color="#e74c3c", alpha=0.85)
    plt.barh(y_pos + bar_height / 2, trie_times, bar_height, label="Trie DP Backtracking", color="#27ae60", alpha=0.9)

    plt.title("Spell Correction Latency: Trie-Pruned Search vs Brute Force (100k Words)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Execution Time (milliseconds)", fontsize=11)
    plt.yticks(y_pos, queries)
    plt.gca().invert_yaxis()  # top query at top
    plt.grid(axis="x", linestyle=":", alpha=0.6)
    plt.legend(frameon=True, facecolor="#f8f9fa", edgecolor="#ced4da", fontsize=10)
    plt.tight_layout()
    p3 = plots_dir / "correction_latency_comparison.png"
    plt.savefig(p3, dpi=300)
    plt.close()
    print(f"Generated plot: {p3}")


def main():
    prefix_results = run_prefix_benchmark("data/words.txt")

    # Load 100k dictionary for spell correction comparison
    print("\nPreparing 100k dataset for Spell Correction benchmark...")
    trie_100k, dict_100k = load_dictionary("data/words.txt", max_words=100_000)
    items_100k = list(dict_100k.items())

    correction_results = run_correction_benchmark(trie_100k, items_100k)

    save_csv_results(prefix_results, correction_results)
    generate_plots(prefix_results, correction_results)
    print("\nBenchmark Suite Completed Successfully!\n")


if __name__ == "__main__":
    main()
