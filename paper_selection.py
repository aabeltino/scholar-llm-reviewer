import json
import pandas as pd
import lmstudio as lms
from llm_models import auto_select_llm_model


def select_papers(input_filename: str, output_filename: str, prompt_template: str) -> pd.DataFrame:
    """
    Classify academic papers from an Excel file using a local LLM via LMStudio.

    Each paper is evaluated against a taxonomy defined in the prompt template.
    The LLM returns a structured JSON decision for each article, which is then
    aggregated and exported to Excel.

    A fresh chat session is created for every paper to prevent context contamination
    from previous responses (hallucination carry-over).

    Args:
        input_filename (str):   Name of the Excel file to read from the data/ folder
                                (e.g. 'papers_review_ontology.xlsx'). Must contain
                                columns: 'Title', 'Authors', 'Snippet'.
        output_filename (str):  Name of the output Excel file saved in the output/ folder
                                (e.g. 'review_ontology_results.xlsx').
        prompt_template (str):  Prompt sent to the LLM for each paper. Must contain
                                three placeholders: {title}, {authors}, {snippet}.

    Returns:
        pd.DataFrame: DataFrame with columns ['Title', 'Include', 'Category', 'Reason']
                      representing the LLM's classification for each paper.
    """

    # ---------------------------------------------------------------------------
    # MODEL & DATA INITIALIZATION
    # ---------------------------------------------------------------------------

    # Auto-select the best available LLM model configured in LMStudio.
    model = auto_select_llm_model()

    # Load raw article data produced by find_papers.py / scrape_scholar().
    input_path = f"data/{input_filename}"
    df = pd.read_excel(input_path)
    print(f"Loaded {len(df)} papers from '{input_path}'.")

    # ---------------------------------------------------------------------------
    # PAPER CLASSIFICATION LOOP
    # ---------------------------------------------------------------------------

    results = []

    for i, row in df.iterrows():
        title   = row["Title"]
        authors = row["Authors"]
        snippet = row["Snippet"]

        print("\n" + "=" * 80)
        print(f"Paper {i + 1} / {len(df)}")
        print(title)
        print("=" * 80)

        # Inject the paper's metadata into the user-provided prompt template.
        prompt = prompt_template.format(title=title, authors=authors, snippet=snippet)

        # Create a fresh chat session per paper to avoid hallucination carry-over
        # from the model's previous responses contaminating the current evaluation.
        chat = lms.Chat()
        chat.add_user_message(prompt)

        # Stream the model's response token-by-token and print it in real time.
        stream        = model.respond_stream(chat)
        full_response = ""

        print("\nModel response:\n")
        for fragment in stream:
            text           = fragment.content
            full_response += text
            print(text, end="", flush=True)
        print("\n")

        # -----------------------------------------------------------------------
        # JSON PARSING
        # -----------------------------------------------------------------------

        # Attempt to parse the model output as structured JSON.
        # On failure, store the raw response under a PARSE_ERROR sentinel so the
        # row is still preserved and can be reviewed manually.
        try:
            data = json.loads(full_response)
        except json.JSONDecodeError:
            print(f"[WARNING] Could not parse JSON for paper {i + 1}. Storing raw response.")
            data = {
                "include":  None,
                "category": "PARSE_ERROR",
                "reason":   full_response,
            }

        results.append({
            "Title":    title,
            "Include":  data["include"],
            "Category": data["category"],
            "Reason":   data["reason"],
        })

    # ---------------------------------------------------------------------------
    # EXPORT & SUMMARY
    # ---------------------------------------------------------------------------

    output   = pd.DataFrame(results)
    out_path = f"output/{output_filename}"
    output.to_excel(out_path, index=False)
    print(f"\nResults saved to '{out_path}'.")

    # Print a breakdown of classification outcomes.
    num_true  = output["Include"].sum()
    num_false = (output["Include"] == False).sum()
    num_none  = output["Include"].isna().sum()

    print(f"\n--- Classification Summary ---")
    print(f"  Included   (true)  : {num_true}")
    print(f"  Excluded   (false) : {num_false}")
    print(f"  Parse errors (None): {num_none}")
    print(f"  Total              : {len(output)}")

    return output


# ---------------------------------------------------------------------------
# EXAMPLE USAGE
# ---------------------------------------------------------------------------

if __name__ == "__main__":

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

    df = select_papers(
        input_filename="papers_review_ontology.xlsx",
        output_filename="review_ontology_results.xlsx",
        prompt_template=prompt_template,
    )