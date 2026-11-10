#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive inspection deliverables to the user home directory.

Overview:
    This is the Step 7 tool of the SKILL workflow. It relocates the final
    deliverables of one inspection run — the offline HTML report, the Excel
    workbook and, on scoped runs, the risk-item JSON — from the local report
    directory into a per-run subdirectory under the user home directory
    (`~/.hcloud-oa-risk/<timestamp>/`), using a copy-verify-delete strategy
    (the safe form of `move`).

Detailed Description:
    The report generator writes its artifacts into `analysis/<timestamp>/`
    relative to the caller's working directory, so the location changes with
    the caller and users cannot reliably find their own report. The merged
    inspection JSON is a workflow intermediate, not a deliverable, so it is
    neither archived nor preserved here; the workflow deletes it as one of its
    temporary JSON files. The risk-item JSON is a deliverable because it
    records the cloud-service scope the run was limited to, so it is archived
    whenever it exists.

    The archive operation:
      - Collects candidates from `--report-dir` (direct children matching the
        report HTML / XLSX / risk-item JSON name patterns, never recursing).
        The report directory is created fresh by the report generator for this
        run, so listing it cannot pick up another run's files; this is not a
        timestamp guess.
      - Skips candidates that do not exist and records the reason.
      - For each remaining file: copies it into the archive directory,
        verifies the destination exists and its byte size matches the source,
        then deletes the original.
      - Writes an `archive_manifest.json` recording archived, skipped and
        failed entries with absolute paths.
      - Removes the report directory with a non-recursive `rmdir`, so a
        directory still holding any file survives untouched.

Workflow:
    1. Parse the command-line arguments (report directory and optional archive
       directory override).
    2. Resolve the archive directory from the user home directory or the
       override.
    3. Collect the candidate files from the report directory.
    4. Copy, verify and delete each candidate.
    5. Write the manifest and remove the report directory when it is empty.
    6. Return a non-zero exit code when any file failed to archive.

Dependencies:
    Python standard library only: argparse, json, logging, os, shutil, sys,
    datetime. No third-party dependencies. The script is purely local and
    does not call hcloud or access the network.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Any


LOGGER = logging.getLogger(__name__)

# Archive location under the user home directory. Each run gets its own
# timestamp subdirectory directly under this directory.
ARCHIVE_DIR_NAME = ".hcloud-oa-risk"
MANIFEST_NAME = "archive_manifest.json"
# Report artifact naming produced by merge_report_generator.py. Candidates are
# matched by prefix and suffix among the direct children of --report-dir. The
# risk-item JSON is a deliverable only on scoped runs; it is matched by its own
# suffix so the merged inspection JSON and any other JSON stay out of the
# archive.
REPORT_NAME_PREFIX = "merge_inspection_report_"
REPORT_NAME_SUFFIXES = (".html", ".xlsx", "_risk_items.json")
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
# Fixed skip reasons recorded in the manifest so the summary can quote them.
SKIP_REASON_NON_EXISTENT = "non-existent"
SKIP_REASON_NOT_A_FILE = "not a regular file"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    1. Add the required report directory option.
    2. Add the optional archive directory and logging options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser with all options.

    Examples:
        >>> parser = build_arg_parser()
        >>> "--report-dir" in parser.format_help()
        True
    """
    parser = argparse.ArgumentParser(
        prog="archive_artifacts",
        description=(
            "Archive inspection deliverables (HTML report and Excel workbook) "
            "to the user home directory."
        ),
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        help=(
            "Required. Absolute path of the timestamped report directory "
            "produced by the report generation step."
        ),
    )
    parser.add_argument(
        "--archive-dir",
        default=None,
        help=(
            "Optional. Archive directory override. Defaults to "
            "~/.hcloud-oa-risk/<local timestamp>/."
        ),
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional. Path to a log file; logs are appended to stderr as well.",
    )
    return parser


def setup_logging(log_file: str | None) -> None:
    """Set up the logging framework.

    1. Configure the root logger level to INFO.
    2. Add a stderr StreamHandler.
    3. Add a FileHandler when log_file is provided.

    Args:
        log_file: str | None — Optional path for file logging.

    Returns:
        None

    Examples:
        >>> setup_logging(None)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s"
    )
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def resolve_archive_dir(timestamp: str, override: str | None = None) -> str:
    """Resolve the absolute archive directory for one run.

    1. Return the resolved override when one is provided.
    2. Expand the user home directory and append the archive directory name
       and the run timestamp otherwise.

    Args:
        timestamp: str — Local-time timestamp string for the directory name.
        override: str | None — Explicit archive directory, or None.

    Returns:
        str: Absolute archive directory path.

    Examples:
        >>> resolve_archive_dir("2026_11_03_18_30_00").endswith(
        ...     os.path.join(".hcloud-oa-risk", "2026_11_03_18_30_00"))
        True
    """
    if override:
        return os.path.abspath(override)
    home = os.path.expanduser("~")
    return os.path.abspath(os.path.join(home, ARCHIVE_DIR_NAME, timestamp))


