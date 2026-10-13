#!/usr/bin/env python3
"""Deploy or update the Genie One Agent for Retail II Governed Analytics.

Provisions a Databricks Genie Space backed by Unity Catalog Gold and Silver tables,
including table & column metadata, natural-language instructions, sample questions,
and five verified Golden SQL benchmark queries.

Usage:
    uv run --with databricks-sdk python genie/deploy_genie.py [--profile <profile>] [--warehouse-id <id>]
"""
import argparse
import json
import os
import sys
from pathlib import Path
from databricks.sdk import WorkspaceClient


def deploy(profile: str = None, warehouse_id: str = None, space_id: str = None):
    kwargs = {}
    if profile:
        kwargs["profile"] = profile
    w = WorkspaceClient(**kwargs)
    
    print(f"Connected to workspace: {w.config.host}")
    current_user = w.current_user.me().user_name
    print(f"Authenticated as: {current_user}")

    # Determine SQL warehouse
    if not warehouse_id:
        print("Auto-detecting SQL warehouse...")
        warehouses = list(w.warehouses.list())
        if not warehouses:
            raise RuntimeError("No SQL warehouses found in the workspace.")
        warehouse = next((wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"), warehouses[0])
        warehouse_id = warehouse.id
        print(f"Using warehouse: {warehouse.name} (ID: {warehouse_id})")

    # Load serialized space configuration
    config_path = Path(__file__).parent / "space_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)

    space_payload = export_data.get("config", export_data)
    title = export_data.get("title", "EDA Governed Gold Analytics")
    description = export_data.get("description", "Self-service analytics over governed gold retail tables")

    # Sort array elements by id as required by the Genie REST API schema
    if "config" in space_payload and "sample_questions" in space_payload["config"]:
        space_payload["config"]["sample_questions"].sort(key=lambda x: x.get("id", ""))
    if "instructions" in space_payload:
        if "text_instructions" in space_payload["instructions"]:
            space_payload["instructions"]["text_instructions"].sort(key=lambda x: x.get("id", ""))
        if "example_question_sqls" in space_payload["instructions"]:
            space_payload["instructions"]["example_question_sqls"].sort(key=lambda x: x.get("id", ""))

    serialized_space = json.dumps(space_payload)

    # Deploy or update space
    target_space_id = space_id or export_data.get("space_id")
    if target_space_id:
        try:
            print(f"Updating existing Genie Space (ID: {target_space_id})...")
            w.genie.update_space(
                space_id=target_space_id,
                title=title,
                description=description,
                warehouse_id=warehouse_id,
                serialized_space=serialized_space
            )
            created_id = target_space_id
            print(f"Successfully updated Genie Space: {target_space_id}")
        except Exception as e:
            print(f"Update failed ({e}); creating a new space instead...")
            target_space_id = None

    if not target_space_id:
        print("Creating new Genie Space...")
        space = w.genie.create_space(
            title=title,
            description=description,
            warehouse_id=warehouse_id,
            serialized_space=serialized_space,
            parent_path=f"/Users/{current_user}/synaptiq/exercise-2"
        )
        created_id = space.space_id
        print(f"Successfully created Genie Space: {created_id}")

    room_url = f"{w.config.host}/genie/rooms/{created_id}"
    print(f"\nGenie Agent URL: {room_url}")

    # Run verification question
    print("\nVerifying agent with sample question...")
    try:
        resp = w.genie.start_conversation_and_wait(
            space_id=created_id,
            content="What were the top 5 revenue days in Q4 2010?"
        )
        print(f"Conversation ID: {resp.conversation_id}")
        for att in (resp.attachments or []):
            if hasattr(att, "text") and att.text:
                print(f"Genie response:\n{att.text.content.strip()}\n")
            if hasattr(att, "query") and att.query:
                print(f"SQL generated:\n{att.query.query.strip()}\n")
    except Exception as e:
        print(f"Note: Verification query did not execute (warehouse may be paused): {e}")

    return created_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy Databricks Genie Agent")
    parser.add_argument("--profile", help="Databricks CLI profile name")
    parser.add_argument("--warehouse-id", help="Target SQL Warehouse ID")
    parser.add_argument("--space-id", help="Target Genie Space ID to update")
    args = parser.parse_args()

    deploy(profile=args.profile, warehouse_id=args.warehouse_id, space_id=args.space_id)
