# ble_stream.py
import asyncio
import struct
from typing import Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# === CONFIG: set your target info here ===
TARGET_NAME = "BionodeWavelet"               # or set to None to match by address
TARGET_ADDRESS: Optional[str] = None      # e.g. "AA:BB:CC:DD:EE:FF" - takes precedence if set
SERVICE_UUID = "80ea98d0-bf05-4d48-92e4-f16b33600320"     # replace with your custom service UUID
CHAR_UUID = "91fd3072-5f44-4038-85d7-b807e11b5121"        # replace with your custom characteristic UUID
RECONNECT_DELAY = 3.0

# === utility: decode incoming bytes to something meaningful ===
def decode_packet(data: bytearray) -> str:
    """
    Example decoder: interpret first two bytes as unsigned short,
    next 4 bytes as float (little-endian). Adjust to your protocol.
    """
    try:
        if len(data) >= 6:
            x, y = struct.unpack_from("<Hf", data, 0)  # < = little-endian
            return f"counter={x}, value={y:.3f}, raw={data.hex()}"
        else:
            return f"raw={data.hex()}"
    except struct.error:
        return f"unparsable raw={data.hex()}"

# === notification handler ===
def notification_handler(sender: int, data: bytearray):
    # sender is the characteristic handle or UUID (library-dependent)
    decoded = decode_packet(data)
    print(f"[NOTIF] {sender}: {decoded}")

# === find device (by address or name) ===
async def find_device() -> Optional[str]:
    if TARGET_ADDRESS:
        return TARGET_ADDRESS

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    print("DEVICES:\n\n", devices)
    for d in devices:
        if d.name and TARGET_NAME and TARGET_NAME in d.name:
            print(f"Found target by name: {d.name} ({d.address})")
            return d.address
    print("Target device not found during scan.")
    return None

# === connect & subscribe loop (with reconnection) ===
async def run():
    address = await find_device()
    if not address:
        print("No device address found; exiting.")
        return

    while True:
        try:
            print(f"Attempting to connect to {address} ...")
            async with BleakClient(address) as client:
                print("Connected." if client.is_connected else "Failed to connect.")

                # optional: check service/characteristic presence
                if SERVICE_UUID not in [s.uuid for s in client.services]:
                    print(f"Warning: Service {SERVICE_UUID} not found on device.")
                # start notify
                await client.start_notify(CHAR_UUID, notification_handler)
                print(f"Subscribed to notifications on {CHAR_UUID}. Press Ctrl+C to stop.")

                # wait until disconnected or interruption
                while client.is_connected:
                    await asyncio.sleep(1.0)

                print("Disconnected from device.")
        except (BleakError, OSError) as e:
            print(f"Connection error: {e!r}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Unexpected error: {e!r}")

        # reconnect delay
        print(f"Reconnecting in {RECONNECT_DELAY} seconds...")
        await asyncio.sleep(RECONNECT_DELAY)

# === entrypoint with graceful shutdown ===
def main():
    loop = asyncio.get_event_loop()
    task = loop.create_task(run())
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        print("Keyboard interrupt received — shutting down...")
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
    finally:
        loop.close()
        print("Exited.")

if __name__ == "__main__":
    main()
