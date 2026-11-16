"""LLM tools limited to transcripts, frames and the Sources folder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..retrieval.hybrid import Retriever
from ..util import format_seconds, parse_seconds, truncate
from ..workspace.store import Conflict, NotFound, StoreError, WorkspaceStore

MAX_RANGE_SECONDS = 180
MAX_RANGE_TOKENS = 4000


@dataclass(slots=True)
class ToolContext:
    store: WorkspaceStore
    ws_dir: Any
    workspace: dict[str, Any]
    session: dict[str, Any]
    retriever: Retriever
    config: Any


def tool_definitions() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "search_transcripts",
                "description": "Search transcript chunks. Returns timestamped excerpts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "video_ids": {"type": "array", "items": {"type": "string"}},
                        "k": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_transcript_range",
                "description": "Read an exact transcript span for one video.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "start": {"type": "string", "description": "mm:ss or seconds"},
                        "end": {"type": "string", "description": "mm:ss or seconds"},
                    },
                    "required": ["video_id", "start", "end"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_videos",
                "description": "List the workspace videos with ids, titles and durations.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_sources",
                "description": "List workspace source documents.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_source",
                "description": "Read a workspace source document by file name.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_source",
                "description": "Create a new markdown source document.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["name", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "patch_source",
                "description": "Replace one unique snippet in a source document. The edit is versioned.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "find": {"type": "string"},
                        "replace": {"type": "string"},
                    },
                    "required": ["name", "find", "replace"],
                },
            },
        },
    ]
    return tools


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)[:12000]


def _chunk_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "video_id": chunk.get("video_id"),
        "start": chunk.get("start"),
        "end": chunk.get("end"),
        "citation": f"[{chunk.get('video_id')} @ {format_seconds(float(chunk.get('start') or 0))}]",
        "text": chunk.get("text"),
    }


async def execute_tool(name: str, arguments: dict[str, Any], ctx: ToolContext) -> str:
    try:
        if name == "search_transcripts":
            query = str(arguments.get("query") or "").strip()
            if not query:
                return _json({"error": "query is required"})
            video_ids = arguments.get("video_ids")
            filter_ids = {str(value) for value in video_ids} if isinstance(video_ids, list) else None
            k = int(arguments.get("k") or 6)
            results = ctx.retriever.search(query, k=max(1, min(k, 20)), video_ids=filter_ids)
            return _json({"results": [_chunk_payload(chunk) for chunk in results]})

        if name == "get_transcript_range":
            video_id = str(arguments.get("video_id") or "")
            start = parse_seconds(arguments.get("start", 0))
            end = parse_seconds(arguments.get("end", start + 60))
            end = min(end, start + MAX_RANGE_SECONDS)
            segments = ctx.store.read_segments(ctx.ws_dir, video_id)
            picked = [
                {
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "citation": f"[{video_id} @ {format_seconds(float(segment.get('start') or 0))}]",
                    "text": segment.get("text"),
                }
                for segment in segments
                if float(segment.get("end") or 0) >= start and float(segment.get("start") or 0) <= end
            ]
            while sum(len(str(item["text"])) for item in picked) // 4 > MAX_RANGE_TOKENS and picked:
                picked.pop()
            return _json({"video_id": video_id, "start": start, "end": end, "segments": picked})

        if name == "list_videos":
            return _json(
                {
                    "videos": [
                        {
                            "id": video.get("id"),
                            "title": video.get("title"),
                            "durationS": video.get("durationS"),
                            "status": video.get("status"),
                        }
                        for video in ctx.workspace.get("videos") or []
                    ]
                }
            )

        if name == "list_sources":
            return _json(
                {
                    "sources": [
                        {"name": source.get("name"), "updatedAt": source.get("updatedAt")}
                        for source in ctx.workspace.get("sources") or []
                    ]
                }
            )

        if name == "read_source":
            source = ctx.store.get_source(ctx.ws_dir, str(arguments.get("name") or ""))
            return _json({"name": source["name"], "content": truncate(source["content"], 12000)})

        if name == "create_source":
            source = ctx.store.create_source(
                ctx.ws_dir,
                str(arguments.get("name") or ""),
                str(arguments.get("content") or ""),
            )
            return _json({"created": source["name"], "id": source["id"]})

        if name == "patch_source":
            name_arg = str(arguments.get("name") or "")
            find = str(arguments.get("find") or "")
            replace = str(arguments.get("replace") or "")
            if not find:
                return _json({"error": "find must not be empty"})
            source = ctx.store.get_source(ctx.ws_dir, name_arg)
            count = source["content"].count(find)
            if count == 0:
                return _json({"error": "find text was not present in the source"})
            if count > 1:
                return _json({"error": f"find text matched {count} times; make it unique"})
            updated = source["content"].replace(find, replace, 1)
            result = ctx.store.update_source(ctx.ws_dir, name_arg, updated, "Patched by assistant")
            return _json({"patched": result["name"], "updatedAt": result["updatedAt"]})

        return _json({"error": f"unknown tool: {name}"})
    except (NotFound, Conflict, StoreError, ValueError) as exc:
        return _json({"error": str(exc)})
