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
            self.hash = repo_config["hash"]

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


def substitute(value, substitutions):
    for key, replacement in substitutions.items():
        value = value.replace("{" + key + "}", replacement)
    return value


def get_subcommand(title, repos, config_file, destination, substitutions):
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


def clean_subcommand(title, repos, config_file, destination, substitutions):
    print("Deleting:", destination)
    shutil.rmtree(Path(destination))


def checkout_subcommand(title, repos, config_file, destination, substitutions):
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
                    print(f"hash {repo.hash} ", end="")
                print()
            cwd = Path.cwd()
            os.chdir(local_destination)
            checkout_target = repo.branch if repo.branch != None else repo.hash
            sbp.run(["git", "checkout", f"{checkout_target}"], check=True)
            os.chdir(cwd)


def resolve_config(config_file, substitutions, seen=None):
    if seen is None:
        seen = set()
    config_file = Path(config_file)
    if config_file in seen:
        return None, []
    seen.add(config_file)
    with open(config_file, "rb") as handle:
        data = tomllib.load(handle)
        arch = data.get("arch")
    args = list()
    for dep in data.get("depends_on", []):
        _, other_args = resolve_config(config_file.parent / f"{dep}.toml", substitutions, seen)
        args += other_args
    for value in data.get("CONFIGURATIONS", {}).values():
        args.append(substitute(value, substitutions))
    for value in data.get("PACKAGES", {}).values():
        args.append(substitute(value, substitutions))
    for var, values in data.get("COMPILER_FLAGS", {}).items():
        args.append(f"{var}=" + " ".join(substitute(v, substitutions) for v in values))
    for var, values in data.get("COMPILER_FLAGS_APPEND", {}).items():
        args.append(f"{var}+=" + " ".join(substitute(v, substitutions) for v in values))
    return arch, args


def build_subcommand(title, repos, config_file, destination, substitutions):
    petsc_destination = f"repos-{title}/PETSC"
    if not Path(petsc_destination).exists():
        raise ValueError("No PETSC repo found")
    config_file = Path(config_file)
    arch, configure_args = resolve_config(config_file, substitutions)
    cwd = Path.cwd()
    os.chdir(petsc_destination)
    result = sbp.run(["./configure", f"PETSC_ARCH={arch}"] + configure_args, check=True)
    result = sbp.run(["make", f"PETSC_ARCH={arch}", "all"], check=True)
    os.chdir(cwd)


def configure_subcommand(title, repos, config_file, destination, substitutions):
    print("Configuring: ", config_file)


def check_subcommand(title, repos, config_file, destination, substitutions):
    print("Checking: ", config_file)


def main():
    parser = argparse.ArgumentParser(description="setup repos")
    parser.add_argument("--config_file", "-c",
                        help="Configuration file to use", default="emu-config.toml")
    subparsers = parser.add_subparsers(dest="group", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch", help="manage the CI repositories")
    fetch_parser.add_argument("subcommand", choices=["get", "clean", "checkout"],
                              help="series of commands that one can run")

    arch_parser = subparsers.add_parser("arch", help="build PETSc arches")
    arch_parser.add_argument("subcommand", choices=["build", "configure", "check"],
                             help="series of commands that one can run")
    arch_parser.add_argument(
        "config", help="path to the arch's TOML config file")

    args = parser.parse_args()

    print("Acting with config file: ", args.config_file)

    title, repos = parse_config(args.config_file)
    subcommand = args.subcommand
    config_file = getattr(args, "config", None)
    destination = str(Path.cwd() / f"repos-{title}")
    substitutions = {"REPOSITORIES_LOCATION": destination, "TITLE": title}
    os.makedirs(f"{destination}/", exist_ok=True)

    if args.group == "fetch":
        if subcommand == "get":
            get_subcommand(title, repos, config_file, destination, substitutions)
        if subcommand == "clean":
            clean_subcommand(title, repos, config_file, destination, substitutions)
        if subcommand == "checkout":
            checkout_subcommand(title, repos, config_file, destination, substitutions)
    if args.group == "arch":
        if subcommand == "build":
            build_subcommand(title, repos, config_file, destination, substitutions)
        if subcommand == "configure":
            configure_subcommand(title, repos, config_file, destination, substitutions)
        if subcommand == "check":
            check_subcommand(title, repos, config_file, destination, substitutions)
