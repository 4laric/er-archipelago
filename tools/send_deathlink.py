#!/usr/bin/env python3
"""Send a single DeathLink to an Archipelago room (solo test harness).

Requires:  pip install websockets
Preconditions:
  * your ER slot was generated with death_link enabled (client is_enabled() == true)
  * SOURCE below is NOT your slot name (the client ignores deathlinks sourced from itself)

Usage:  edit HOST/SLOT/GAME/PASSWORD/SOURCE below, then:  python send_deathlink.py
  - local server:      HOST = "localhost:38281"        (scheme ws://)
  - archipelago.gg:    HOST = "archipelago.gg:XXXXX"   (scheme wss://, auto-detected)
"""
import asyncio, json, ssl, sys, time
import websockets

HOST     = "localhost:38281"     # host:port of the AP room
SLOT     = "Alaric"             # YOUR slot name (connect as it; multiple conns per slot are allowed)
GAME     = "Elden Ring"          # must match the slot's game
PASSWORD = None                  # room password, or None
SOURCE   = "TestBot"             # shown as the killer; MUST differ from SLOT to beat the self-guard
AP_VER   = {"major": 0, "minor": 6, "build": 7, "class": "Version"}   # matches .ap-version 0.6.7


async def main():
    scheme = "wss" if not HOST.startswith(("localhost", "127.")) else "ws"
    uri = f"{scheme}://{HOST}"
    ctx = ssl._create_unverified_context() if scheme == "wss" else None
    async with websockets.connect(uri, ping_interval=None, ssl=ctx, max_size=None) as ws:
        await ws.recv()  # RoomInfo
        await ws.send(json.dumps([{
            "cmd": "Connect", "game": GAME, "name": SLOT, "password": PASSWORD,
            "uuid": "deathlink-tester", "version": AP_VER,
            "items_handling": 0, "tags": ["DeathLink", "Tracker"], "slot_data": False,
        }]))
        while True:
            for p in json.loads(await ws.recv()):
                if p.get("cmd") == "Connected":
                    await ws.send(json.dumps([{
                        "cmd": "Bounce", "tags": ["DeathLink"],
                        "data": {"time": time.time(), "source": SOURCE,
                                 "cause": f"{SOURCE} is testing keep-runes"},
                    }]))
                    print(f"DeathLink sent to room {HOST} as '{SOURCE}'.")
                    await asyncio.sleep(1)
                    return
                if p.get("cmd") == "ConnectionRefused":
                    print("Connection refused:", p.get("errors"), file=sys.stderr)
                    return


if __name__ == "__main__":
    asyncio.run(main())