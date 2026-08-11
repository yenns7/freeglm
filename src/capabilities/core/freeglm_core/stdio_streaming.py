"""Low-memory stdio transport for the MCP server.

Drop-in replacement for `mcp.server.stdio.stdio_server`. Large tool results
(image blocks exceeding a threshold) are serialized block-by-block so peak
memory stays near one frame. All other messages take the standard SDK path.
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from io import TextIOWrapper

import anyio
import mcp.types as types
from mcp.shared.message import SessionMessage

from shared.env import STREAM_THRESHOLD

# Stream manually once image payload exceeds STREAM_THRESHOLD bytes.
_CHUNK = 64 * 1024


def _j(obj) -> str:
    # ensure_ascii=False matches pydantic's UTF-8 output.
    return json.dumps(obj, ensure_ascii=False)


def _streamable_result(root) -> bool:
    """True if this is a tool response big enough to warrant block-by-block streaming."""
    if not isinstance(root, types.JSONRPCResponse):
        return False
    content = root.result.get("content")
    if not isinstance(content, list):
        return False
    total = 0
    for b in content:
        if isinstance(b, dict) and b.get("type") == "image":
            total += len(b.get("data", ""))
            if total >= STREAM_THRESHOLD:
                return True
    return False


@asynccontextmanager
async def streaming_stdio_server():
    stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))
    stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    async def stdin_reader():
        try:
            async with read_stream_writer:
                async for line in stdin:
                    try:
                        message = types.JSONRPCMessage.model_validate_json(line)
                    except Exception as exc:
                        await read_stream_writer.send(exc)
                        continue
                    await read_stream_writer.send(SessionMessage(message))
        except anyio.ClosedResourceError:
            await anyio.lowlevel.checkpoint()

    async def _stream_result(root) -> None:
        """Serialize a JSONRPCResponse block-by-block through a small buffer."""
        buf: list[str] = []
        buflen = 0

        async def emit(s: str) -> None:
            nonlocal buflen
            buf.append(s)
            buflen += len(s)
            if buflen >= _CHUNK:
                await stdout.write("".join(buf))
                buf.clear()
                buflen = 0

        await emit('{"jsonrpc":"2.0","id":' + _j(root.id) + ',"result":{')
        first = True
        for k, v in root.result.items():
            await emit("" if first else ",")
            first = False
            await emit(_j(k) + ":")
            if k == "content" and isinstance(v, list):
                await emit("[")
                for i, block in enumerate(v):
                    await emit("" if i == 0 else ",")
                    await emit(_j(block))  # one block at a time — caps peak
                await emit("]")
            else:
                await emit(_j(v))
        await emit("}}\n")
        if buf:
            await stdout.write("".join(buf))

    async def stdout_writer():
        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    root = session_message.message.root
                    if _streamable_result(root):
                        await _stream_result(root)
                    else:
                        data = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                        await stdout.write(data + "\n")
                    await stdout.flush()
        except anyio.ClosedResourceError:
            await anyio.lowlevel.checkpoint()

    async with anyio.create_task_group() as tg:
        tg.start_soon(stdin_reader)
        tg.start_soon(stdout_writer)
        yield read_stream, write_stream
