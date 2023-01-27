import asyncio
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
import selenium.common.exceptions as exc
import re
from pathlib import Path
import csv
import time
import discord
import threading
import os
import logging

# Set logging
root_logger = logging.getLogger("n7-scrap")
root_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(name)s:%(levelname)s:%(message)s')
fileHandler = logging.FileHandler('n7-scrap.log', 'a+', 'utf-8')
fileHandler.setFormatter(formatter)
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(formatter)
root_logger.addHandler(fileHandler)
root_logger.addHandler(stdoutHandler)


# Exceptions
class RecoverableException(Exception):
    def __init__(self):
        pass


# Constants
my_username = os.environ['N7_USERNAME']
my_password = os.environ['N7_PASSWORD']
bot_secret = os.environ['BOT_SECRET']

save_file = Path("./data/marks.txt")
save_file.parent.mkdir(parents=True, exist_ok=True)

driver = None

discord_client = discord.Client()
subscribed_user_ids = [285411445028421632]
message_queue = []

event = threading.Event()
stop_thread = False

latest_success = time.localtime()


# Discord
class Message:
    def __init__(self, user_id, msg):
        self.user_id = user_id
        self.message = msg


@discord_client.event
async def on_ready():
    root_logger.info('We have logged in as {0.user}'.format(discord_client))


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    root_logger.info("Received message from {1}: {0}".format(message.content, message.author.name))

    if message.author.id != 285411445028421632:
        await message.author.send("Unauthorized user!")
        return

    if message.content == "ping":
        await message.author.send("pong!")
        return
    elif message.content == "reset":
        await message.author.send("Reset requested by user.")
        reset()
        return
    elif message.content == "hardreset":
        await message.author.send("Hard reset requested by user.")
        hard_reset()
        return
    elif message.content == "last":
        await message.author.send("Latest successful scrap: {0}".format(time.strftime("%H:%M:%S", latest_success)))
        return

    await message.author.send("Unknown command.")


async def notify_users():
    await discord_client.wait_until_ready()
    while True:
        for m in message_queue:
            try:
                user = await discord_client.fetch_user(m.user_id)
                await user.send(m.message)
            except Exception as e:
                root_logger.exception("Notify users failed with exception {0}".format(e))
                pass

            message_queue.remove(m)

        await asyncio.sleep(10)


# Helpers
def start_firefox():
    global driver

    if driver is not None:
        driver.quit()

    driver = webdriver.Firefox()
    driver.set_window_size(1080, 3000)


def close_firefox():
    global driver

    if driver is not None:
        driver.quit()

    driver = None


def reset():
    root_logger.debug("Executing reset command")

    if save_file.exists():
        save_file.unlink()
    event.set()


def hard_reset():
    global stop_thread, thd, driver

    root_logger.debug("Executing hard reset command")

    if save_file.exists():
        save_file.unlink()

    stop_thread = True
    event.set()
    root_logger.debug("Waiting for thread to finish")
    thd.join()
    root_logger.debug("Thread finished")

    thd = threading.Thread(target=main)
    thd.start()


def format_mark(t):
    return "New mark: **{0}** (**{1}**): **{2}**".format(t[1], t[0], t[2])


def get_clickable_from_span(text):
    i = 0
    while True:
        try:
            sp = driver.find_element(By.XPATH, "//span[text()='" + text + "']")
            break
        except Exception:
            if i > 5:
                root_logger.error("Could not get clickable from span {0}".format(text))
                raise RecoverableException
            i += 1
            time.sleep(1)

    return sp.find_element(By.XPATH, "./../..")


def get_first_parent(element, xpath):
    try:
        return element.find_element(By.XPATH, "./../" + xpath)
    except exc.NoSuchElementException:
        return get_first_parent(element.find_element(By.XPATH, "./.."), xpath)


def load_saved_marks():
    if not save_file.exists():
        return []

    with save_file.open("r", encoding="utf-8") as f:
        return [tuple(values) for values in csv.reader([ln for ln in f.readlines() if ln != ""])]


def save_marks(tuple_list):
    with save_file.open('w', encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerows(tuple_list)


def on_new_mark(t):
    for uid in subscribed_user_ids:
        message_queue.append(Message(uid, format_mark(t)))


def login():
    root_logger.debug("Logging in")
    driver.get("https://mdw.inp-toulouse.fr/mdw3/#!notesView")
    if driver.current_url == "https://mdw.inp-toulouse.fr/mdw3/#!notesView":
        # Already logged in, refresh if table is still open
        root_logger.debug("Already logged in...")
        driver.refresh()
        return

    username = driver.find_element(By.XPATH, "//input[@id='username']")
    password = driver.find_element(By.XPATH, "//input[@id='password']")
    submit = driver.find_element(By.XPATH, "//input[@name='submit']")

    username.send_keys(my_username)
    password.send_keys(my_password)
    submit.click()

    driver.get("https://mdw.inp-toulouse.fr/mdw3/#!notesView")
    driver.refresh()

    root_logger.debug("Logged in, current URL is {0}".format(driver.current_url))


def load_website_marks():
    root_logger.debug("Loading website marks")

    # Click on 2nd year marks
    get_clickable_from_span("N7I53/181").click()
    time.sleep(1)

    # Close Help popup
    get_clickable_from_span("Fermer").click()
    time.sleep(1)

    # Get table text
    elt = driver.find_element(By.XPATH, "//b[text()='N7I53']")
    tbl = get_first_parent(elt, "tbody")
    tbody_text = tbl.text

    root_logger.debug("Table text: {0}".format(tbody_text.replace("\n", "\\n")))

    # Tuple in form: (CODE, NAME, MARK, _)
    return re.findall(r"(N[A-Z0-9]+)\n +([^\n]+)\n([0-9]+(\.[0-9]+)?)\n", tbody_text)


def analyse_marks(new_marks, saved_marks):
    root_logger.debug("Analysing marks: new count is {0} - saved count is {1}".format(len(new_marks), len(saved_marks)))
    if len(new_marks) == len(saved_marks):
        return saved_marks

    saved_dict = {t[0]: t for t in saved_marks}
    new_dict = {t[0]: t for t in new_marks if not t[0] in saved_dict}

    for key in new_dict:
        root_logger.info("New mark found: {0}".format(key))
        on_new_mark(new_dict[key])

    return [(t[0], t[1], t[2]) for t in new_marks]


def main():
    global stop_thread, latest_success

    root_logger.info("Executing main loop")
    stop_thread = False
    while not stop_thread:
        try:
            # Clear event if a reset was requested
            event.clear()
            # Bugfix for firefox crashing on linux
            start_firefox()

            login()
            new = load_website_marks()
            saved = load_saved_marks()

            new = analyse_marks(new, saved)
            save_marks(new)

            latest_success = time.localtime()

            # Close firefox
            close_firefox()

            event.wait(10*60)
        except RecoverableException:
            # Error when loading page maybe? try again.
            event.wait(5*60)
        except Exception as e:
            root_logger.exception("Fetch thread raised exception {0}".format(e))
            event.wait(5*60)


thd = threading.Thread(target=main)
thd.start()

discord_client.loop.create_task(notify_users())
discord_client.run(bot_secret)
