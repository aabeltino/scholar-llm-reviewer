import undetected_chromedriver as uc

# Chrome version to use with undetected_chromedriver.
# Must match the major version of the Chrome binary installed on this machine.
# Check your version at chrome://settings/help and update this constant accordingly.
CHROME_VERSION = 146


def open_tab() -> tuple[uc.Chrome, uc.ChromeOptions]:
    """
    Launch a Chrome browser instance configured to bypass bot-detection.

    Uses undetected_chromedriver to avoid triggering Google Scholar's
    automation detection. The browser opens in a visible (non-headless) window
    so that CAPTCHAs can be solved manually when needed.

    Returns:
        tuple[uc.Chrome, uc.ChromeOptions]:
            - driver:  A ready-to-use Chrome WebDriver instance.
            - options: The ChromeOptions used to configure the driver.

    Raises:
        Exception: Propagates any error raised during driver initialization,
                   e.g. Chrome/ChromeDriver version mismatch.
    """

    options = uc.ChromeOptions()

    # Keep the browser visible so the user can interact with CAPTCHAs manually.
    options.headless = False

    # Stability and compatibility flags for running Chrome via Selenium.
    options.add_argument("--disable-gpu")               # Avoids GPU-related crashes on some systems.
    options.add_argument("--no-sandbox")                # Required in restricted environments (e.g. Docker).
    options.add_argument("--disable-dev-shm-usage")     # Prevents shared memory issues on Linux.

    # Suppress the navigator.webdriver flag that sites use to detect automation.
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Spoof a realistic browser User-Agent to reduce bot-detection likelihood.
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{CHROME_VERSION}.0.7559.110 Safari/537.36"
    )

    # Instantiate the driver, pinning the Chrome major version explicitly
    # to ensure undetected_chromedriver patches the correct binary.
    driver = uc.Chrome(options=options, version_main=CHROME_VERSION)

    return driver, options