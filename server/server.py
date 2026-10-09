import asyncio
import os
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived
from aioquic.quic.configuration import QuicConfiguration

MAX_BODY = 1 << 20   # 1 MiB ceiling, guards against a malformed request


class H3Server(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http = H3Connection(self._quic)

    def quic_event_received(self, event):
        for h3_event in self._http.handle_event(event):
            if not isinstance(h3_event, HeadersReceived):
                continue
            headers = dict(h3_event.headers)
            path = headers.get(b":path", b"/").decode()
            if headers.get(b":method", b"GET") == b"GET":
                nbytes = 1024
                if "bytes=" in path:
                    try:
                        nbytes = int(path.split("bytes=")[1].split("&")[0])
                    except ValueError:
                        nbytes = 1024
                body = bytes(max(0, min(nbytes, MAX_BODY)))
            else:
                body = b"ok"
            self._http.send_headers(h3_event.stream_id, [(b":status", b"200")])
            self._http.send_data(h3_event.stream_id, body, end_stream=True)
            self.transmit()


async def main():
    strategy = os.environ.get("PAD_STRATEGY") or None
    target = int(os.environ.get("PAD_TARGET", "1000"))
    config = QuicConfiguration(
        is_client=False,
        alpn_protocols=["h3"],
        max_datagram_size=1350,
        max_data=16777216,
        max_stream_data=16777216,
        padding_strategy=strategy,
        padding_target=target,
    )
    config.load_cert_chain("/app/ssl_cert.pem", "/app/ssl_key.pem")
    print(f"server listening on 0.0.0.0:4433  "
          f"padding_strategy={strategy!r} padding_target={target}", flush=True)
    await serve("0.0.0.0", 4433, configuration=config, create_protocol=H3Server)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
