import asyncio
import os
import random
import ssl
import sys
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration

SERVER = "172.16.0.2"
PORT = 4433
FLOW_TIMEOUT = 300      # seconds; a flow exceeding this is treated as failed

# Requests per flow (N_REQ). Calibrated once during the Phase 9 rehearsal, 
# then fixed. Each request adds one draw from the class distribution, so a 
# high count makes every flow's size statistics an almost exact description of 
# its class, the classes separate perfectly, and no padding effect can 
# register against the ceiling. At N_REQ = 1000 the baseline wf1_mean reached 
# 0.990 and at 80 it became 0.895. Full calibration process is in Appendix C
N_REQ = 80
LO, HI = 120, 1080


class H3Client(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http = H3Connection(self._quic)
        self._waiters = {}

    def quic_event_received(self, event):
        for h3_event in self._http.handle_event(event):
            sid = getattr(h3_event, "stream_id", None)
            if sid not in self._waiters:
                continue
            fut, buf = self._waiters[sid]
            if isinstance(h3_event, DataReceived):
                buf.extend(h3_event.data)
                if h3_event.stream_ended and not fut.done():
                    fut.set_result(bytes(buf))
            elif isinstance(h3_event, HeadersReceived) and h3_event.stream_ended:
                if not fut.done():
                    fut.set_result(bytes(buf))

    async def get(self, path):
        sid = self._quic.get_next_available_stream_id()
        fut = asyncio.get_event_loop().create_future()
        self._waiters[sid] = (fut, bytearray())
        self._http.send_headers(sid, [
            (b":method", b"GET"),
            (b":scheme", b"https"),
            (b":authority", b"quic-server"),
            (b":path", path.encode()),
        ], end_stream=True)
        self.transmit()
        return await fut


def _clip(n):
    return max(LO, min(HI, int(n)))


async def _run(c, sizes):
    for n in sizes:
        await c.get(f"/get?bytes={_clip(n)}")


async def narrow(c):
    await _run(c, [random.gauss(600, 60) for _ in range(N_REQ)])


async def bimodal(c):
    await _run(c, [random.gauss(300, 60) if random.random() < 0.5
                   else random.gauss(900, 60) for _ in range(N_REQ)])


async def spread(c):
    await _run(c, [random.uniform(LO, HI) for _ in range(N_REQ)])


async def right_skew(c):
    await _run(c, [LO + random.expovariate(1 / 480) for _ in range(N_REQ)])


async def left_skew(c):
    await _run(c, [HI - random.expovariate(1 / 480) for _ in range(N_REQ)])


PROFILES = {"narrow": narrow, "bimodal": bimodal, "spread": spread,
            "right_skew": right_skew, "left_skew": left_skew}


async def main(name):
    config = QuicConfiguration(
        is_client=True,
        alpn_protocols=["h3"],
        verify_mode=ssl.CERT_NONE,
        max_datagram_size=1350,
        max_data=16777216,
        max_stream_data=16777216,
        padding_strategy=os.environ.get("PAD_STRATEGY") or None,
        padding_target=int(os.environ.get("PAD_TARGET", "1000")),
    )
    secrets = os.environ.get("SSLKEYLOGFILE")
    if secrets:
        # Line-buffered, so the keys reach disk as they are written instead of
        # on process exit. Phase 11 reads this file.
        config.secrets_log_file = open(secrets, "a", buffering=1)
    async with connect(SERVER, PORT, configuration=config,
                       create_protocol=H3Client) as client:
        await client.wait_connected()
        await PROFILES[name](client)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PROFILES:
        sys.exit(f"usage: client.py <{'|'.join(PROFILES)}>")
    try:
        asyncio.run(asyncio.wait_for(main(sys.argv[1]), FLOW_TIMEOUT))
    except asyncio.TimeoutError:
        sys.exit(f"flow timed out after {FLOW_TIMEOUT}s")