def _is_report_file_name(entry: str) -> bool:
    """Decide whether a directory entry is a report artifact.

    1. Require the report filename prefix.
    2. Require one of the known report suffixes, which include the scoped
       risk-item JSON written on whitelisted runs.
    3. Reject every other JSON, so the merged inspection JSON and stray
       files never enter the archive.

    Args:
        entry: str — A direct child name of the report directory.

    Returns:
        bool: True when the name matches the report artifact pattern.

    Examples:
        >>> _is_report_file_name("merge_inspection_report_2026_11_03_18_30_00.html")
        True
        >>> _is_report_file_name("merge_inspection_report_2026_11_03_18_30_00_risk_items.json")
        True
        >>> _is_report_file_name("merge_inspection_results_2026_11_03_18_30_00.json")
        False
    """
    return entry.startswith(REPORT_NAME_PREFIX) and entry.endswith(
        REPORT_NAME_SUFFIXES
    )


def collect_candidates(report_dir: str) -> list[str]:
    """Collect the absolute candidate paths to archive.

    1. List the direct children of the report directory and keep the ones
       matching the report artifact pattern.
    2. Return the absolute paths in sorted order.

    Args:
        report_dir: str — Absolute path of the timestamped report directory.

    Returns:
        list[str]: Absolute candidate file paths (existence is checked later).

    Examples:
        >>> collect_candidates("C:/tmp/missing")
        []
    """
    candidates: list[str] = []
    try:
        entries = os.listdir(report_dir)
    except OSError as exc:
        LOGGER.warning("Report directory cannot be listed: %s (%s)", report_dir, exc)
        entries = []
    for entry in sorted(entries):
        if not _is_report_file_name(entry):
            continue
        candidates.append(os.path.abspath(os.path.join(report_dir, entry)))
    return candidates


def archive_one_file(src: str, archive_dir: str) -> dict[str, Any]:
    """Archive a single file via copy-verify-delete.

    1. Copy the file into the archive directory preserving its basename.
    2. Verify the destination exists and its byte size matches the source.
    3. Delete the source only after successful verification.

    Args:
        src: str — Absolute path of the source file.
        archive_dir: str — Absolute path of the archive directory.

    Returns:
        dict[str, Any]: Result with source, destination, archived flag, bytes
            on success, and detail on failure.

    Examples:
        # >>> archive_one_file("/abs/report.html", "/abs/archive")
        # {'source': '/abs/report.html', 'destination': '/abs/archive/report.html', 'archived': True, 'bytes': 1024, 'detail': 'archived'}
    """
    name = os.path.basename(src)
    dest = os.path.join(archive_dir, name)
    try:
        shutil.copy2(src, dest)
    except OSError as exc:
        return {
            "source": src,
            "destination": dest,
            "archived": False,
            "detail": "copy failed: {}".format(exc),
        }
    if not os.path.exists(dest):
        return {
            "source": src,
            "destination": dest,
            "archived": False,
            "detail": "destination missing after copy",
        }
    source_size = os.path.getsize(src)
    destination_size = os.path.getsize(dest)
    if source_size != destination_size:
        return {
            "source": src,
            "destination": dest,
            "archived": False,
            "detail": "size mismatch: src={} dest={}".format(
                source_size, destination_size
            ),
        }
    try:
        os.remove(src)
    except OSError as exc:
        return {
            "source": src,
            "destination": dest,
            "archived": False,
            "detail": "delete-original failed: {}".format(exc),
        }
    return {
        "source": src,
        "destination": dest,
        "archived": True,
        "bytes": destination_size,
        "detail": "archived",
    }


def run_archive(
    report_dir: str,
    archive_dir: str,
    timestamp: str,
) -> dict[str, Any]:
    """Archive every candidate and remove the report directory when emptied.

    1. Create the archive directory.
    2. Collect the candidates from the report directory.
    3. Skip missing or non-file candidates and archive the rest.
    4. Remove the report directory with a non-recursive rmdir.
    5. Return the manifest dictionary.

    Args:
        report_dir: str — Absolute path of the timestamped report directory.
        archive_dir: str — Absolute path of the archive directory.
        timestamp: str — The run timestamp recorded in the manifest.

    Returns:
        dict[str, Any]: Manifest with archive_dir, timestamp, archived,
            skipped, failures and report_dir_removed.

    Examples:
        # >>> run_archive("/abs/report", "/abs/archive", "2026_11_03_18_30_00")
        # {'archive_dir': '/abs/archive', 'archived': [...], ...}
    """
    os.makedirs(archive_dir, exist_ok=True)
    archived: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for path in collect_candidates(report_dir):
        if not os.path.exists(path):
            skipped.append({"source": path, "reason": SKIP_REASON_NON_EXISTENT})
            continue
        if not os.path.isfile(path):
            skipped.append({"source": path, "reason": SKIP_REASON_NOT_A_FILE})
            continue
        result = archive_one_file(path, archive_dir)
        if result["archived"]:
            archived.append(result)
            LOGGER.info("Archived %s -> %s", result["source"], result["destination"])
        else:
            failures.append(result)
            LOGGER.error(
                "Failed to archive %s: %s", result["source"], result["detail"]
            )
    report_dir_removed = _remove_report_dir(report_dir)
    manifest: dict[str, Any] = {
        "archive_dir": archive_dir,
        "timestamp": timestamp,
        "archived": archived,
        "skipped": skipped,
        "failures": failures,
        "report_dir_removed": report_dir_removed,
    }
    return manifest


