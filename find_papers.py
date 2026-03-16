from webscraping import open_tab
import time
import random
import pandas as pd
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_scholar(query: str, output_filename: str) -> pd.DataFrame:
    """
    Scrape Google Scholar search results for a given query and save them to Excel.

    Iterates through result pages interactively, allowing the user to handle
    CAPTCHAs manually between pages. Scraping stops either when the user types
    'quit' or when the last results page is reached.

    Args:
        query (str):           Boolean search query to submit to Google Scholar.
        output_filename (str): Name of the output Excel file (e.g. 'papers.xlsx').
                               The file is saved inside the data/ folder.

    Returns:
        pd.DataFrame: DataFrame containing the scraped papers with columns:
                      ['Title', 'Link', 'Authors', 'Snippet'].
    """

    # ---------------------------------------------------------------------------
    # DRIVER INITIALIZATION
    # ---------------------------------------------------------------------------

    driver, options = open_tab()
    wait = WebDriverWait(driver, timeout=15)

    driver.get("https://scholar.google.com/")

    # ---------------------------------------------------------------------------
    # SEARCH QUERY SETUP
    # ---------------------------------------------------------------------------

    wait.until(EC.element_to_be_clickable((By.ID, "gs_hdr_tsi"))).send_keys(query)
    wait.until(EC.element_to_be_clickable((By.ID, "gs_hdr_tsb"))).click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")))

    # ---------------------------------------------------------------------------
    # RESULTS COLLECTION
    # ---------------------------------------------------------------------------

    l_titles = []
    l_links = []
    l_authors = []
    l_snippets = []

    while True:
        # Re-fetch the count of result cards on this page to use as loop range.
        # We iterate by index rather than holding element references, so that
        # each card is re-queried fresh — avoiding StaleElementReferenceException
        # caused by Google's JS updating the DOM after initial page load.
        n_results = len(driver.find_elements(By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl"))
        print(f"Papers found on this page: {n_results}")

        for idx in range(n_results):
            try:
                # Re-fetch the specific card by index at each iteration.
                # This ensures we always hold a live reference to the element.
                result = driver.find_elements(By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")[idx]

                titles = result.find_elements(By.CSS_SELECTOR, "h3.gs_rt")
                links = result.find_elements(By.CSS_SELECTOR, "h3.gs_rt a")
                authors_info = result.find_elements(By.CSS_SELECTOR, "div.gs_a")
                snippets = result.find_elements(By.CSS_SELECTOR, "div.gs_rs")

                if len(titles) == len(links) == len(authors_info) == len(snippets) > 0:
                    title = titles[0].text
                    link = links[0].get_attribute("href")
                    authors = authors_info[0].text
                    snippet = snippets[0].text

                    print(title)
                    print(link)
                    print(authors)
                    print(snippet)

                    l_titles.append(title)
                    l_links.append(link)
                    l_authors.append(authors)
                    l_snippets.append(snippet)
                else:
                    print(f"Skipped [{idx}] — unexpected structure.")

            except StaleElementReferenceException:
                # Card was re-rendered by Google's JS between the index fetch
                # and the actual read — skip and move to the next one.
                print(f"Skipped [{idx}] — stale element, card was re-rendered mid-scrape.")
                continue

        # -----------------------------------------------------------------------
        # PAGINATION & CAPTCHA HANDLING
        # -----------------------------------------------------------------------

        waiting = random.randint(5, 15)
        print(f"Waiting {waiting}s before next interaction...")
        time.sleep(waiting)

        user_input = input("Press Enter to continue to the next page, or type 'quit' to stop: ")

        if user_input.strip().lower() == "quit":
            print("Scraping stopped by user.")
            break

        try:
            next_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[@class='gs_ico gs_ico_nav_next']/..")
                )
            )
            next_button.click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")))
        except Exception:
            print("Last page reached — no further results available.")
            break

    # ---------------------------------------------------------------------------
    # EXPORT TO EXCEL
    # ---------------------------------------------------------------------------

    df = pd.DataFrame(
        zip(l_titles, l_links, l_authors, l_snippets),
        columns=["Title", "Link", "Authors", "Snippet"]
    )

    output_path = f"data/{output_filename}"
    df.to_excel(output_path, index=False)
    print(f"Saved {len(df)} papers to '{output_path}'.")

    driver.quit()

    return df