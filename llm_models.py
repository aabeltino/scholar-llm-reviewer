import lmstudio as lms


def auto_select_llm_model() -> lms.LLM:
    """
    Automatically select and return an available LLM from LMStudio.

    Queries the list of currently loaded models and returns the first one found.

    Returns:
        lms.LLM: A ready-to-use LLM instance.

    Raises:
        RuntimeError: If no models are currently loaded in LMStudio.
    """

    # Retrieve all models currently loaded in the LMStudio local server.
    loaded_models = lms.list_loaded_models()

    if not loaded_models:
        raise RuntimeError(
            "No models are currently loaded in LMStudio. "
            "Please load a model before running this script."
        )

    selected = loaded_models[0].identifier
    print(f"[LMStudio] Using loaded model: '{selected}'")
    return lms.llm(selected)