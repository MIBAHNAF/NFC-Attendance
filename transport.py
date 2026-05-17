import asyncio, threading, queue, serial
from serial.tools import list_ports

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    BleakScanner = BleakClient = None

HELLO = b"HELLO\r\n"
UART_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"


class BaseReader:
    def __init__(self, out_q: "queue.Queue[str]", logger=print):
        self.q = out_q
        self.log = logger            # ← all status routed through this

    def start(self):
        raise NotImplementedError()


# ---------- USB ----------
class USBReader(BaseReader):
    def __init__(self, out_q, logger=print):
        super().__init__(out_q, logger)
        self.ser = None

    def _find_port(self):
        for p in list_ports.comports():
            try:
                s = serial.Serial(p.device, 9600, timeout=2)
                if s.read(len(HELLO)) == HELLO:
                    self.ser = s
                    self.log(f"[USB] Connected on {p.device}")
                    break
                s.close()
            except (OSError, serial.SerialException):
                continue
        if not self.ser:
            self.log("[USB] No Arduino detected")

    def _worker(self):
        self._find_port()
        if not self.ser:
            return
        while True:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
            except serial.SerialException:
                break
            if line:
                self.q.put(line)

    def start(self):
        threading.Thread(target=self._worker, daemon=True).start()


# ---------- BLE ----------
class BleReader(BaseReader):
    def __init__(self, out_q, name_hint="DSD TECH", mac_hint=None, logger=print):
        super().__init__(out_q, logger)
        self.name = name_hint
        self.mac  = mac_hint
        self._buf = bytearray()

    async def _ble_main(self):
        if BleakScanner is None or BleakClient is None:
            self.log("[BLE] Not found - using USB")
            return

        self.log("[BLE] Scanning...")
        try:
            devs = await BleakScanner.discover(timeout=5)
        except OSError:
            self.log("[BLE] Not ready - using USB")
            return

        if self.mac:
            tgt = next((d for d in devs if d.address.lower() == self.mac.lower()), None)
        else:
            tgt = next((d for d in devs if (d.name or "").startswith(self.name)), None)
        if not tgt:
            self.log("[BLE] Not found - using USB")
            return

        self.log(f"[BLE] Connecting to {tgt.name} @ {tgt.address}")

        def handler(_, data: bytes):
            self._buf.extend(data)
            while b'\n' in self._buf:
                line, _, rest = self._buf.partition(b'\n')
                self._buf = bytearray(rest)
                s = line.strip(b'\r').decode(errors="ignore")
                if s:
                    self.q.put(s)

        try:
            async with BleakClient(tgt) as cli:
                await cli.start_notify(CHAR_UUID, handler)
                self.log("[BLE] Subscribed - streaming")
                while True:
                    await asyncio.sleep(3600)
        except OSError:
            self.log("[BLE] Connection failed - using USB")

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._ble_main())
        except Exception:
            self.log("[BLE] Disabled - using USB")
        finally:
            loop.close()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
