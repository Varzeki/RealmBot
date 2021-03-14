import os
import git
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
import Realm

repo = git.Repo("./")

while True:
    print("\nRUNNING GIT PULL")
    repo.remotes.origin.pull()
    print("RUNNING BOT")
    Realm.bot.run(TOKEN)
