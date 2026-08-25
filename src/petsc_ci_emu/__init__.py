import argparse
import tomllib
from typing import Dict
import os
import shutil
from pathlib import Path
import subprocess as sbp


class repository:
    def __init__(self, name: str, repo_config: Dict):
        self.name = name
        self.type = None
        self.localizer = None
        self.branch = None
        self.hash = None
        if "type" not in repo_config.keys():
            raise ValueError("Repository configuration must define type")
        self.type = repo_config["type"]
        if self.type == "remote":
            if "url" not in repo_config.keys():
                raise ValueError("Repository of type remote must define url")
            self.localizer = repo_config["url"]
        elif self.type == "local":
            if "path" not in repo_config.keys():
                raise ValueError("Repository of type local must define path")
            if "method" not in repo_config.keys():
                raise ValueError("Repository of type local must define method")
            self.localizer = repo_config["path"]
            self.get_method = repo_config["method"]
        if "branch" in repo_config.keys():
            self.branch = repo_config["branch"]
        if "hash" in repo_config.keys():
            self.hash = repo_config["branch"]

    def __str__(self):
        string = f"{self.name} \n"
        string += f"    type: {self.type}\n"
        if self.type == "local":
            string += f"    method: {self.get_method}\n"
        string += f"    localizer: {self.localizer}\n"
        if self.branch != None:
            string += f"    branch: {self.branch}\n"
        if self.hash != None:
            string += f"    hash: {self.hash}\n"
        return string


def parse_config(config_file: str):
    with open(config_file, 'rb') as handle:
        data = tomllib.load(handle)
        title = data["title"]
        data.pop("title")
        repos = list()
        for element in list(data):
            repos.append(repository(element, data[element]))
    return title, repos


destination = None


def get_subcommand(title, repos):
    print("Getting:")
    for repo in repos:
        local_destination = f"{destination}/{repo.name}"
        print(repo)
        if repo.type == "remote":
            sbp.run(["git", "clone", f"{repo.localizer}",
                    local_destination], check=True)
        elif repo.get_method == "link":
            Path(local_destination).symlink_to(repo.localizer)
        else:
            shutil.copytree(Path(repo.localizer), Path(local_destination))


def clean_subcommand(title, repos):
    destination = f"repos-{title}"
    print("Deleting:", destination)
    shutil.rmtree(Path(destination))


def checkout_subcommand(title, repos):
    destination = f"repos-{title}"
    for repo in repos:
        local_destination = f"{destination}/{repo.name}"
        if repo.branch != None or repo.hash != None:
            print("Checking out : ", repo.name)
            if repo.type == "local" and repo.get_method == "link":
                print(
                    f"WARNING: Checking-out delocalized repo {repo.name} to", end="")
                if repo.branch != None:
                    print(f"branch {repo.branch} ", end="")
                if repo.hash != None:
                    print(f"hash {repo.branch} ", end="")
                print()
            cwd = Path.cwd()
            os.chdir(local_destination)
            sbp.run(["git", "checkout", f"{repo.branch}"], check=True)
            os.chdir(cwd)


def bpackages_subcommand(title):
    petsc_destination = f"repos-{title}/PETSC"
    packages_config = "petsc_configs/arch-packages.conf"
    if not Path(petsc_destination).exists():
        raise ValueError("No PETSC repo found")
    if not Path().exists():
        raise ValueError("No configuration for arch-packages found")
    configure_args = list()
    with open(packages_config, "r") as flag_list:
        lines = flag_list.readlines()
        configure_args = [line.strip() for line in lines]
    cwd = Path.cwd()
    os.chdir(petsc_destination)
    result = sbp.run(["./configure"] + configure_args)
    result = sbp.run(["make", "PETSC_ARCH=arch-packages", "all"])
    os.chdir(cwd)


def main():
    parser = argparse.ArgumentParser(description="setup repos")
    parser.add_argument("--config_file", "-c",
                        help="Configuration file to use", default="emu-config.toml")
    subparsers = parser.add_subparsers(dest="group", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="manage the CI repositories")
    fetch_parser.add_argument("subcommand", choices=["get", "clean", "checkout"],
                              help="series of commands that one can run")

    build_parser = subparsers.add_parser("build", help="build PETSc arches")
    build_parser.add_argument("subcommand", choices=["bpackages", "cpackages"],
                              help="series of commands that one can run")

    args = parser.parse_args()

    print("Acting with config file: ", args.config_file)

    global destination
    title, repos = parse_config(args.config_file)
    subcommand = args.subcommand
    destination = f"repos-{title}"
    os.makedirs(f"{destination}/", exist_ok=True)

    if args.group == "fetch":
        if subcommand == "get":
            get_subcommand(title, repos)
        if subcommand == "clean":
            clean_subcommand(title, repos)
        if subcommand == "checkout":
            checkout_subcommand(title, repos)
    if args.group == "build":
        if subcommand == "bpackages":
            bpackages_subcommand(title)
