#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""List the account's convertible single MySQL instances across all regions.

Overview:
    This script discovers every RDS for MySQL single instance of the
    account in one call via the `hcloud` (KooCLI) command line tool and
    prints the convertible ones as pretty JSON to stdout. It is the
    instance discovery tool of the SKILL workflow: the Agent renders the
    JSON as a table and asks the user to pick the instance to convert.

Detailed Description:
    Discovery goes through RMS ListAllResources, which aggregates resources
    of all regions: the account domain id is resolved via IAM
    KeystoneListAuthDomains, then every page of `type=rds.instances` is
    fetched. The RMS cli-region channel only accepts cn-north-4, so that
    value is hard-coded. The script takes no region parameter on purpose:
    the step must list every single MySQL instance of the account, and any
    region filter would narrow that set. Pagination follows
    page_info.next_marker with limit=200 and drops repeated ids.

    Only convertible entries are emitted: engine mysql, haMode Single and
    state Normal. RMS reports a different volumeType vocabulary (ULTRAHIGH)
    than ListInstances (CLOUDSSD), so the summary carries the RMS value for
    display only; the conversion steps re-read the instance from
    ListInstances for authoritative region, flavor, version, storage and
    charge mode values. The script is read-only: it never mutates anything
    and writes no report file.

Workflow:
    1. Parse the command line (no parameters).
    2. Resolve the account domain id via KeystoneListAuthDomains.
    3. Fetch all rds.instances pages via RMS ListAllResources.
    4. Flatten each resource and keep the convertible single MySQL ones.
    5. Print the selected instances as pretty JSON to stdout.

Dependencies:
    - Python 3.9+ standard library only (argparse, logging, sys).
    - rds_common (same directory, shared helpers).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated, with `iam:domains:list` and `rms:resources:list`
      permissions.
"""

from __future__ import annotations

import argparse
import logging
import sys

import rds_common as common

LOGGER = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Register the platform-injected `--domain_id` and `--x_user_auth_token`
       options; discovery takes no region parameter because it always covers
       the whole account.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args, unknown = parser.parse_known_args([])
        >>> (args.domain_id, args.x_user_auth_token, unknown)
        (None, None, [])
        >>> parser.parse_args(["--region", "cn-north-4"])
        Traceback (most recent call last):
        SystemExit: 2
    """
    parser = argparse.ArgumentParser(
        prog="list_instances",
        description=(
            "List every convertible single MySQL instance of the account "
            "across all regions as pretty JSON via the hcloud CLI. Discovery "
            "uses RMS (fixed cn-north-4 channel) and takes no region "
            "parameter."
        ),
    )
    common.add_platform_arguments(parser)
    return parser


def run() -> int:
    """Resolve the domain, list the instances and print the convertible ones.

    1. Resolve the account domain id via KeystoneListAuthDomains.
    2. Fetch every rds.instances page via RMS ListAllResources.
    3. Flatten the resources and keep the convertible single MySQL ones.
    4. Print the selected instances as pretty JSON to stdout.

    Args:
        None

    Returns:
        int: Exit code (0 on success, 1 on failure).

    Examples:
        # Requires hcloud credentials:
        # >>> run()
        1
    """
    try:
        domain_id = common.resolve_domain_id(common.DEFAULT_TIMEOUT)
        resources = common.list_all_resources(domain_id, common.DEFAULT_TIMEOUT)
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1
    summaries = [common.build_instance_summary(resource) for resource in resources]
    selected = common.select_single_mysql_instances(summaries)
    LOGGER.info(
        "Found %d RDS resources across all regions, %d convertible single "
        "MySQL instances.",
        len(resources),
        len(selected),
    )
    print(common.format_discovery_json(selected, []))
    return 0


def main() -> int:
    """Run the instance discovery workflow.

    1. Parse arguments, including the platform-injected compatibility
       options, and set up logging.
    2. Delegate to run() for resolution and printing.

    Args:
        None

    Returns:
        int: Exit code (0 on success, 1 on failure).

    Examples:
        # Running the script requires hcloud credentials:
        # >>> main()
        1
    """
    common.parse_known_arguments(build_arg_parser())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    return run()


if __name__ == "__main__":
    sys.exit(main())
