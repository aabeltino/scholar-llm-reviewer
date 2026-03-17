from find_papers import scrape_scholar
from paper_selection import select_papers

# ---------------------------------------------------------------------------
# SEARCH QUERY
# ---------------------------------------------------------------------------

query = """(
    "knowledge graph" OR "semantic network" OR "supply chain ontology" OR "graph-based modeling"
) AND (
    "supply chain" OR "raw materials" OR "logistics network" OR "material flow"
) AND (
    "centrality" OR "betweenness centrality" OR "network analysis" OR "graph metrics" OR "network concentration"
) AND (
    "digital twin" OR "dynamic modeling" OR "real-time simulation" OR "inventory simulation"
) AND (
    "stress testing" OR "resilience analysis" OR "shock simulation" OR "disruption modeling" OR "robustness metrics"
) AND (
    "operational measure" OR "quantitative metric" OR "supply chain performance" OR "demand coverage" OR "lead time increase"
) AND (
    "empirical" OR "case study" OR "simulation study" OR "real-world data"
)"""

# ---------------------------------------------------------------------------
# PROMPT TEMPLATE
# Placeholders {title}, {authors}, {snippet} are filled in at runtime
# for each paper by select_papers().
# ---------------------------------------------------------------------------

prompt_template = """
You assist a literature review about raw material value chain analysis using
knowledge graphs, digital twins, centrality measures, and stress testing.

Taxonomy categories:
  1. Domain Ontology & Knowledge Graph Implementation
  2. Structural Analysis & Centrality Measures
  3. Supply Chain Digital Twin & Simulation
  4. Stress Testing & Resilience Analysis

Evaluate the following paper in the context of this review.

Title:   {title}
Authors: {authors}
Snippet: {snippet}

Return ONLY a JSON object — no preamble, no explanation, no markdown:

{{
  "include":  true or false,
  "category": "",
  "reason":   ""
}}
"""

# ---------------------------------------------------------------------------
# FILE NAMES
# ---------------------------------------------------------------------------

RAW_DATA_FILE = "papers_review_ontology.xlsx"
RESULTS_FILE  = "review_ontology_results.xlsx"

# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Step 1 — Scrape Google Scholar and save raw article data to data/
    print("\n=== STEP 1: Scraping Google Scholar ===\n")
    scrape_scholar(query=query, output_filename=RAW_DATA_FILE, year_to='2022', year_from='2026', sort_by_date=False)

    # Step 2 — Classify each article with the LLM and save results to output/
    print("\n=== STEP 2: Classifying papers with LLM ===\n")
    select_papers(
        input_filename=RAW_DATA_FILE,
        output_filename=RESULTS_FILE,
        prompt_template=prompt_template,
    )

    print("\n=== Pipeline complete. ===")
