#!/usr/bin/env python3
"""Ask natural-language questions to the Retail II Genie One Agent.

Usage:
    uv run --with databricks-sdk python genie/ask_genie.py "What percentage of revenue comes from guest checkouts?"
"""
import argparse
import sys
from databricks.sdk import WorkspaceClient

DEFAULT_SPACE_ID = "01f1be9f6999187ea0956f86f5fe7e9b"


def ask(question: str, space_id: str = DEFAULT_SPACE_ID, profile: str = None):
    kwargs = {}
    if profile:
        kwargs["profile"] = profile
    w = WorkspaceClient(**kwargs)

    print(f"Connecting to Genie Space: {space_id} on {w.config.host}")
    print(f"Question: {question}\n")

    response = w.genie.start_conversation_and_wait(
        space_id=space_id,
        content=question
    )

    print(f"Conversation ID: {response.conversation_id}\n")
    for att in (response.attachments or []):
        if hasattr(att, "query") and att.query:
            print("Generated SQL:")
            print(att.query.query.strip())
            print("-" * 60)
        if hasattr(att, "text") and att.text:
            print("Genie Answer:")
            print(att.text.content.strip())
            print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Databricks Genie Agent")
    parser.add_argument("question", help="Natural language question to ask Genie")
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID, help="Genie Space ID")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile")
    args = parser.parse_args()

    ask(args.question, space_id=args.space_id, profile=args.profile)
