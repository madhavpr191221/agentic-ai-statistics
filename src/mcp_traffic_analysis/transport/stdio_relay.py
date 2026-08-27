"""Transparent stdio relay that records exact JSON-RPC frame sizes and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID, uuid4

from mcp_traffic_analysis.measurement.transport_models import (
    FrameDirection,
    FrameMessageType,
    TransportFrame,
)


def _parse_frame(
    payload: bytes,
) -> tuple[FrameMessageType, str | int | None, str | None, UUID | None]:
    try:
        message: dict[str, Any] = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return FrameMessageType.MALFORMED, None, None, None
    message_id = message.get("id")
    jsonrpc_id = message_id if isinstance(message_id, (str, int)) else None
    method = message.get("method") if isinstance(message.get("method"), str) else None
    if method is not None and jsonrpc_id is None:
        message_type = FrameMessageType.NOTIFICATION
    elif method is not None:
        message_type = FrameMessageType.REQUEST
    else:
        message_type = FrameMessageType.RESPONSE
    call_id: UUID | None = None
    params = message.get("params")
    meta = params.get("_meta", {}) if isinstance(params, dict) else {}
    raw_call_id = meta.get("call_id") if isinstance(meta, dict) else None
    if isinstance(raw_call_id, str):
        try:
            call_id = UUID(raw_call_id)
        except ValueError:
            pass
    return message_type, jsonrpc_id, method, call_id


class FrameWriter:
    def __init__(self, path: Path, run_id: UUID) -> None:
        self.path = path
        self.run_id = run_id
        self._sequence = 0
        self._lock = threading.Lock()
        self._requests: dict[str | int, tuple[str | None, UUID | None]] = {}

    def record(self, raw_frame: bytes, direction: FrameDirection) -> None:
        payload = raw_frame.rstrip(b"\r\n")
        delimiter_bytes = len(raw_frame) - len(payload)
        message_type, jsonrpc_id, method, call_id = _parse_frame(payload)
        with self._lock:
            if direction is FrameDirection.CLIENT_TO_SERVER and jsonrpc_id is not None:
                self._requests[jsonrpc_id] = (method, call_id)
            elif direction is FrameDirection.SERVER_TO_CLIENT and jsonrpc_id in self._requests:
                method, call_id = self._requests[jsonrpc_id]
            frame = TransportFrame(
                frame_id=uuid4(),
                run_id=self.run_id,
                sequence_number=self._sequence,
                wall_time_utc=datetime.now(UTC),
                monotonic_time_ns=time.monotonic_ns(),
                direction=direction,
                message_type=message_type,
                jsonrpc_id=jsonrpc_id,
                mcp_method=method,
                call_id=call_id,
                payload_bytes=len(payload),
                frame_bytes=len(raw_frame),
                delimiter_bytes=delimiter_bytes,
                payload_sha256=hashlib.sha256(payload).hexdigest(),
            )
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(frame.model_dump_json() + "\n")
                handle.flush()
            self._sequence += 1


def _pump(
    source: BinaryIO,
    destination: BinaryIO,
    recorder: FrameWriter,
    direction: FrameDirection,
) -> None:
    try:
        while raw_frame := source.readline():
            recorder.record(raw_frame, direction)
            destination.write(raw_frame)
            destination.flush()
    finally:
        try:
            destination.close()
        except OSError:
            pass


def relay(args: argparse.Namespace) -> int:
    child_args = (
        list(args.server_arg)
        if args.server_arg
        else ["--manifest", str(args.manifest), "--events", str(args.events)]
    )
    process = subprocess.Popen(
        [
            args.python,
            "-m",
            args.server_module,
            *child_args,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("stdio server pipes were not created")
    recorder = FrameWriter(args.frames, UUID(args.run_id))
    client_to_server = threading.Thread(
        target=_pump,
        args=(sys.stdin.buffer, process.stdin, recorder, FrameDirection.CLIENT_TO_SERVER),
        daemon=True,
    )
    server_to_client = threading.Thread(
        target=_pump,
        args=(process.stdout, sys.stdout.buffer, recorder, FrameDirection.SERVER_TO_CLIENT),
        daemon=True,
    )
    client_to_server.start()
    server_to_client.start()
    client_to_server.join()
    server_to_client.join()
    return process.wait()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument(
        "--server-module",
        default="mcp_traffic_analysis.fixtures.stdio_server",
        help="Python module launched behind the transparent relay.",
    )
    parser.add_argument(
        "--server-arg",
        action="append",
        default=[],
        help="One argument passed to the child server; repeat for multiple arguments.",
    )
    return parser


def main() -> int:
    return relay(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
