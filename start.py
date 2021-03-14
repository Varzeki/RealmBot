import subprocess
import git

repo = git.Repo("./")

while True:
    print("\nRUNNING GIT PULL")
    current = repo.head.commit
    repo.remotes.origin.pull()
    if current != repo.head.commit:
        print("Update Pulled")
    print("RUNNING BOT")
    subprocess.call(["python3", "Realm.py"])
