# ADMG-gen

Random ADMG generator and identification oracle. Generates Acyclic Directed Mixed Graphs (ADMGs), runs ananke's OneLineID algorithm to determine whether p(Y | do(X)) is identified, and computes the exact identifying functional when it is. Intended as a ground-truth dataset generator for causal inference benchmarking.

## Requirements

```bash
pip install git+https://github.com/noahmerhai/ananke-py3.13.git
pip install networkx numpy matplotlib
```

## Files

| File | Description |
|------|-------------|
| `admg_stress_test.py` | Generates 100 random ADMGs and runs identification on each |
| `visualize_admgs.py` | Renders graphs from results as a PDF grid or interactive viewer |
| `stress_test_results.json` | Output of the last stress test run |
| `admg_grid.pdf` | Output of the last visualizer run |

## Usage

### Stress test

Run 100 trials with deterministic seeds 0–99 (reproducible):

```bash
python admg_stress_test.py
```

Run 100 trials with random seeds (different graphs every run):

```bash
python admg_stress_test.py --random
```

Both modes print the seeds used and save results to `stress_test_results.json`. To reproduce a random run, pass its seeds directly as the `seeds` list in the JSON back into `run_stress_test`.

**Example output:**
```
Seeds: [0, 1, 2, ..., 99]
===== ADMG Identification Stress Test =====
Total:           100
Identified:      62
Not identified:  38
Errors:          0

--- By node count ---
3 nodes: 15 identified / 22 total
...
```

### Visualizer

Render all 100 graphs as a 10×10 PDF grid:

```bash
python visualize_admgs.py --all
```

View a single graph interactively by its id:

```bash
python visualize_admgs.py --id 42
```

## Output format

`stress_test_results.json` has the following structure:

```json
{
  "seeds": [0, 1, 2, ...],
  "results": [
    {
      "id": 0,
      "vertices": ["V0", "V1", "V2"],
      "di_edges": [["V0", "V1"], ["V1", "V2"]],
      "bi_edges": [["V0", "V2"]],
      "treatment": "V0",
      "outcome": "V2",
      "n_nodes": 3,
      "n_di_edges": 2,
      "n_bi_edges": 1,
      "is_identified": true,
      "functional": "ΣV1 ΦV2V1V0(p(V);G) ",
      "error": null,
      "seed": 0
    },
    ...
  ]
}
```

`functional` is the identifying functional expression when `is_identified` is `true`, and `null` otherwise. `error` captures any exception raised by ananke.

## Graph generation

Each ADMG is generated deterministically from a seed:

1. Sample number of nodes uniformly from {3, 4, 5, 6, 7}
2. Build a random DAG using a shuffled topological order, including each forward edge with probability drawn uniformly from [0.2, 0.7]
3. Add bidirected edges between each pair of vertices with probability drawn uniformly from [0.1, 0.5]
4. Remove isolated vertices (no directed or bidirected edges)
5. Select treatment as a node with at least one descendant; select outcome as a descendant of treatment

If no valid treatment/outcome pair can be found, the generator retries with `seed + 1000`.

## Visualization legend

| Color | Meaning |
|-------|---------|
| Green node | Treatment (X) |
| Orange node | Outcome (Y) |
| Gray node | Other variable |
| Black arrow | Directed edge |
| Blue curved arrows | Bidirected edge (confounding) |

Graph titles are green when identified, red when not. Identified graphs also show their identifying functional below the graph.
