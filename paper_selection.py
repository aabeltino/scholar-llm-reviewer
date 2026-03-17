import json
import pandas as pd
import lmstudio as lms
from llm_models import auto_select_llm_model


def select_papers(input_filename: str, output_filename: str, prompt_template: str, temperature: float = 0.7) -> pd.DataFrame:
    """
    Classify academic papers from an Excel dataset using a local Large Language Model (LLM) via LM Studio.

    Each paper is evaluated against a taxonomy defined in the provided prompt template.
    The model returns a structured JSON decision for each paper (e.g., inclusion, category, and justification),
    which is then parsed, aggregated, and exported to an output Excel file.

    To ensure independence across evaluations and prevent context contamination
    (i.e., hallucination carry-over), a new chat session is initialized for each paper.

    Args:
        input_filename (str):
            Name of the Excel file located in the `data/` directory
            (e.g., 'papers_review_ontology.xlsx'). The file must include
            the following columns: 'Title', 'Authors', 'Snippet'.

        output_filename (str):
            Name of the output Excel file to be saved in the `output/` directory
            (e.g., 'review_ontology_results.xlsx').

        prompt_template (str):
            Prompt template used to query the LLM. It must include the placeholders
            {title}, {authors}, and {snippet}, which will be dynamically filled
            with each paper’s metadata.

        temperature (float, optional):
            Sampling temperature controlling the randomness of the model’s output.
            Lower values (e.g., 0.0–0.3) yield more deterministic and consistent results,
            while higher values increase variability. Default is 0.7.

    Returns:
        pd.DataFrame:
            A DataFrame containing the classification results with the following columns:
            - 'Title'    : Title of the paper
            - 'Include'  : Boolean indicating inclusion/exclusion decision
            - 'Category' : Assigned taxonomy category (or 'PARSE_ERROR' if parsing fails)
            - 'Reason'   : Model-generated explanation supporting the decision
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

        # Define the model configuration
        config = {'temperature': temperature}

        # Stream the model's response token-by-token and print it in real time.
        stream        = model.respond_stream(chat, config=config)
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