def _remove_report_dir(report_dir: str) -> bool:
    """Remove the report directory only when it is already empty.

    1. Resolve the directory to an absolute path.
    2. Call the non-recursive os.rmdir so a non-empty directory survives.
    3. Return whether the directory was removed.

    Args:
        report_dir: str — Absolute or relative report directory path.

    Returns:
        bool: True when the directory was removed, False otherwise.

    Examples:
        # >>> _remove_report_dir("/abs/emptied-report-dir")
        # True
    """
    target = os.path.abspath(report_dir)
    try:
        os.rmdir(target)
    except OSError as exc:
        LOGGER.info("Report directory kept (%s): %s", exc, target)
        return False
    LOGGER.info("Report directory removed: %s", target)
    return True


def write_manifest(manifest: dict[str, Any], archive_dir: str) -> str:
    """Write the archive manifest into the archive directory.

    1. Serialize the manifest with ensure_ascii=False and indent=2.
    2. Write it to archive_dir/archive_manifest.json.
    3. Return the absolute manifest path.

    Args:
        manifest: dict[str, Any] — The archive manifest.
        archive_dir: str — Absolute path of the archive directory.

    Returns:
        str: Absolute path of the written manifest.

    Examples:
        # >>> write_manifest({"archived": []}, "/abs/archive")
        # '/abs/archive/archive_manifest.json'
    """
    manifest_path = os.path.join(archive_dir, MANIFEST_NAME)
    with open(manifest_path, "w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, ensure_ascii=False, indent=2)
    return os.path.abspath(manifest_path)


def print_summary(manifest: dict[str, Any], manifest_path: str) -> None:
    """Emit the archive summary via logging to stderr.

    1. Log the archive directory and per-category counts.
    2. Log every archived file's absolute destination path.
    3. Log skipped and failed entries with their reasons.

    Args:
        manifest: dict[str, Any] — The archive manifest.
        manifest_path: str — Absolute path of the written manifest.

    Returns:
        None

    Examples:
        # >>> print_summary({"archived": [], "skipped": [], "failures": []}, "/abs/manifest.json")
    """
    LOGGER.info("=" * 60)
    LOGGER.info("Archive of inspection deliverables completed")
    LOGGER.info("=" * 60)
    LOGGER.info("Archive directory: %s", manifest.get("archive_dir", ""))
    LOGGER.info(
        "Archived: %d, skipped: %d, failed: %d",
        len(manifest.get("archived", [])),
        len(manifest.get("skipped", [])),
        len(manifest.get("failures", [])),
    )
    for item in manifest.get("archived", []):
        LOGGER.info(
            "  - %s (%d bytes)", item.get("destination", ""), item.get("bytes", 0)
        )
    for item in manifest.get("skipped", []):
        LOGGER.warning(
            "  - skipped %s: %s", item.get("source", ""), item.get("reason", "")
        )
    for item in manifest.get("failures", []):
        LOGGER.error(
            "  - failed %s: %s", item.get("source", ""), item.get("detail", "")
        )
    LOGGER.info("Manifest: %s", manifest_path)
    LOGGER.info(
        "Report directory removed: %s", manifest.get("report_dir_removed", False)
    )
    LOGGER.info("=" * 60)


def run(args: argparse.Namespace) -> int:
    """Run the archive operation from parsed arguments.

    1. Resolve the archive directory from the override or the user home.
    2. Run the archive operation and write the manifest.
    3. Emit the summary and return the exit code.

    Args:
        args: argparse.Namespace — Parsed command-line arguments.

    Returns:
        int: Exit code; 0 when every candidate was archived, 1 otherwise.

    Examples:
        # >>> run(argparse.Namespace(report_dir="/abs/report", archive_dir=None))
        # 0
    """
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    archive_dir = resolve_archive_dir(timestamp, args.archive_dir)
    LOGGER.info(
        "Archiving artifacts from %s to %s", args.report_dir, archive_dir
    )
    manifest = run_archive(args.report_dir, archive_dir, timestamp)
    manifest_path = write_manifest(manifest, archive_dir)
    print_summary(manifest, manifest_path)
    return 1 if manifest["failures"] else 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the archive operation.

    1. Parse the command-line arguments.
    2. Set up logging.
    3. Run the archive operation and return its exit code.

    Args:
        argv: list[str] | None — Optional argument list; sys.argv[1:] when None.

    Returns:
        int: Exit code from run().

    Examples:
        # >>> main(["--report-dir", "/abs/report"])
        # 0
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_file)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
