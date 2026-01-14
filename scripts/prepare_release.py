#!/usr/bin/python3

import os
import subprocess

import click
from pathlib import Path

from git import Repo
from specfile import Specfile

def cut_first_n_lines(path: str, n: int):
    with open(path, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(path, 'w') as fout:
        fout.writelines(data[n:])

def prepend_line(file_name: str, line: str):
    """ Insert given string as a new line at the beginning of a file """
    # define name of temporary dummy file
    dummy_file = file_name + '.bak'
    # open original file in read mode and dummy file in write mode
    with open(file_name, 'r') as read_obj, open(dummy_file, 'w') as write_obj:
        # Write given line to the dummy file
        write_obj.write(line + '\n')
        # Read lines from original file one by one and append them to the dummy file
        for line in read_obj:
            write_obj.write(line)
    # remove original file
    os.remove(file_name)
    # Rename dummy file as the original file
    os.rename(dummy_file, file_name)

@click.command()
@click.argument("version")
@click.argument("specfile_path")
def prepare_release(version: str, specfile_path: str):
    repo = Repo()
    repo_name = (
        os.getenv("GITHUB_REPOSITORY", "/").split("/")[1] or Path(repo.working_dir).name
    )
    changelog_file = Path("CHANGELOG.md")
    current_changelog = changelog_file.read_text()

    cmd_tag = ['git', 'tag', '--sort=-committerdate', '--merged']
    previoustag = subprocess.Popen(cmd_tag, stdout=subprocess.PIPE).communicate()[0]
    previoustag = previoustag.decode('utf8', 'strict').split('\n')[0]

    cmd = ['git', 'log', '--format="- %s"', '...'+previoustag]
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE ).communicate()[0]
    new_entry = output.decode('utf8', 'strict')
    new_entry ='\n'.join([ item[1:-1] for item in new_entry.split('\n') ])

    changelog_file.write_text(f"# {version}\n\n{new_entry}\n{current_changelog}")
    for path in specfile_path.split(","):
        with Specfile(path, autosave=True) as specfile:
            specfile.release = "1"
            specfile.version = version
            specfile.add_changelog_entry(
                f"- New upstream release {version}",
                author="Packit Team <hello@packit.dev>",
            )
        # fix specfile release field and version macros
        with Specfile(path, autosave=True) as specfile:
            specfile.version = "%{project_version_prime}.%{project_version_major}.%{project_version_minor}.%{project_version_micro}"
        cut_first_n_lines(path, 4)
        prepend_line(path, "%global project_version_micro " + version.split(".")[3])
        prepend_line(path, "%global project_version_minor " + version.split(".")[2])
        prepend_line(path, "%global project_version_major " + version.split(".")[1])
        prepend_line(path, "%global project_version_prime " + version.split(".")[0])

        version_file = "VERSION.cmake"
        cut_first_n_lines(version_file, 4)
        prepend_line(version_file, "set(DEFAULT_PROJECT_VERSION_MICRO " + version.split(".")[3]+ ")")
        prepend_line(version_file, "set(DEFAULT_PROJECT_VERSION_MINOR " + version.split(".")[2]+ ")")
        prepend_line(version_file, "set(DEFAULT_PROJECT_VERSION_MAJOR " + version.split(".")[1]+ ")")
        prepend_line(version_file, "set(DEFAULT_PROJECT_VERSION_PRIME " + version.split(".")[0]+ ")")

if __name__ == "__main__":
    prepare_release()
