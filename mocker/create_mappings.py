"""
Script for creating mapping configurations for mocker raw data.

This script creates mapping configurations that transform raw data
from various source types (kubernetes-api, opentelemetry-traces, etc.)
into the internal graph model (16 node types, 11 edge types).

Usage:
    python -m mocker.create_mappings --url http://localhost:8000
    python -m mocker.create_mappings --url http://localhost:8000 --dry-run
    python -m mocker.create_mappings --url http://localhost:8000 --source-type kubernetes-api
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests

from mocker.mappings import ALL_MAPPINGS


def check_existing_mapping(base_url: str, name: str) -> bool:
    """Check if a mapping with the given name already exists."""
    try:
        resp = requests.get(f"{base_url}/api/v1/mapper/", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        mappings = data.get("mappings", [])
        return any(m["name"] == name for m in mappings)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to check existing mappings: {e}")
        return False


def create_mapping(base_url: str, config: dict[str, Any]) -> dict[str, Any] | None:
    """Create a mapping configuration via API."""
    try:
        resp = requests.post(
            f"{base_url}/api/v1/mapper/",
            json=config,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to create mapping: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"        Response: {e.response.text}")
        return None


def activate_mapping(base_url: str, mapping_id: str) -> bool:
    """Activate a mapping configuration."""
    try:
        resp = requests.post(
            f"{base_url}/api/v1/mapper/{mapping_id}/activate",
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Failed to activate mapping: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create mapping configurations for mocker raw data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create all mappings
    python -m mocker.create_mappings --url http://localhost:8000

    # Dry run (show what would be created)
    python -m mocker.create_mappings --url http://localhost:8000 --dry-run

    # Create only specific source type
    python -m mocker.create_mappings --source-type kubernetes-api
        """,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the backend API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes",
    )
    parser.add_argument(
        "--source-type",
        help="Create mapping for a specific source type only",
        choices=[
            "kubernetes-api",
            "opentelemetry-traces",
            "opentelemetry-metrics",
            "istio-access-logs",
            "istio-metrics",
            "prometheus",
            "terraform-state",
            "argocd",
            "api-gateway",
        ],
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Create mappings without activating them",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    print(f"Backend URL: {args.url}")
    print(f"Source types to process: {args.source_type or 'all'}")
    print()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for mapping in ALL_MAPPINGS:
        source_type = mapping["source_type"]
        name = mapping["name"]

        # Filter by source type if specified
        if args.source_type and source_type != args.source_type:
            continue

        # Check if already exists
        if check_existing_mapping(args.url, name):
            print(f"[SKIP] {name} (already exists)")
            skipped_count += 1
            continue

        # Dry run mode
        if args.dry_run:
            print(f"[DRY-RUN] Would create: {name}")
            if args.verbose:
                print(f"           source_type: {source_type}")
                print(f"           field_mappings: {len(mapping.get('field_mappings', []))}")
                print(f"           conditional_rules: {len(mapping.get('conditional_rules', []))}")
            created_count += 1
            continue

        # Create mapping
        print(f"[CREATE] {name}...")
        created = create_mapping(args.url, mapping)

        if created is None:
            error_count += 1
            continue

        created_count += 1
        mapping_id = created.get("id", "unknown")
        print(f"[CREATED] {name} (id={mapping_id})")

        # Activate mapping
        if not args.no_activate:
            if activate_mapping(args.url, mapping_id):
                print(f"[ACTIVATED] {name}")
            else:
                print(f"[WARNING] Failed to activate {name}")

        if args.verbose:
            print(f"  source_type: {source_type}")
            print(f"  field_mappings: {len(mapping.get('field_mappings', []))}")
            print(f"  conditional_rules: {len(mapping.get('conditional_rules', []))}")
            print()

    # Summary
    print()
    print("=" * 50)
    print(f"Summary: {created_count} created, {skipped_count} skipped, {error_count} errors")

    if args.dry_run:
        print("(dry-run mode - no changes made)")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
