"""
ADMG Visualizer
Renders causal graphs from stress_test_results.json.

Usage:
    python visualize_admgs.py --all        # 10x10 grid PDF
    python visualize_admgs.py --id 42      # single graph viewer
"""

import argparse
import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

_HERE = Path(__file__).parent
RESULTS_PATH = _HERE / "stress_test_results.json"
PDF_PATH = _HERE / "admg_grid.pdf"

NODE_DEFAULT = "#d0d0d0"
NODE_TREATMENT = "#4caf50"
NODE_OUTCOME = "#ff9800"
EDGE_DIRECTED = "black"
EDGE_BIDIRECTED = "#1565c0"


def load_results():
    with open(RESULTS_PATH) as f:
        data = json.load(f)
    # support both old flat list and new {"seeds": ..., "results": ...} format
    return data["results"] if isinstance(data, dict) else data


def draw_graph(ax, record, layout_seed=None, functional_fontsize=None):
    vertices = record["vertices"]
    di_edges = [tuple(e) for e in record["di_edges"]]
    bi_edges = [tuple(e) for e in record["bi_edges"]]
    treatment = record["treatment"]
    outcome = record["outcome"]
    is_identified = record["is_identified"]
    gid = record["id"]

    # Build a graph just for layout
    G = nx.DiGraph()
    G.add_nodes_from(vertices)
    G.add_edges_from(di_edges)
    for u, v in bi_edges:
        if not G.has_node(u):
            G.add_node(u)
        if not G.has_node(v):
            G.add_node(v)

    seed = layout_seed if layout_seed is not None else gid
    pos = nx.spring_layout(G, seed=seed, k=1.5)

    # Node colors
    node_colors = []
    for v in vertices:
        if v == treatment and v == outcome:
            node_colors.append(NODE_TREATMENT)  # treat takes priority if same node
        elif v == treatment:
            node_colors.append(NODE_TREATMENT)
        elif v == outcome:
            node_colors.append(NODE_OUTCOME)
        else:
            node_colors.append(NODE_DEFAULT)

    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=vertices,
        node_color=node_colors,
        node_size=300,
        edgecolors="black",
        linewidths=0.8,
    )
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight="bold")

    # Draw directed edges (solid black arrows)
    if di_edges:
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edgelist=di_edges,
            edge_color=EDGE_DIRECTED,
            arrows=True,
            arrowsize=12,
            width=1.0,
            connectionstyle="arc3,rad=0.05",
            node_size=300,
        )

    # Draw bidirected edges as two curved arcs (one each direction) in blue
    for u, v in bi_edges:
        for src, dst in [(u, v), (v, u)]:
            ax.annotate(
                "",
                xy=pos[dst],
                xytext=pos[src],
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=EDGE_BIDIRECTED,
                    lw=1.2,
                    connectionstyle="arc3,rad=0.35",
                    mutation_scale=10,
                ),
                zorder=1,
            )

    # Title
    if is_identified is True:
        title_color = "#2e7d32"
        label = "Identified"
    elif is_identified is False:
        title_color = "#c62828"
        label = "Not identified"
    else:
        title_color = "#555555"
        label = "Error"

    ax.set_title(
        f"Graph {gid} — {label}",
        fontsize=7,
        color=title_color,
        fontweight="bold",
        pad=3,
    )
    ax.axis("off")

    # Functional subtitle
    if functional_fontsize is not None:
        import textwrap
        functional = record.get("functional")
        if functional:
            # ~40 chars at fontsize 5 (grid), ~70 chars at fontsize 8 (single)
            wrap_width = max(20, int(350 / functional_fontsize))
            wrapped = "\n".join(textwrap.wrap(functional.strip(), width=wrap_width))
            ax.text(
                0.5, -0.02, wrapped,
                transform=ax.transAxes,
                fontsize=functional_fontsize,
                color="#333333",
                ha="center", va="top",
                family="monospace",
            )


def render_all(results):
    matplotlib.use("pdf")
    n = len(results)
    cols = 10
    rows = (n + cols - 1) // cols  # ceil division

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.8, rows * 3.4))
    fig.subplots_adjust(hspace=0.65, wspace=0.15)

    for idx, record in enumerate(results):
        row, col = divmod(idx, cols)
        ax = axes[row][col]
        draw_graph(ax, record, functional_fontsize=5)

    # Hide any unused axes
    for idx in range(n, rows * cols):
        row, col = divmod(idx, cols)
        axes[row][col].axis("off")

    fig.suptitle("ADMG Identification Stress Test — 100 Graphs", fontsize=14, fontweight="bold", y=1.01)
    fig.savefig(PDF_PATH, bbox_inches="tight")
    print(f"Grid PDF saved to {PDF_PATH}")


def render_single(results, gid):
    matplotlib.use("TkAgg")
    record = next((r for r in results if r["id"] == gid), None)
    if record is None:
        print(f"No graph with id={gid}")
        return

    fig, ax = plt.subplots(figsize=(7, 6))
    draw_graph(ax, record, layout_seed=42, functional_fontsize=8)

    # Legend
    legend_handles = [
        mpatches.Patch(color=NODE_TREATMENT, label=f"Treatment ({record['treatment']})"),
        mpatches.Patch(color=NODE_OUTCOME, label=f"Outcome ({record['outcome']})"),
        mpatches.Patch(color=NODE_DEFAULT, label="Other node"),
        mpatches.Patch(color=EDGE_DIRECTED, label="Directed edge"),
        mpatches.Patch(color=EDGE_BIDIRECTED, label="Bidirected edge"),
    ]
    ax.legend(handles=legend_handles, loc="lower left", fontsize=8, framealpha=0.8)

    fig.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Visualize ADMGs from stress test results")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Render all graphs as a 10x10 grid PDF")
    group.add_argument("--id", type=int, metavar="N", help="Render a single graph by id")
    args = parser.parse_args()

    results = load_results()

    if args.all:
        render_all(results)
    else:
        render_single(results, args.id)


if __name__ == "__main__":
    main()
