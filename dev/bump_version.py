# coding=utf-8
"""
Created on 15.5.2023
Updated on 7.7.2023

Potku is a graphical user interface for analyzation and
visualization of measurement data collected from a ToF-ERD
telescope. For physics calculations Potku uses external
analyzation components.
Copyright (C) 2023 Sami Voutilainen

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (file named 'LICENCE').
"""

__author__ = "Sami Voutilainen"
__version__ = "2.0"

import subprocess
import os
from datetime import date
import re
import argparse

"""
Script for updating the version number stored in version.txt and pushing the
update to remote/master via a pull request. version.txt must be in the root of
the repository. Git and GitHub CLI must be installed to run the script. Script
saves the new version number on the first row of version.txt and the date of the
new version on the second row.
"""

dev_directory = os.path.dirname(os.path.realpath(__file__))
root_directory = os.path.dirname(dev_directory)
version_file_path = os.path.join(root_directory, "version.txt")
version_pattern = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.' \
                  r'(?P<patch>0|[1-9]\d*)' \
                  r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)' \
                  r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))' \
                  r'?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+' \
                  r'(?:\.[0-9a-zA-Z-]+)*))?$'


parser = argparse.ArgumentParser(description='Bump Potku version')
parser.add_argument('--remote', help='Set git remote (usually origin)', default="origin")
args = parser.parse_args()
remote = args.remote

def get_github_status():
    """
    Get status of the repo in which the script is run in. Return true if there
    are no uncommitted changes and false if there are changes. Additionally,
    print the uncommitted changes.
    Returns: bool
    """
    git_status_process = subprocess.run(["git", "status", "-s"],
                                        capture_output=True,
                                        cwd=root_directory,
                                        check=True)

    ret = git_status_process.stdout.decode('UTF-8')
    if not ret:
        print("Working tree is clean, ready to proceed.")
        git_checkout_master = subprocess.run(["git", "checkout", "master"],
                                             capture_output=True,
                                             cwd=root_directory,
                                             check=True)

        print("Checked out master.")

        git_pull_remote_master = subprocess.run(["git", "pull", remote, "master"],
                                                capture_output=True,
                                                cwd=root_directory,
                                                check=True)
        return True

    print("There are uncommitted differences, cannot proceed.")

    print(ret)

    return False


def git_bump_and_pr(version_string: str):
    """
    Creates a new branch for bumping the version number, commits the updated
    version number.txt, pushes to the new branch, creates a pull request and
    checks out back into master and deletes the newly created local branch for
    the version bump.
    Args:
        version_string: string representation of the new version number.
    """
    git_create_branch = subprocess.run(["git", "checkout", "-b",
                                        f"bump_version_{version_string}"],
                                       capture_output=True,
                                       cwd=root_directory,
                                       check=True)
    ret_branch = git_create_branch.stdout.decode('UTF-8')
    print(ret_branch)

    subprocess.run(["git", "add", version_file_path], check=True)

    git_commit_process = subprocess.run(["git", "commit", "-m",
                                         f"Bump version to {version_string}"],
                                        capture_output=True,
                                        cwd=root_directory, check=True)
    ret_commit = git_commit_process.stdout.decode('UTF-8')
    print(ret_commit)

    print(f'Pushing a new branch: bump_version_{version_string}')

    subprocess.run(["git", "push", remote,
                    f"bump_version_{version_string}"], cwd=root_directory, check=True)

    print('Created a new pull request, URL follows')

    subprocess.run(["gh", "pr", "create", "-B", "master", "-t",
                    f"Version bump to {version_string}", "-b",
                    "Version bump via script."], cwd=root_directory, check=True)

    print('Please edit the pull request to provide more information about the changes in this version.')

    subprocess.run(["git", "checkout", "master"], cwd=root_directory, check=True)

    subprocess.run(["git", "branch", "-D", f'bump_version_{version_string}'], 
                    cwd=root_directory, check=True)

    subprocess.run(["git", "pull", remote, "master"], check=True)
    print('You are now back on master branch, consider doing a git pull after GitHub actions bot finishes.')
    
    return


