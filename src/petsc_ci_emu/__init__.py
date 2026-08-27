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


def get_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
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


def clean_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    print("Deleting:", destination)
    shutil.rmtree(Path(destination))


def checkout_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
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
        return None, [], {}
    seen.add(config_file)
    with open(config_file, "rb") as handle:
        data = tomllib.load(handle)
        arch = data.get("arch")
    args = list()
    tests = dict()
    for dep in data.get("depends_on", []):
        _, other_args, other_tests = resolve_config(
            config_file.parent / f"{dep}.toml", substitutions, seen)
        args += other_args
        tests.update(other_tests)
    for value in data.get("CONFIGURATIONS", {}).values():
        args.append(substitute(value, substitutions))
    for value in data.get("PACKAGES", {}).values():
        args.append(substitute(value, substitutions))
    for var, values in data.get("COMPILER_FLAGS", {}).items():
        args.append(f"{var}=" + " ".join(substitute(v, substitutions)
                    for v in values))
    for var, values in data.get("COMPILER_FLAGS_APPEND", {}).items():
        args.append(f"{var}+=" + " ".join(substitute(v, substitutions)
                    for v in values))
    for name, command in data.get("TESTS", {}).items():
        tests[name] = substitute(command, substitutions)
    return arch, args, tests


def petsc_arch_run(title, config_file, substitutions, action):
    petsc_destination = f"repos-{title}/PETSC"
    if not Path(petsc_destination).exists():
        raise ValueError("No PETSC repo found")
    config_files = set()
    arch, configure_args, tests = resolve_config(
        Path(config_file), substitutions, config_files)
    cwd = Path.cwd()
    os.chdir(petsc_destination)
    action(arch, configure_args, config_files, tests)
    os.chdir(cwd)


META_DIR = ".ci-emu-meta"


def confirm(question):
    return input(f"{question} [y/N] ").strip().lower() == "y"


