import asyncio
import json
import logging
from typing import Optional

import grpc

from .event_bus import subscribe, unsubscribe
from .grpc import realtime_pb2, realtime_pb2_grpc

logger = logging.getLogger(__name__)


class RealtimeService(realtime_pb2_grpc.RealtimeServicer):
    async def StreamEvents(self, request: realtime_pb2.SubscribeRequest, context: grpc.aio.ServicerContext):
        q = subscribe()
        try:
            while True:
                event = await q.get()
                # Optional filtering by type
                evt_type: Optional[str] = event.get('data', {}).get('type') or event.get('type')
                if request.filter_type and evt_type != request.filter_type:
                    continue
                payload_json = json.dumps(event.get('data', {}))
                yield realtime_pb2.Event(type=evt_type or '', payload_json=payload_json)
        except asyncio.CancelledError:
            raise
        finally:
            await unsubscribe(q)


async def serve_grpc(port: int = 50051):
    server = grpc.aio.server(options=[('grpc.max_send_message_length', 10 * 1024 * 1024)])
    realtime_pb2_grpc.add_RealtimeServicer_to_server(RealtimeService(), server)
    server.add_insecure_port(f'[::]:{port}')
    logger.info(f"gRPC server listening on {port}")
    await server.start()
    await server.wait_for_termination()

