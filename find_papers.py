from webscraping import open_tab
import time
import random
import pandas as pd
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_scholar(query: str, output_filename: str, filter_scholarly: bool = True, sort_by_date: bool = True, year_from: str = None,
    year_to: str = None) -> pd.DataFrame:
    """
    Scrape Google Scholar search results for a given query and save them to Excel.

    Iterates through result pages interactively, allowing the user to handle
    CAPTCHAs manually between pages. Scraping stops either when the user types
    'quit' or when the last results page is reached.

    Args:
        query (str):           Boolean search query to submit to Google Scholar.
        output_filename (str): Name of the output Excel file (e.g. 'papers.xlsx').
        filter_scholarly (bool): Whether to filter results to scholarly articles.
        sort_by_date (bool):     Whether to sort results by date.
        year_from (str):         Optional start year for custom date range.
        year_to (str):           Optional end year for custom date range.

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

    if filter_scholarly:
        # Click on the "Scholarly articles" link in a language-independent way
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.gs_ind > a[href*='as_rr=1']"))).click()
        # Wait for the updated search results
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")))
    if sort_by_date:
        # Click on the "Sort by date" link in a language-independent way
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.gs_ind > a[href*='scisbd=1']"))).click()
        # Wait for the results sorted by date
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")))

    # ---------------------------------------------------------------------------
    # CUSTOM YEAR FILTER
    # ---------------------------------------------------------------------------

    if year_from and year_to:
        date_filter(wait, driver, year_from, year_to)

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

def date_filter(wait, driver, start_year, end_year):
    """
    Fill the custom year range form on Google Scholar and submit it safely.

    Args:
        wait (WebDriverWait): Selenium WebDriverWait instance for waiting on elements.
        driver (WebDriver): Selenium WebDriver instance.
        start_year (str): Starting year for the custom range (e.g., "2015").
        end_year (str): Ending year for the custom range (e.g., "2023").
    """

    # Click "Intervallo personalizzato..."
    wait.until(EC.element_to_be_clickable((By.ID, "gs_res_sb_yyc"))).click()

    # Wait for the custom date range form to be present in the DOM
    wait.until(EC.presence_of_element_located((By.ID, "gs_res_sb_yyf")))
    form = driver.find_element(By.ID, "gs_res_sb_yyf")

    # ---------------------------------------------------------------------------
    # ENTER START YEAR
    # ---------------------------------------------------------------------------
    # Wait until the "from" year input is visible
    ylo_input = wait.until(EC.visibility_of(form.find_element(By.ID, "gs_as_ylo")))
    # Clear any existing value in the input
    ylo_input.clear()
    # Enter the desired starting year
    ylo_input.send_keys(start_year)

    # ---------------------------------------------------------------------------
    # ENTER END YEAR
    # ---------------------------------------------------------------------------
    # Wait until the "to" year input is visible
    yhi_input = wait.until(EC.visibility_of(form.find_element(By.NAME, "as_yhi")))
    # Clear any existing value in the input
    yhi_input.clear()
    # Enter the desired ending year
    yhi_input.send_keys(end_year)

    # ---------------------------------------------------------------------------
    # SUBMIT FORM
    # ---------------------------------------------------------------------------
    # Submit the form directly instead of clicking the button
    # This avoids issues with dynamic buttons or hidden elements
    form.submit()

    # Wait for the search results to be fully loaded after applying the year filter
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_r.gs_or.gs_scl")))
