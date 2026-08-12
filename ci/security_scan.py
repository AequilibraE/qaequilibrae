"""Runs the checks that the QGIS plugins website runs on every uploaded plugin version.

See https://plugins.qgis.org/docs/security-scanning. Over there, Bandit CRITICAL findings and
any detect-secrets hit block publication, while Flake8 and the packaged-file checks are
informational. This script mirrors that split: it fails only on the blocking checks and prints
the rest as a report.

The tree that gets scanned is the one that ends up in the ZIP, i.e. the tracked contents of the
plugin directory, so anything gitignored (``qaequilibrae/packages``) is out of scope here just
like it is out of scope over there.

Usage::

    python ci/security_scan.py              # scans HEAD, which is what gets packaged
    python ci/security_scan.py --worktree   # scans tracked files as they are on disk
"""

import argparse
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tarfile
import tempfile
from pathlib import Path

PLUGIN_DIR = "qaequilibrae"

# Bandit rules the QGIS plugins website reports as CRITICAL. Those are non-skippable there, so a
# single hit stops the plugin from being published.
# https://plugins.qgis.org/docs/security-scanning/rules
CRITICAL_BANDIT_RULES = [
    "B102",  # exec used
    "B103",  # set bad file permissions
    "B105",  # hardcoded password string
    "B106",  # hardcoded password function argument
    "B107",  # hardcoded password default
    "B111",  # execute with run_as_root=True
    "B201",  # flask debug=True
    "B202",  # tarfile unsafe members
    "B301",  # pickle usage
    "B302",  # marshal usage
    "B304",  # insecure cipher
    "B305",  # insecure cipher mode
    "B306",  # insecure mktemp
    "B307",  # eval used
    "B312",  # telnetlib usage
    "B321",  # ftp usage
    "B323",  # unverified SSL context
    "B401",  # import telnetlib
    "B402",  # import ftplib
    "B412",  # import httpoxy vulnerable module
    "B413",  # import pycrypto
    "B501",  # request with no cert validation
    "B502",  # ssl with bad version
    "B503",  # ssl with bad defaults
    "B505",  # weak cryptographic key
    "B506",  # yaml.load() used
    "B507",  # ssh no host key verification
    "B601",  # paramiko shell=True
    "B602",  # subprocess.Popen with shell=True
    "B604",  # function call with shell=True
    "B605",  # start process with a shell
    "B609",  # linux wildcard injection
    "B610",  # django extra() used
    "B611",  # django RawSQL used
    "B612",  # logging config insecure listen
    "B613",  # trojan source
    "B615",  # huggingface unsafe download
    "B701",  # jinja2 autoescape=False
]

# Flagged by the website's package inspection. Informational, but worth knowing about.
SUSPICIOUS_SUFFIXES = {".bat", ".bin", ".cmd", ".dll", ".dylib", ".exe", ".pyc", ".pyd", ".pyo", ".sh", ".so"}


def relative_to(filename, plugin_path):
    """Turns a path reported by a tool into one relative to the plugin directory."""
    try:
        return Path(filename).resolve().relative_to(plugin_path.resolve()).as_posix()
    except ValueError:
        return Path(filename).as_posix()


def run_tool(module, arguments, cwd):
    """Runs ``python -m module`` and returns the completed process, output captured."""
    command = [sys.executable, "-m", module, *arguments]
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)  # nosec B603


def known_bandit_rules():
    """The subset of CRITICAL_BANDIT_RULES the installed Bandit actually implements.

    The website and our Bandit can be on different versions, and passing an unknown id to
    ``-t`` makes Bandit bail out, so anything it does not know about is dropped.
    """
    from bandit.core import extension_loader

    manager = extension_loader.MANAGER
    implemented = set(manager.plugins_by_id) | set(manager.blacklist_by_id)
    return [rule for rule in CRITICAL_BANDIT_RULES if rule in implemented]


def repository_root():
    process = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(process.stdout.strip())


def executable_files(root, worktree):
    """Plugin-relative paths that git marks executable.

    Executability has to come from git rather than from the files on disk: it is git's mode that
    ends up in the ZIP, copying into the scan directory does not carry mode bits across, and
    Windows has no executable bit to read in the first place.
    """
    command = ["git", "ls-files", "-s", PLUGIN_DIR] if worktree else ["git", "ls-tree", "-r", "HEAD", PLUGIN_DIR]
    listing = subprocess.run(command, cwd=root, capture_output=True, text=True, check=True)  # nosec B603 B607

    executable = set()
    for line in listing.stdout.splitlines():
        if "\t" not in line:
            continue
        details, path = line.split("\t", 1)
        if details.split()[0] == "100755":
            executable.add(Path(path).relative_to(PLUGIN_DIR).as_posix())
    return executable


def export_plugin(destination, worktree):
    """Writes the packaged plugin tree into *destination* and returns its path."""
    root = repository_root()

    if worktree:
        listing = subprocess.run(  # nosec B603 B607
            ["git", "ls-files", PLUGIN_DIR], cwd=root, capture_output=True, text=True, check=True
        )
        for name in listing.stdout.splitlines():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
    else:
        archive_path = destination / "plugin.tar"
        subprocess.run(  # nosec B603 B607
            ["git", "archive", "--format=tar", f"--output={archive_path}", "HEAD", PLUGIN_DIR], cwd=root, check=True
        )
        with tarfile.open(archive_path) as archive:
            extraction = {"filter": "data"} if sys.version_info >= (3, 12) else {}
            archive.extractall(destination, **extraction)  # nosec B202
        archive_path.unlink()

    return destination / PLUGIN_DIR, executable_files(root, worktree)


