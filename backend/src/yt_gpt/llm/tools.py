"""LLM tools for transcripts, Sources and optional video frames."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from ..retrieval.hybrid import Retriever
from ..util import format_seconds, parse_seconds, truncate
from ..vision.frames import VisualError, contact_sheet, frame_at, image_data_url
from ..workspace.store import Conflict, NotFound, StoreError, WorkspaceStore

MAX_RANGE_SECONDS = 180
MAX_RANGE_TOKENS = 4000


@dataclass(slots=True)
class ToolResult:
    text: str
    images: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolContext:
    store: WorkspaceStore
    ws_dir: Any
    workspace: dict[str, Any]
    session: dict[str, Any]
    retriever: Retriever
    config: Any
    visuals: bool = False


def tool_definitions(*, visuals: bool = False) -> list[dict[str, Any]]:
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
    if visuals:
        tools.extend(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "get_contact_sheet",
                        "description": (
                            "Return a timestamped contact sheet of video frames. Use this to inspect "
                            "slides, charts, demonstrations or visual context before answering."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "video_id": {"type": "string"},
                                "index": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 3,
                                    "description": "Zero-based contact sheet index.",
                                },
                                "refresh": {"type": "boolean"},
                            },
                            "required": ["video_id"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_frame",
                        "description": (
                            "Return a high-resolution frame near an exact timestamp when a detail "
                            "is too small on the contact sheet."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "video_id": {"type": "string"},
                                "start": {"type": "string", "description": "mm:ss or seconds"},
                            },
                            "required": ["video_id", "start"],
                        },
                    },
                },
            ]
        )
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


async def execute_tool(name: str, arguments: dict[str, Any], ctx: ToolContext) -> str | ToolResult:
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

        if name in {"get_contact_sheet", "get_frame"}:
            if not ctx.visuals:
                return _json({"error": "Visual tools are disabled for this workspace or chat."})
            video_id = str(arguments.get("video_id") or "")
            if name == "get_contact_sheet":
                index = int(arguments.get("index") or 0)
                refresh = bool(arguments.get("refresh") or False)
                sheet = await asyncio.to_thread(
                    contact_sheet, ctx.store, ctx.ws_dir, video_id, index, refresh=refresh
                )
                frames = sheet["sheet"].get("frames") or []
                text = _json(
                    {
                        "video_id": video_id,
                        "sheet": sheet["index"],
                        "sheet_count": sheet["sheet_count"],
                        "timestamps": [frame.get("label") for frame in frames],
                        "citation_hint": f"[{video_id} @ {frames[0].get('label')}]"
                        if frames
                        else "",
                        "note": "Frames are sampled from the video; use get_frame for exact detail.",
                    }
                )
                return ToolResult(text, [image_data_url(sheet["path"])])
            start = parse_seconds(arguments.get("start", 0))
            moment = await asyncio.to_thread(frame_at, ctx.store, ctx.ws_dir, video_id, start)
            label = format_seconds(float(moment["start"]))
            text = _json(
                {
                    "video_id": video_id,
                    "start": label,
                    "citation": f"[{video_id} @ {label}]",
                    "low_resolution": moment["low_resolution"],
                }
            )
            return ToolResult(text, [image_data_url(moment["path"])])

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
    except (NotFound, Conflict, StoreError, VisualError, ValueError) as exc:
        return _json({"error": str(exc)})
