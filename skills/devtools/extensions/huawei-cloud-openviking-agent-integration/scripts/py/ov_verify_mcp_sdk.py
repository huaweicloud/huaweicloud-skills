#!/usr/bin/env python3
"""ov_verify_mcp_sdk.py — MCP endpoint verification using the official MCP Python SDK.

Replaces the hand-rolled multi-POST curl implementation in verify_mcp.sh with a
single-session Streamable HTTP client (mcp.client.streamable_http.streamable_http_client
+ mcp.ClientSession). One HTTP session carries initialize -> initialized ->
tools/list -> tools/call(health), which matches the streamable-http transport
semantics the OpenViking server expects.

Usage:
    ov_verify_mcp_sdk.py <mcp_url> [--api-key KEY]

Output (stdout):
    SERVER:<name>
    VERSION:<version>
    PROTOCOL:<protocol>
    TOOLS:<count>
    TOOL:<name>:<description-first-80>
    HEALTH:<text-result>

Exit codes:
    0   handshake + health tool call succeeded
    1   handshake/tool failure (details on stderr)
    2   mcp SDK not installed / unknown cli error
"""
import argparse
import asyncio
import sys

def err(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)

def _flatten_exc(e):
    """Recursively unwrap ExceptionGroup to reach leaf errors."""
    subs = getattr(e, "exceptions", [])
    if subs:
        for s in subs:
            yield from _flatten_exc(s)
    else:
        yield e

async def run_verify(url, api_key):
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        import httpx2  # SDK 2.x transport backend
    except ImportError as e:
        err(f"MCP Python SDK not available: {e}")
        # ISSUE-016: the streamable-http transport + httpx2 backend used here
        # requires the 2.x SDK line — 1.x never worked with this code path
        err("Install it with: pip install --upgrade 'mcp>=2.0'")
        return 2

    http_client = None
    try:
        if api_key:
            http_client = httpx2.AsyncClient(
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=httpx2.Timeout(30.0),
            )
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                # 1) initialize
                init = await session.initialize()
                # SDK <2.2 used camelCase (serverInfo/protocolVersion); 2.2+ uses
                # snake_case (server_info/protocol_version). Tolerate both.
                si = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
                proto = getattr(init, "protocol_version", None) or getattr(init, "protocolVersion", None)
                if si is None:
                    raise RuntimeError(f"initialize response has no server_info: {init!r}")
                print(f"SERVER:{si.name}")
                print(f"VERSION:{si.version}")
                print(f"PROTOCOL:{proto}")

                # 2) initialized notification is sent automatically by the SDK.

                # 3) tools/list
                tools_result = await session.list_tools()
                tools = list(tools_result.tools)
                print(f"TOOLS:{len(tools)}")
                for t in tools:
                    desc = (getattr(t, "description", "") or "").splitlines()[0][:80]
                    print(f"TOOL:{t.name}:{desc}")

                # 4) tools/call health
                health = await session.call_tool("health", {})
                if hasattr(health, "content"):
                    texts = [
                        c.text for c in health.content
                        if getattr(c, "type", None) == "text"
                    ]
                    result_text = "\n".join(texts) if texts else str(health)
                else:
                    result_text = str(health)
                print(f"HEALTH:{result_text[:200]}")
                return 0
    except Exception as e:
        err(f"MCP verification failed: {type(e).__name__}: {str(e)[:200]}")
        for leaf in _flatten_exc(e):
            err(f"  cause: {type(leaf).__name__}: {str(leaf)[:300]}")
        return 1
    finally:
        if http_client is not None:
            await http_client.aclose()

def main():
    parser = argparse.ArgumentParser(description="Verify OpenViking MCP endpoint with official SDK")
    parser.add_argument("mcp_url", help="MCP endpoint URL, e.g. http://127.0.0.1:1933/mcp")
    parser.add_argument("--api-key", default="", help="Bearer API key (dev mode needs none)")
    args = parser.parse_args()
    try:
        rc = asyncio.run(run_verify(args.mcp_url, args.api_key or None))
    except KeyboardInterrupt:
        err("interrupted")
        rc = 1
    sys.exit(rc)

if __name__ == "__main__":
    main()