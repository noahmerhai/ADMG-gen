"""
ADMG Identification Stress Test
Generates 100 random ADMGs and runs ananke's OneLineID on each.
Usage:
    python admg_stress_test.py           # deterministic seeds 0-99
    python admg_stress_test.py --random  # random seeds each run
"""

import argparse
import json
import random
from pathlib import Path
import numpy as np
import networkx as nx
from ananke.graphs import ADMG
from ananke.identification import OneLineID


def generate_random_admg(seed):
    """
    Generate a random ADMG spec deterministically from a seed.
    n_nodes is sampled uniformly from [3,4,5,6,7].
    Returns dict with vertices, di_edges, bi_edges, treatment, outcome.
    Retries with seed+1000 if no valid (treatment, outcome) pair exists.
    """
    rng = np.random.default_rng(seed)

    n_nodes = int(rng.integers(3, 8))  # [3, 7] inclusive
    vertices = [f"V{i}" for i in range(n_nodes)]

    # --- directed edges: random DAG via topological ordering ---
    order = vertices[:]
    rng.shuffle(order)

    di_edge_prob = float(rng.uniform(0.2, 0.7))
    di_edges = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            if rng.random() < di_edge_prob:
                di_edges.append((order[i], order[j]))

    # ensure at least one directed edge
    if not di_edges:
        src = order[0]
        dst = order[1]
        di_edges.append((src, dst))

    # --- bidirected edges ---
    bi_edge_prob = float(rng.uniform(0.1, 0.5))
    bi_edges = []
    for i in range(len(vertices)):
        for j in range(i + 1, len(vertices)):
            if rng.random() < bi_edge_prob:
                bi_edges.append((vertices[i], vertices[j]))

    # --- remove isolated vertices (no directed or bidirected edges) ---
    di_nodes = {v for e in di_edges for v in e}
    bi_nodes = {v for e in bi_edges for v in e}
    connected = di_nodes | bi_nodes
    vertices = [v for v in vertices if v in connected]

    if len(vertices) < 2:
        return generate_random_admg(seed + 1000)

    # --- pick treatment and outcome ---
    # Build reachability from directed edges
    g = nx.DiGraph()
    g.add_nodes_from(vertices)
    g.add_edges_from(di_edges)

    valid_treatments = [
        v for v in vertices
        if len(list(nx.descendants(g, v))) > 0
    ]

    if not valid_treatments:
        # retry with offset seed
        return generate_random_admg(seed + 1000)

    treatment = str(rng.choice(valid_treatments))
    descendants = list(nx.descendants(g, treatment))

    if not descendants:
        return generate_random_admg(seed + 1000)

    outcome = str(rng.choice(descendants))

    return {
        "vertices": vertices,
        "di_edges": di_edges,
        "bi_edges": bi_edges,
        "treatment": treatment,
        "outcome": outcome,
    }


def test_identification(i, admg_spec):
    """
    Build ananke ADMG from spec and run OneLineID.
    Returns a result dict with identification status and graph stats.
    """
    result = {
        "id": i,
        "vertices": admg_spec["vertices"],
        "di_edges": admg_spec["di_edges"],
        "bi_edges": admg_spec["bi_edges"],
        "treatment": admg_spec["treatment"],
        "outcome": admg_spec["outcome"],
        "n_nodes": len(admg_spec["vertices"]),
        "n_di_edges": len(admg_spec["di_edges"]),
        "n_bi_edges": len(admg_spec["bi_edges"]),
        "is_identified": None,
        "functional": None,
        "error": None,
    }

    try:
        graph = ADMG(
            vertices=admg_spec["vertices"],
            di_edges=admg_spec["di_edges"],
            bi_edges=admg_spec["bi_edges"],
        )
        oid = OneLineID(graph, [admg_spec["treatment"]], [admg_spec["outcome"]])
        result["is_identified"] = bool(oid.id())
        if result["is_identified"]:
            try:
                result["functional"] = oid.functional()
            except Exception as fe:
                result["functional"] = f"{type(fe).__name__}: {fe}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def run_stress_test(n_trials=100, use_random_seeds=False):
    seeds = (
        [random.randint(0, 2**31 - 1) for _ in range(n_trials)]
        if use_random_seeds
        else list(range(n_trials))
    )
    print("Seeds:", seeds)
    results = []
    for i, seed in enumerate(seeds):
        spec = generate_random_admg(seed)
        result = test_identification(i, spec)
        result["seed"] = seed
        results.append(result)
    return results, seeds


def print_summary(results):
    total = len(results)
    identified = sum(1 for r in results if r["is_identified"] is True)
    not_identified = sum(1 for r in results if r["is_identified"] is False)
    errors = sum(1 for r in results if r["error"] is not None)

    print("===== ADMG Identification Stress Test =====")
    print(f"Total:           {total}")
    print(f"Identified:      {identified}")
    print(f"Not identified:  {not_identified}")
    print(f"Errors:          {errors}")
    print()
    print("--- By node count ---")

    node_counts = sorted(set(r["n_nodes"] for r in results))
    for n in node_counts:
        group = [r for r in results if r["n_nodes"] == n]
        group_identified = sum(1 for r in group if r["is_identified"] is True)
        print(f"{n} nodes: {group_identified} identified / {len(group)} total")


def main():
    parser = argparse.ArgumentParser(description="ADMG identification stress test")
    parser.add_argument(
        "--random", action="store_true",
        help="Use random seeds instead of deterministic 0-99",
    )
    args = parser.parse_args()

    results, seeds = run_stress_test(100, use_random_seeds=args.random)
    print_summary(results)

    out_path = Path(__file__).parent / "stress_test_results.json"
    output = {"seeds": seeds, "results": results}
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
