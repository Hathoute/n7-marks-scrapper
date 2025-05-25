# n7-marks-scrapper

This project is a web scraper that retrieves marks from the MDW website of INP-Toulouse N7 and sends notifications via Discord when new marks are available.

## Prerequisites

- Python 3.6+
- Selenium
- Firefox
- Geckodriver
- Discord bot token

## Setup

1.  Install the required Python packages:

    ```bash
    pip install selenium discord.py
    ```

2.  Download the appropriate Geckodriver version for your Firefox browser and add it to your PATH.

## Configuration

Set the following environment variables:

-   `N7_USERNAME`: Your N7 username.
-   `N7_PASSWORD`: Your N7 password.
-   `BOT_SECRET`: Your Discord bot token.

## Usage

1.  Run the `entrypoint.sh` script to start the scraper:

    ```bash
    ./entrypoint.sh
    ```

    This script will:

    -   Check that all required environment variables are defined.
    -   Create a fake display for Firefox using Xvfb.
    -   Start the `main.py` script.

2.  The `main.py` script will:

    -   Log in to the MDW website.
    -   Scrape the marks from the website.
    -   Compare the new marks with the saved marks.
    -   Send notifications to subscribed users via Discord if new marks are found.
    -   Save the new marks to a file.

## Discord Bot Commands

The following commands are available via the Discord bot:

-   `ping`: Responds with "pong!".
-   `reset`: Deletes the saved marks file, forcing the scraper to send notifications for all marks on the next run.
-   `hardreset`: Restarts the scraper thread and deletes the saved marks file.
-   `last`: Returns the time of the latest successful scrap.

## Technical Details

### `entrypoint.sh`

This script is the entry point for the scraper. It sets up the environment and starts the `main.py` script.

### `main.py`

This script contains the main logic for the scraper. It uses Selenium to automate Firefox and scrape the marks from the MDW website. It also uses the Discord API to send notifications to subscribed users.

The script is structured as follows:

-   **Constants**: Defines constants such as the username, password, bot token, and save file path.
-   **Discord**: Defines the Discord client and the event handlers for receiving messages.
-   **Helpers**: Defines helper functions such as `start_firefox`, `close_firefox`, `reset`, `hard_reset`, `format_mark`, `get_clickable_from_span`, `get_first_parent`, `load_saved_marks`, `save_marks`, and `on_new_mark`.
-   **Main**: Defines the main function that is executed in a loop. The main function logs in to the MDW website, scrapes the marks, compares the new marks with the saved marks, sends notifications, and saves the new marks.

## Logging

The script uses the `logging` module to log messages to a file and to the console. The log file is located at `n7-scrap.log`.

## Threading

The script uses threading to run the main scraping logic in a separate thread. This allows the Discord bot to continue running even if the scraper is blocked.