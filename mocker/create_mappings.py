from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import httpx

from mocker.mappings import ALL_MAPPINGS
from mocker.sample_data import SAMPLE_DATA_BY_SOURCE_TYPE, PRIMARY_SAMPLE_BY_SOURCE_TYPE


def register_agent(base_url: str, name: str, source_type: str) -> str | None:
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/agents/register",
            json={"name": name, "source_type": source_type},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("token")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"[ERROR] Failed to register agent: {e}")
        return None


def send_raw_data(
    base_url: str,
    source_type: str,
    data: Dict[str, Any],
    token: str,
) -> str | None:
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/receiver/raw?source_type={source_type}",
            json=data,
            headers={"X-Agent-Token": token},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("chunk_id")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"[ERROR] Failed to send raw data: {e}")
        return None


def check_existing_mapping(base_url: str, name: str) -> bool:
    try:
        resp = httpx.get(f"{base_url}/api/v1/mapper/", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        mappings = data.get("mappings", [])
        return any(m["name"] == name for m in mappings)
    except (httpx.RequestError, httpx.HTTPStatusError):
        return False


def get_existing_chunk_for_source_type(base_url: str, source_type: str) -> str | None:
    try:
        resp = httpx.get(
            f"{base_url}/api/v1/receiver/raw",
            params={"source_type": source_type, "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        chunks = data.get("chunks", [])
        if chunks:
            return chunks[0].get("id")
        return None
    except (httpx.RequestError, httpx.HTTPStatusError):
        return None


def create_mapping(base_url: str, config: dict[str, Any]) -> dict[str, Any] | None:
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/mapper/",
            json=config,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] Failed to create mapping: {e}")
        if e.response is not None:
            print(f"        Response: {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"[ERROR] Failed to create mapping: {e}")
        return None


def activate_mapping(base_url: str, mapping_id: str) -> bool:
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/mapper/{mapping_id}/activate",
            timeout=60,
        )
        resp.raise_for_status()
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"[ERROR] Failed to activate mapping: {e}")
        return False


def recreate_all_edges(base_url: str) -> dict[str, Any] | None:
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/mapper/recreate-edges",
            json={},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"[ERROR] Failed to recreate edges: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create mapping configurations with sample_chunk_id",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        choices=list(SAMPLE_DATA_BY_SOURCE_TYPE.keys()),
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Create mappings without activating them",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Skip sending sample data (only create mappings)",
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

    agent_token = None
    if not args.dry_run and not args.skip_data:
        agent_token = register_agent(args.url, "mapping-creator", "kubernetes-api")
        if not agent_token:
            print("[ERROR] Failed to register agent, cannot send sample data")
            return 1

    created_count = 0
    skipped_count = 0
    error_count = 0
    chunks_sent = 0

    for mapping in ALL_MAPPINGS:
        source_type = mapping["source_type"]
        name = mapping["name"]

        if args.source_type and source_type != args.source_type:
            continue

        if check_existing_mapping(args.url, name):
            print(f"[SKIP] {name} (already exists)")
            skipped_count += 1
            continue

        sample_chunk_id = None
        if not args.dry_run and not args.skip_data:
            existing_chunk_id = get_existing_chunk_for_source_type(args.url, source_type)

            if existing_chunk_id:
                sample_chunk_id = existing_chunk_id
                print(f"[DATA] Using existing chunk for {source_type}: {sample_chunk_id[:8]}...")
                if args.verbose:
                    print(f"       chunk_id: {sample_chunk_id}")
            elif agent_token:
                samples = SAMPLE_DATA_BY_SOURCE_TYPE.get(source_type, [])
                primary_sample = PRIMARY_SAMPLE_BY_SOURCE_TYPE.get(source_type)

                if primary_sample:
                    print(f"[DATA] Sending sample data for {source_type}...")
                    sample_chunk_id = send_raw_data(args.url, source_type, primary_sample, agent_token)

                    if sample_chunk_id:
                        chunks_sent += 1
                        if args.verbose:
                            print(f"       chunk_id: {sample_chunk_id}")

                        for i, sample in enumerate(samples[1:], 1):
                            chunk_id = send_raw_data(args.url, source_type, sample, agent_token)
                            if chunk_id:
                                chunks_sent += 1
                                if args.verbose:
                                    print(f"       additional chunk {i}: {chunk_id}")
                    else:
                        print(f"[WARN] Failed to send sample data for {source_type}")

        if args.dry_run:
            print(f"[DRY-RUN] Would create: {name}")
            if args.verbose:
                print(f"           source_type: {source_type}")
                print(f"           field_mappings: {len(mapping.get('field_mappings', []))}")
                print(f"           conditional_rules: {len(mapping.get('conditional_rules', []))}")
                print(f"           sample_data: {len(SAMPLE_DATA_BY_SOURCE_TYPE.get(source_type, []))} chunks")
            created_count += 1
            continue

        mapping_config = dict(mapping)
        if sample_chunk_id:
            mapping_config["sample_chunk_id"] = sample_chunk_id

        print(f"[CREATE] {name}...")
        created = create_mapping(args.url, mapping_config)

        if created is None:
            error_count += 1
            continue

        created_count += 1
        mapping_id = created.get("id", "unknown")
        print(f"[CREATED] {name} (id={mapping_id})")
        if sample_chunk_id:
            print(f"         sample_chunk_id: {sample_chunk_id}")

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

    print()
    print("=" * 50)
    print(f"Summary:")
    print(f"  Mappings: {created_count} created, {skipped_count} skipped, {error_count} errors")
    print(f"  Sample data chunks sent: {chunks_sent}")

    if created_count > 0 and not args.dry_run and not args.no_activate:
        import time
        print()
        print("[EDGES] Waiting for background replays to complete...")
        time.sleep(3)
        print("[EDGES] Recreating all edges...")
        result = recreate_all_edges(args.url)
        if result:
            print(f"[EDGES] Created {result['edges_created']} edges, {result['unresolved_count']} unresolved references")

    if args.dry_run:
        print("(dry-run mode - no changes made)")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
