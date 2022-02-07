import asyncio
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

# Constants
my_username = os.environ['N7_USERNAME']
my_password = os.environ['N7_PASSWORD']
bot_secret = os.environ['BOT_SECRET']

save_file = Path("./marks.txt")
save_file.parent.mkdir(parents=True, exist_ok=True)

driver = webdriver.Firefox()

discord_client = discord.Client()
subscribed_user_ids = [285411445028421632]
message_queue = []

event = threading.Event()
stop_thread = False


# Discord
class Message:
    def __init__(self, user_id, msg):
        self.user_id = user_id
        self.message = msg


@discord_client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(discord_client))


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    print("Received message from {1}: {0}".format(message.content, message.author.name))

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

    await message.author.send("Unknown command.")


async def notify_users():
    await discord_client.wait_until_ready()
    while True:
        for m in message_queue:
            try:
                user = await discord_client.fetch_user(m.user_id)
                await user.send(m.message)
            except Exception:
                pass

            message_queue.remove(m)

        await asyncio.sleep(10)


# Helpers
def reset():
    if save_file.exists():
        save_file.unlink()
    event.set()


def hard_reset():
    global stop_thread, thd, driver

    if save_file.exists():
        save_file.unlink()

    stop_thread = True
    event.set()
    thd.join()

    driver.close()
    driver = webdriver.Firefox()

    thd = threading.Thread(target=main)
    thd.start()


def format_mark(t):
    return "New mark: **{0}** (**{1}**): **{2}**".format(t[1], t[0], t[2])


def get_clickable_from_span(text):
    while True:
        try:
            sp = driver.find_element(By.XPATH, "//span[text()='" + text + "']")
            break
        except Exception:
            pass

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
    driver.get("https://mdw.inp-toulouse.fr/mdw3/#!notesView")
    if driver.current_url == "https://mdw.inp-toulouse.fr/mdw3/#!notesView":
        # Already logged in, refresh if table is still open
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


def load_website_marks():
    # Click on 2nd year marks
    get_clickable_from_span("N7I52/181").click()
    time.sleep(1)

    # Close Help popup
    get_clickable_from_span("Fermer").click()
    time.sleep(1)

    # Get table text
    elt = driver.find_element(By.XPATH, "//b[text()='N7I52']")
    tbl = get_first_parent(elt, "tbody")
    tbody_text = tbl.text

    # Tuple in form: (CODE, NAME, MARK, _)
    return re.findall(r"(N[A-Z0-9]+)\n +([^\n]+)\n([0-9]+(\.[0-9]+)?)\n", tbody_text)


def analyse_marks(new_marks, saved_marks):
    if len(new_marks) == len(saved_marks):
        return saved_marks

    saved_dict = {t[0]: t for t in saved_marks}
    new_dict = {t[0]: t for t in new_marks if not t[0] in saved_dict}

    for key in new_dict:
        on_new_mark(new_dict[key])

    return [(t[0], t[1], t[2]) for t in new_marks]


def main():
    global stop_thread
    stop_thread = False
    while not stop_thread:
        login()
        new = load_website_marks()
        saved = load_saved_marks()

        new = analyse_marks(new, saved)
        save_marks(new)

        event.clear()
        event.wait(10*60)


thd = threading.Thread(target=main)
thd.start()

discord_client.loop.create_task(notify_users())
discord_client.run(bot_secret)
