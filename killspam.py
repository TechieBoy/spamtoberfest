#! /usr/bin/env python3
from github import Github
from github.GithubException import UnknownObjectException, BadCredentialsException
from datetime import datetime
import os
from math import log
import argparse


# To avoid adding new dependencies (probably breaks in windows)
# https://stackoverflow.com/questions/287871/how-to-print-colored-text-in-python
class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def is_spam(pr):
    # Amazing machine learning(if statements) based spam detection lol
    num_files_changed_score = 0
    num_changed = 0
    ext_score = 0
    edit_score = 0
    patches = ""
    for file in pr.get_files():
        num_changed += 1
        fname = file.filename
        extension = fname.split(".")[-1]

        # Penalize md, html, env or files with no extension
        if extension in ["md", "html"] or extension == fname:
            ext_score += 10
        # Penalize few changes
        edit_score += 5 - file.changes
        patch_list = file.patch.split("\n")
        patches = ""
        for p in patch_list:
            if p[0] == "-":
                patches += f"{bcolors.FAIL}{p}{bcolors.ENDC}\n"
            elif p[0] == "+":
                patches += f"{bcolors.OKGREEN}{p}{bcolors.ENDC}\n"
            else:
                patches = patches + p + "\n"

    # Penalize low number of files changed, or too many files changed
    file_changed_score = 3 - log(num_changed)
    if file_changed_score < 0:
        # Greater than 20 files changed?!
        num_files_changed_score += 10
    else:
        num_files_changed_score += file_changed_score
    total_score = num_files_changed_score + edit_score + ext_score
    if total_score > 12:
        return patches
    return False


if __name__ == "__main__":
    personal_token = os.environ.get("GITHUB_PERSONAL_TOKEN")
    if not personal_token:
        print(
            "{bcolors.HEADER}Please set GITHUB_PERSONAL_TOKEN env variable{bcolors.ENDC}\n[https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token]."
        )
        quit()
    parser = argparse.ArgumentParser(description="Lists potentially spam prs in github")
    parser.add_argument("--repo", "-r", required=True)
    repo = parser.parse_args().repo
    g = Github(personal_token)
    try:
        repo = g.get_repo(repo)
    except UnknownObjectException:
        print(f"{bcolors.FAIL}No repo named {repo} found, quitting{bcolors.ENDC}")
        quit()
    except BadCredentialsException:
        print(f"{bcolors.FAIL}Invalid credentials, please check your token{bcolors.ENDC}")
        quit()

    prs = repo.get_pulls(state="open")
    spam_prs = []
    for pr in prs:
        if pr.created_at > datetime(year=2020, month=9, day=30):
            spam_data = is_spam(pr)
            if spam_data:
                spam_prs.append((pr, spam_data))

    if len(spam_prs) > 0:
        print(f"{bcolors.HEADER}Found a total of {len(spam_prs)} potentially spam PR's!{bcolors.ENDC}")
        print("----------------------------------------------------")
    else:
        print("No spam PR's found! If this is a incorrect, please help improve the crude spam detection!")
        quit()
    for (pr, spam_data) in spam_prs:
        print(f"\n{bcolors.WARNING}#{pr.number}:{pr.title}{bcolors.ENDC}\n{spam_data}")
        print("----------------------------------------------------")

    spam_label = None
    try:
        spam_label = repo.get_label("spam")
    except UnknownObjectException:
        # Create a spam label with poop color
        spam_label = repo.create_label(name="spam", color="7a5901", description="Spam")

    resp = input("Mark all as spam and close? [Y]es, [N]o, [O]ne at a time\n")
    if resp.strip().lower() == "y":
        print("Working...")
        for (pr, _) in spam_prs:
            pr.set_labels(spam_label)
            pr.edit(state="closed")
    elif resp.strip().lower() == "n":
        print("Aborting")
    elif resp.strip().lower() == "o":
        for (pr, spam_data) in spam_prs:
            print(f"{bcolors.WARNING}PR #{pr.number}:\n{pr.title}\n{pr.url}{bcolors.ENDC}\n{spam_data}\n")
            resp = input("Mark this as spam and close? [y/N]")
            if resp.strip().lower() == "y":
                pr.set_labels(spam_label)
                pr.edit(state="closed")
    print(f"{bcolors.OKGREEN}Done!{bcolors.ENDC}")
