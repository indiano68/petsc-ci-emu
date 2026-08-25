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


parser = argparse.ArgumentParser(description="setup repos")
parser.add_argument("--config_file", "-c",
                    help="Configuration file to use", default="emu-config.toml")
parser.add_argument("subcommand", choices=["bpackages", "cpackages"],
                    help="series of commands that one can run")
args = parser.parse_args()

print("Acting with config file: ", args.config_file)

title, repos = parse_config(args.config_file)
subcommand = args.subcommand
destination = f"repos-{title}"
os.makedirs(f"{destination}/", exist_ok=True)
if subcommand == "bpackages":
    bpackages_subcommand(title)
