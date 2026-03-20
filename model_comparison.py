import json
import pandas as pd
import lmstudio as lms


# =============================================================================
# FUNCTION: select_papers
# =============================================================================
def paper_selector(
        input_filename: str,
        output_filename: str,
        prompt_template: str,
        temperature: float = 0.7,
        model_name: str = "qwen/qwen3-4b-thinking-2507"
) -> pd.DataFrame:
    """
    Classify academic papers from an Excel dataset using a local LLM via LM Studio.

    Each paper is evaluated against a taxonomy defined in the provided prompt template.
    The model is asked to return a structured JSON decision (include, category, reason)
    for each paper. Parsing failures are handled gracefully to preserve all results.

    Args:
        input_filename (str): Name of the Excel file in the 'data/' directory.
                              Must contain columns: 'Title', 'Authors', 'Snippet'.
        output_filename (str): Name of the Excel file to save in the 'output/' directory.
        prompt_template (str): Prompt template with placeholders {title}, {authors}, {snippet}.
        temperature (float, optional): Sampling temperature for LLM responses. Default: 0.7.
        model_name (str, optional): Identifier of the LLM to use.

    Returns:
        pd.DataFrame: DataFrame with columns:
                      - 'Title'    : Paper title
                      - 'Include'  : Boolean inclusion decision
                      - 'Category' : Assigned taxonomy category
                      - 'Reason'   : Model explanation
    """

    # ---------------------------------------------------------------------------
    # MODEL & DATA INITIALIZATION
    # ---------------------------------------------------------------------------

    # Load the specified LLM model in LM Studio
    model = lms.llm(model_name)

    # Load input Excel file with paper metadata
    input_path = f"data/{input_filename}"
    df = pd.read_excel(input_path)
    print(f"Loaded {len(df)} papers from '{input_path}'.")

    # ---------------------------------------------------------------------------
    # PAPER CLASSIFICATION LOOP
    # ---------------------------------------------------------------------------

    results = []

    for i, row in df.iterrows():
        title, authors, snippet = row["Title"], row["Authors"], row["Snippet"]

        print("\n" + "=" * 80)
        print(f"Paper {i + 1} / {len(df)}")
        print(title)
        print("=" * 80)

        # Fill in the prompt template with the paper's metadata
        prompt = prompt_template.format(title=title, authors=authors, snippet=snippet)

        # Create a fresh chat session to prevent previous context from contaminating results
        chat = lms.Chat()
        chat.add_user_message(prompt)

        # Define model configuration
        config = {'temperature': temperature}

        # Stream the model's response token-by-token and collect the full response
        full_response = ""
        stream = model.respond_stream(chat, config=config)

        print("\nModel response:\n")
        for fragment in stream:
            text = fragment.content
            full_response += text
            print(text, end="", flush=True)
        print("\n")

        # -----------------------------------------------------------------------
        # JSON PARSING
        # -----------------------------------------------------------------------

        # Attempt to parse model output as structured JSON
        # If parsing fails, store raw response with a PARSE_ERROR sentinel
        try:
            data = json.loads(full_response)
        except json.JSONDecodeError:
            print(f"[WARNING] Could not parse JSON for paper {i + 1}. Storing raw response.")
            data = {
                "include": None,
                "category": "PARSE_ERROR",
                "reason": full_response,
            }

        # Append parsed or fallback results
        results.append({
            "Title": title,
            "Include": data.get("include"),
            "Category": data.get("category"),
            "Reason": data.get("reason"),
        })

    # ---------------------------------------------------------------------------
    # EXPORT & SUMMARY
    # ---------------------------------------------------------------------------

    output = pd.DataFrame(results)
    out_path = f"output/{output_filename}"
    output.to_excel(out_path, index=False)
    print(f"\nResults saved to '{out_path}'.")

    # Print a summary of classification outcomes
    num_true = output["Include"].sum()
    num_false = (output["Include"] == False).sum()
    num_none = output["Include"].isna().sum()

    print(f"\n--- Classification Summary ---")
    print(f"  Included   (True)  : {num_true}")
    print(f"  Excluded   (False) : {num_false}")
    print(f"  Parse errors (None): {num_none}")
    print(f"  Total              : {len(output)}")

    return output


# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

RAW_DATA_FILE = "papers_review_ontology.xlsx"
RESULTS_FILE = "review_ontology_results.xlsx"
COMPARISON_FILE = "output/comparison_test_local_models.xlsx"

# Prompt template for literature review classification
PROMPT_TEMPLATE = """
You are assisting with a literature review on raw material value chain analysis
using knowledge graphs, digital twins, centrality measures, and stress testing.

Taxonomy categories:
1. Domain Ontology & Knowledge Graph Implementation
2. Structural Analysis & Centrality Measures
3. Supply Chain Digital Twin & Simulation
4. Stress Testing & Resilience Analysis

Evaluate the following paper within this context:

Title:   {title}
Authors: {authors}
Snippet: {snippet}

Return ONLY a valid JSON object (no explanations, no markdown):

{{
  "include": true or false,
  "category": "",
  "reason": ""
}}
"""

# =============================================================================
# LOAD AVAILABLE MODELS
# =============================================================================

loaded_models = lms.list_loaded_models()

# Stop execution if no models are loaded, but keep the instance alive
if len(loaded_models) == 0:
    print('Error: no models loaded. Restart after uploading.')
    try:
        raise SystemExit
    except SystemExit:
        print("Execution stopped, but the Python session remains active.")

# =============================================================================
# STEP 1+: RUN CLASSIFICATION FOR EACH LOADED MODEL
# =============================================================================

dfs = []

for i, loaded_model in enumerate(loaded_models):
    print(f"\n=== STEP {i}: LLM classification run {i} with {loaded_model.identifier} ===\n")

    df = paper_selector(
        input_filename=RAW_DATA_FILE,
        output_filename=f"TEST{i}_{RESULTS_FILE}",
        prompt_template=PROMPT_TEMPLATE,
        model_name=loaded_model.identifier,
        temperature=0.7
    )

    dfs.append(df)

# =============================================================================
# STEP 2: COMPARE RESULTS ACROSS MODELS
# =============================================================================

print("\n=== STEP comparison: finding common included papers ===\n")

# Start with papers included in the first run, rename columns with _run1 suffix
common_rows = dfs[0][dfs[0]['Include'] == True].copy()
common_rows = common_rows.rename(
    columns={col: f"{col}_run1" for col in common_rows.columns if col != 'Title'}
)

# Merge subsequent runs, keeping only included papers and adding run-specific suffixes
for idx, df in enumerate(dfs[1:], start=2):
    df_included = df[df['Include'] == True].copy()
    df_included = df_included.rename(
        columns={col: f"{col}_run{idx}" for col in df_included.columns if col != 'Title'}
    )
    common_rows = pd.merge(common_rows, df_included, on='Title')

# Save comparison results
common_rows.to_excel(COMPARISON_FILE, index=False)
print(f"\n=== Pipeline complete. Results saved to {COMPARISON_FILE} ===\n")