def check_bandit(plugin_path):
    """Bandit, restricted to the rules that block publication. Returns the blocking findings."""
    rules = known_bandit_rules()
    skipped = sorted(set(CRITICAL_BANDIT_RULES) - set(rules))

    # --ignore-nosec on purpose: the website does not let anyone skip a CRITICAL rule, so an
    # inline suppression comment must not be able to hide one from us either.
    arguments = ["-r", str(plugin_path), "-f", "json", "-q", "--ignore-nosec", "-t", ",".join(rules)]
    process = run_tool("bandit", arguments, cwd=None)
    if process.returncode not in (0, 1):
        raise RuntimeError(f"bandit failed to run:\n{process.stderr}")

    findings = json.loads(process.stdout)["results"]

    unknown = f" ({', '.join(skipped)} unknown to this Bandit)" if skipped else ""
    print(f"Bandit, {len(rules)} blocking rules{unknown}")
    for finding in findings:
        location = f"{relative_to(finding['filename'], plugin_path)}:{finding['line_number']}"
        print(f"  CRITICAL {finding['test_id']} {finding['test_name']} at {location}")
        print(f"           {finding['issue_text']}")
    if not findings:
        print("  no blocking findings")
    return findings


def report_bandit_advisories(plugin_path):
    """Everything else Bandit has to say. Informational, matching the website's WARNING/INFO."""
    process = run_tool("bandit", ["-r", str(plugin_path), "-f", "json", "-q"], cwd=None)
    if process.returncode not in (0, 1):
        return

    findings = json.loads(process.stdout)["results"]
    print(f"\nBandit advisories (non-blocking): {len(findings)}")
    for finding in findings:
        location = f"{relative_to(finding['filename'], plugin_path)}:{finding['line_number']}"
        print(f"  {finding['issue_severity']:6} {finding['test_id']} at {location}")


def check_secrets(plugin_path):
    """detect-secrets. Any hit blocks publication. Returns the findings per file."""
    arguments = ["scan", "--all-files", "--exclude-files", r"metadata\.txt", "--exclude-files", r"\.secrets\.baseline"]
    baseline = plugin_path / ".secrets.baseline"
    if baseline.is_file():
        arguments += ["--baseline", str(baseline)]
    arguments.append(".")

    process = run_tool("detect_secrets", arguments, cwd=plugin_path)
    if process.returncode != 0:
        raise RuntimeError(f"detect-secrets failed to run:\n{process.stderr}")

    findings = json.loads(process.stdout).get("results", {})

    print("\ndetect-secrets")
    for name, secrets in findings.items():
        for secret in secrets:
            print(f"  CRITICAL {secret['type']} at {name}:{secret.get('line_number')}")
    if not findings:
        print("  no secrets detected")
    return findings


def report_flake8(plugin_path):
    """Flake8. Informational on the website, so informational here too."""
    config = plugin_path / ".flake8"
    arguments = ["--max-line-length=120"]
    if config.is_file():
        arguments.append(f"--config={config}")
    arguments.append(".")

    process = run_tool("flake8", arguments, cwd=plugin_path)
    issues = [line for line in process.stdout.splitlines() if line.strip()]
    print(f"\nFlake8 (non-blocking): {len(issues)} issues")
    for issue in issues[:20]:
        print(f"  {issue}")
    if len(issues) > 20:
        print(f"  ... and {len(issues) - 20} more")


def report_files(plugin_path, marked_executable):
    """The website's package inspection: suspicious types, hidden files, executable bits."""
    suspicious, hidden, executable = [], [], []

    for root, directories, files in os.walk(plugin_path):
        directories[:] = [d for d in directories if d != "__pycache__"]
        for name in files:
            full_path = Path(root) / name
            relative = full_path.relative_to(plugin_path).as_posix()
            if full_path.suffix.lower() in SUSPICIOUS_SUFFIXES:
                suspicious.append(relative)
            if name.startswith("."):
                hidden.append(relative)
            if relative in marked_executable:
                executable.append(relative)

    print("\nPackaged files (non-blocking)")
    for label, entries in [("suspicious", suspicious), ("hidden", hidden), ("executable", executable)]:
        print(f"  {label}: {', '.join(sorted(entries)) if entries else 'none'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="scan tracked files as they are on disk instead of as they are committed at HEAD",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as work_dir:
        plugin_path, marked_executable = export_plugin(Path(work_dir), args.worktree)
        print(f"Scanning {PLUGIN_DIR} as {'in the working tree' if args.worktree else 'committed at HEAD'}\n")

        bandit_findings = check_bandit(plugin_path)
        secret_findings = check_secrets(plugin_path)
        report_bandit_advisories(plugin_path)
        report_flake8(plugin_path)
        report_files(plugin_path, marked_executable)

    blocking = len(bandit_findings) + sum(len(s) for s in secret_findings.values())
    if blocking:
        print(f"\nFAILED: {blocking} finding(s) would block publication on plugins.qgis.org")
        return 1

    print("\nPASSED: nothing that would block publication on plugins.qgis.org")
    return 0


if __name__ == "__main__":
    sys.exit(main())
