"""
mcp_server/tools/streaming_tools

streaminges and abortinges tool
"""
import asyncio
from utils.logger import get_logger
import uuid

logger = get_logger("mcp.streaming_tools")

# In-memory registery for active streams
# 🎈 for prod/scalability redis shud be used to manage this
active_streams={}

def is_valid_stream_id(stream_id)->bool:
    try:
        uuid.UUID(str(stream_id))
        return True
    except Exception as e:
        logger.error(f"stream_id validation failed with error: {str(e)}")
        return False

async def streaminges(args,stream):
    """
    Intake agent starts consuming stream from db/externalsource for now mock faker stream reusable function to replicate the same

    Further Streams incremental output (e.g., logs/events/processing) of the Intake Agent and other agents to the client i.e electron app via minmal golang fiber streaming microservice.
    Args must include a unique 'stream_id' for control.
    """
    stream_id = args.get("stream_id")
    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    active_streams[stream_id] = True
    try:
        for i in range(100):
            # check if stream is still active
            if not active_streams.get(stream_id):
                logger.info(f"Stream {stream_id} aborted at iteration {i}")
                break
            log_event = {"event": "log", "stream_id": stream_id, "message": f"processing {i}"}
            logger.debug(f"Stream {stream_id} event: {log_event}")
            await stream.send(log_event)
            await asyncio.sleep(0.1) # give control back to event loop to avoid indefinate event loop blocking
        logger.info(f"Stream {stream_id} completed")
        return {"done": True, "stream_id": stream_id}
    finally:
        active_streams.pop(stream_id,None)
        logger.info(f"Stream {stream_id} cleaned up")

async def abortinges(args,stream,context):
    """
    Aborts a running stream/process by stream_id.
    i.e the Intake agent stops taking stream and all agents stop processing transactions and the golang fiber microservice stop streaming log/events to electron app
    """
    stream_id = args.get("stream_id")
    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        return {"error": msg}
    if stream_id in active_streams:
        active_streams[stream_id] = False
        logger.info(f"Aborted stream {stream_id}")
        return {"aborted": True, "stream_id": stream_id}
    else:
        logger.warning(f"Tried to abort non-existent stream {stream_id}")
        return {"error": "No such stream", "stream_id": stream_id}