def version_not_taken(version_text):
    """
    Checks if the inputted version number is already taken or not
    Args:
        version_text: user inputted version string
    Returns: bool whether the version number is already taken or not
    """
    git_tags = subprocess.run(["git", "tag"], capture_output=True,
                              cwd=root_directory, check=True)
    tag_list = git_tags.stdout.decode('UTF-8').splitlines()
    if version_text in tag_list:
        print("Version number is already taken on GitHub!")
        return False
    return True


def get_version():
    """
    Get version number from the version.txt file.
    Returns: version number as a string or None if problems are encountered.
    """
    try:
        version_file = open(version_file_path, "r")
        version_contents = version_file.read().splitlines()
        version_number_str = version_contents[0]
        version_file.close()
    except FileNotFoundError:
        print('version.txt not found!')
        return None
    except IndexError:
        print('Unexpected things in version.txt!')
        return None

    return version_number_str


def save_version(version_string: str):
    """
    Save version number and date of version to the version.txt file
    Args:
        version_string: the version number to be saved as a string.
    """
    version_date = date.today().isoformat()
    version_file = open(version_file_path, "w")
    version_file.writelines([f'{version_string}\n', version_date])
    version_file.close()

    return


def verify_version(version_number_str: str):
    """
    Verify version number from a string.
    Args:
        version_number_str: string representing the semantic version number.

    Returns: Bool whether the version number is valid or not.
    """
    match = re.match(version_pattern, version_number_str)

    if match:

        return True

    return False


def input_new_version():
    """
    Updates the version number based on user input. User can either input a
    hardcoded semantic level to bump the respective level, or their own version
    number. User can also cancel by entering 'c'.

    Returns: a user-entered version string that has passed the regex check.
    """
    new_version_number = None
    input_accepted = False

    while not input_accepted:

        print('Enter a new version number or c to cancel.')
        text_input = input().casefold()
        if text_input == 'c':
            input_accepted = True

        if verify_version(text_input) and version_not_taken(text_input):
            new_version_number = text_input
            input_accepted = True

    return new_version_number


def check_gh_cli_installation():
    """
    Checks if GitHub CLI is installed by running gh version command.
    Returns: bool, True if installation is found, false if not found.
    """
    gh_version_process = subprocess.run(["gh", "version"],
                                        capture_output=True,
                                        cwd=root_directory,
                                        check=True)
    ret_gh = gh_version_process.stdout.decode('UTF-8')
    if "gh version" in ret_gh:
        return True
    return False


def check_git_installation():
    """
    Checks if Git is installed by running git version command.
    Returns: bool, True if installation is found, false if not found.
    """
    git_version_process = subprocess.run(["git", "version"],
                                         capture_output=True,
                                         cwd=root_directory,
                                         check=True)
    ret_git = git_version_process.stdout.decode('UTF-8')
    if "git version" in ret_git:
        return True
    return False


def version_bump_process():
    """
    Function that manages the whole process of updating the version number.
    Returns:
    """
    print('This script is intended only for Potku devs to initiate an automatic'
          ' version number bump.')

    if check_git_installation() is False:
        print("Git not installed. Install Git first. Aborting process.")
        return
    if check_gh_cli_installation() is False:
        print("GitHub CLI not installed. Install GitHub CLI first. "
              "Aborting process.")

    working_tree_is_clean = get_github_status()
    if not working_tree_is_clean:
        return

    current_version_string = get_version()
    print(f'Current version is {current_version_string}')
    if current_version_string is None:
        print('Aborting process.')
        return

    new_version_string = input_new_version()

    if new_version_string is None:
        print('Version bump process cancelled.')
        return

    print(f'New version number would be {new_version_string}')

    input_accepted = False
    while not input_accepted:
        print('Continue with this number y/n? Last chance to cancel.')
        continue_response = input().casefold()
        if continue_response == 'y':
            save_version(new_version_string)
            git_bump_and_pr(new_version_string)
            input_accepted = True
        elif continue_response == 'n':
            print('Version bump cancelled.')
            input_accepted = True
        else:
            print('Please enter y to proceed or n to cancel.')

    return


if __name__ == "__main__":
    version_bump_process()
