"""``yt-gpt serve | doctor | export | version``."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

from . import config
from .llm.embeddings import ensure_workspace_embeddings
from .llm.provider import LlmConfig
from .util import iso_now
from .version import __version__
from .workspace.store import StoreError, WorkspaceStore


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    cfg = config.load_config()
    host = args.host or cfg.host
    port = args.port or cfg.port
    url = f"http://{'127.0.0.1' if host in {'0.0.0.0', '::'} else host}:{port}"
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"yt-gpt {__version__} serving at {url}")
    uvicorn.run("yt_gpt.server.app:app", host=host, port=port, log_level=cfg.log_level)
    return 0


def _check(label: str, value: str, ok: bool, hint: str = "") -> dict[str, object]:
    return {"label": label, "value": value, "ok": ok, "hint": hint}


def doctor_checks() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    root = config.home()
    try:
        config.ensure_home()
        probe = root / ".doctor"
        probe.write_text(iso_now(), encoding="utf-8")
        probe.unlink()
        checks.append(_check("Home", str(root), True))
    except OSError as exc:
        checks.append(_check("Home", f"{root} ({exc})", False, "Pick a writable YT_GPT_HOME."))

    try:
        import yt_dlp

        version = getattr(yt_dlp.version, "__version__", "unknown")
        checks.append(_check("yt-dlp", version, True))
    except Exception as exc:
        checks.append(_check("yt-dlp", str(exc), False, "Reinstall yt-gpt."))

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    checks.append(
        _check("ffmpeg", ffmpeg or "missing", bool(ffmpeg), "Install ffmpeg or the imageio-ffmpeg extra.")
    )

    try:
        import faster_whisper  # noqa: F401

        whisper = "installed"
    except Exception:
        whisper = "not installed (optional)"
    checks.append(
        _check(
            "Whisper fallback",
            whisper,
            True,
            "Install yt-gpt[whisper] to transcribe videos without captions.",
        )
    )

    cookies = config.cookies_file()
    checks.append(
        _check(
            "Cookies",
            str(cookies) if cookies else "none",
            True,
            "Only needed for private or age-gated videos.",
        )
    )

    profiles = config.local_user_profiles()
    checks.append(_check("Profiles", str(len(profiles)), bool(profiles), "Create a profile in the browser."))
    return checks


def _rebuild_all() -> tuple[int, int]:
    videos = 0
    workspaces = 0
    for profile in config.local_user_profiles():
        user_id = profile.get("id")
        if not isinstance(user_id, str):
            continue
        store = WorkspaceStore(user_id)
        for workspace in store.list_workspaces():
            try:
                ws_dir = store.resolve(str(workspace.get("id")))
                videos += store.rebuild_derived(ws_dir)
                workspaces += 1
            except StoreError:
                continue
    return workspaces, videos


def _doctor(args: argparse.Namespace) -> int:
    checks = doctor_checks()
    for check in checks:
        status = "ok" if check["ok"] else "warn"
        print(f"[{status:4}] {check['label']}: {check['value']}")
        if check.get("hint") and not check["ok"]:
            print(f"       {check['hint']}")
    if args.rebuild:
        workspaces, videos = _rebuild_all()
        print(f"Rebuilt {videos} video(s) across {workspaces} workspace(s).")
    return 0 if all(bool(check["ok"]) for check in checks) else 1


def _pick_user(email: str | None) -> dict:
    profiles = config.local_user_profiles()
    if email:
        target = email.strip().lower()
        for profile in profiles:
            if str(profile.get("email", "")).lower() == target:
                return profile
        raise SystemExit(f"No local profile uses {email!r}.")
    if len(profiles) == 1:
        return profiles[0]
    raise SystemExit("Multiple profiles exist. Pass --user with the profile email.")


def _export(args: argparse.Namespace) -> int:
    profile = _pick_user(args.user)
    store = WorkspaceStore(str(profile["id"]))
    try:
        ws_dir = store.resolve(args.workspace)
    except StoreError as exc:
        raise SystemExit(str(exc)) from exc
    content = store.write_transcripts(ws_dir)
    if args.out:
        out = Path(args.out).expanduser()
    else:
        out = Path.cwd() / "transcripts.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out} ({len(content)} chars).")
    return 0


def _embed(args: argparse.Namespace) -> int:
    profile = _pick_user(args.user)
    user_id = str(profile["id"])
    llm_config = LlmConfig.for_user(user_id)
    if not llm_config.embedding_model:
        raise SystemExit("Set an embedding model in Settings first.")
    store = WorkspaceStore(user_id)
    if args.workspace:
        try:
            workspaces = [store.resolve(args.workspace)]
        except StoreError as exc:
            raise SystemExit(str(exc)) from exc
    else:
        workspaces = [store.resolve(str(item.get("id"))) for item in store.list_workspaces()]
    total = 0
    for ws_dir in workspaces:
        total += asyncio.run(
            ensure_workspace_embeddings(store, ws_dir, llm_config, force=args.force)
        )
    print(
        f"Embedded {total} chunk(s) with {llm_config.embedding_model} "
        f"in {len(workspaces)} workspace(s)."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yt-gpt", description="Ask questions across YouTube transcripts.")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the local web app")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--no-browser", action="store_true")
    serve.set_defaults(func=_serve)

    doctor = sub.add_parser("doctor", help="Check the environment")
    doctor.add_argument("--rebuild", action="store_true", help="Rebuild clean text, chunks and exports")
    doctor.set_defaults(func=_doctor)

    embed = sub.add_parser("embed", help="Build dense vectors for existing workspaces")
    embed.add_argument("workspace", nargs="?", default=None)
    embed.add_argument("--user", default=None, help="Profile email when several exist")
    embed.add_argument("--force", action="store_true", help="Re-embed all chunks")
    embed.set_defaults(func=_embed)

    export = sub.add_parser("export", help="Write a workspace transcript to markdown")
    export.add_argument("workspace")
    export.add_argument("--user", default=None, help="Profile email when several exist")
    export.add_argument("--out", default=None)
    export.set_defaults(func=_export)

    version = sub.add_parser("version", help="Print the version")
    version.set_defaults(func=lambda args: print(__version__) or 0)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["serve"]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
