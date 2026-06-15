"""Shared CLI helpers for OEP publish commands."""

from __future__ import annotations

from argparse import ArgumentParser

from mappers.oep.api import OEP_API_TOKEN_ENV


def add_oep_publish_cli_args(parser: ArgumentParser) -> None:
    """Register ``--token``, ``--method``, and ``--skip-validation`` on a parser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to extend in place.

    Returns
    -------
    None
    """
    parser.add_argument(
        "--token",
        default=None,
        help=f"OEP user API token (or {OEP_API_TOKEN_ENV} env var).",
    )
    parser.add_argument(
        "--method",
        default="POST",
        choices=("POST", "PUT"),
        help="HTTP method for OEP table meta API (default POST).",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip OMI OEMetadata validation before push (not recommended).",
    )
    parser.add_argument(
        "--no-infer-schema",
        action="store_true",
        help="Do not download source file samples to infer schema.fields (Zenodo/CKAN URLs).",
    )
    parser.add_argument(
        "--no-provision-tables",
        action="store_true",
        help="Do not create empty OEP tables before metadata push.",
    )
    parser.add_argument(
        "--schema-sample-lines",
        type=int,
        default=None,
        help="Lines to stream per source file for schema inference (default: 2).",
    )