def meta_write(arch, emu_config_file, config_file, config_files):
    meta = Path(arch) / META_DIR
    shutil.rmtree(meta, ignore_errors=True)
    (meta / "configs").mkdir(parents=True)
    shutil.copy(emu_config_file, meta / "emu-config.toml")
    root = Path(config_file)
    for source in config_files:
        target = meta / "configs" / source.relative_to(root.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    with open(meta / "meta.toml", "w") as handle:
        handle.write(f'config = "{root.name}"\n')


def meta_matches(arch, emu_config_file, configure_args, substitutions):
    meta = Path(arch) / META_DIR
    if not meta.exists():
        return True
    with open(meta / "meta.toml", "rb") as handle:
        root = tomllib.load(handle)["config"]
    with open(meta / "emu-config.toml", "rb") as stored, open(emu_config_file, "rb") as current:
        if tomllib.load(stored) != tomllib.load(current):
            return False
    _, stored_args, _ = resolve_config(meta / "configs" / root, substitutions)
    return stored_args == configure_args


def arch_configure(arch, args, config_files, emu_config_file, config_file, substitutions):
    if not meta_matches(arch, emu_config_file, args, substitutions):
        if not confirm(f"{arch} was produced by different configs, override (deletes {arch})?"):
            return
        shutil.rmtree(arch, ignore_errors=True)
    sbp.run(["./configure", f"PETSC_ARCH={arch}"] + args, check=True)
    meta_write(arch, emu_config_file, config_file, config_files)


def arch_build(arch, args, config_files, emu_config_file, substitutions):
    if not meta_matches(arch, emu_config_file, args, substitutions):
        if not confirm(f"{arch} was produced by different configs, continue anyway?"):
            return
    sbp.run(["make", f"PETSC_ARCH={arch}", "all"], check=True)


def arch_link(arch, args, config_files, emu_config_file, destination, substitutions):
    if not meta_matches(arch, emu_config_file, args, substitutions):
        if not confirm(f"{arch} was produced by different configs, continue anyway?"):
            return
    link_hpddm_headers(arch, destination)


def arch_test(arch, args, tests, test, emu_config_file, substitutions):
    if not meta_matches(arch, emu_config_file, args, substitutions):
        if not confirm(f"{arch} was produced by different configs, continue anyway?"):
            return
    if test not in tests:
        raise ValueError(f"No test {test} in {sorted(tests)}")
    sbp.run(f"PETSC_ARCH={arch} {tests[test]}", shell=True, check=True)


def build_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    petsc_arch_run(title, config_file, substitutions,
                   lambda arch, args, config_files, tests: arch_build(
                       arch, args, config_files, emu_config_file, substitutions))


def configure_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    petsc_arch_run(title, config_file, substitutions,
                   lambda arch, args, config_files, tests: arch_configure(
                       arch, args, config_files, emu_config_file, config_file, substitutions))


def check_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    print("Checking: ", config_file)


def test_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    petsc_arch_run(title, config_file, substitutions,
                   lambda arch, args, config_files, tests: arch_test(
                       arch, args, tests, test, emu_config_file, substitutions))


def link_hpddm_headers(arch, destination):
    include = Path(f"{arch}/include")
    if not list(include.glob("HPDDM_*")):
        raise ValueError(f"No HPDDM headers found in {include}")
    for header in Path(f"{destination}/HPDDM/include").iterdir():
        target = include / header.name
        target.unlink(missing_ok=True)
        target.symlink_to(header.resolve())


def link_subcommand(title, repos, emu_config_file, config_file, destination, substitutions, test):
    petsc_arch_run(title, config_file, substitutions,
                   lambda arch, args, config_files, tests: arch_link(
                       arch, args, config_files, emu_config_file, destination, substitutions))


def main():
    parser = argparse.ArgumentParser(description="setup repos")
    parser.add_argument("--config_file", "-c",
                        help="Configuration file to use", default="emu-config.toml")
    subparsers = parser.add_subparsers(dest="group", required=True)

    repos_parser = subparsers.add_parser(
        "repos", help="manage the CI repositories")
    repos_parser.add_argument("subcommand", choices=["get", "clean", "checkout"],
                              help="series of commands that one can run")

    arch_parser = subparsers.add_parser("arch", help="build PETSc arches")
    arch_parser.add_argument("subcommand", choices=["build", "configure", "check", "link", "test"],
                             help="series of commands that one can run")
    arch_parser.add_argument(
        "config", help="path to the arch's TOML config file")
    arch_parser.add_argument(
        "test", nargs="?", help="name of the test to run (only for arch test)")

    args = parser.parse_args()

    print("Acting with config file: ", args.config_file, flush=True)

    emu_config_file = Path(args.config_file).resolve()
    title, repos = parse_config(args.config_file)
    subcommand = args.subcommand
    config_file = Path(args.config).resolve() if getattr(
        args, "config", None) else None
    test = getattr(args, "test", None)
    if subcommand == "test" and test is None:
        parser.error("arch test requires a test name")
    destination = str(Path.cwd() / f"repos-{title}")
    substitutions = {"REPOSITORIES_LOCATION": destination, "TITLE": title}
    os.makedirs(f"{destination}/", exist_ok=True)

    if args.group == "repos":
        if subcommand == "get":
            get_subcommand(title, repos, emu_config_file,
                           config_file, destination, substitutions, test)
        if subcommand == "clean":
            clean_subcommand(title, repos, emu_config_file,
                             config_file, destination, substitutions, test)
        if subcommand == "checkout":
            checkout_subcommand(title, repos, emu_config_file,
                                config_file, destination, substitutions, test)
    if args.group == "arch":
        if subcommand == "build":
            build_subcommand(title, repos, emu_config_file,
                             config_file, destination, substitutions, test)
        if subcommand == "configure":
            configure_subcommand(title, repos, emu_config_file,
                                 config_file, destination, substitutions, test)
        if subcommand == "check":
            check_subcommand(title, repos, emu_config_file,
                             config_file, destination, substitutions, test)
        if subcommand == "test":
            test_subcommand(title, repos, emu_config_file,
                            config_file, destination, substitutions, test)
        if subcommand == "link":
            link_subcommand(title, repos, emu_config_file,
                            config_file, destination, substitutions, test)
