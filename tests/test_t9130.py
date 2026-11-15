"""Advertisement handling of the Smart Scale C20 (T9130)."""

import asyncio
from types import SimpleNamespace

from eufylife_ble_client import EufyLifeBLEDevice

# Bytes 0-9 as sent by a C20 (device-specific, byte 6 counts up).
PREFIX = bytes.fromhex("0fb70052e600afb5f96a")


def packet(flags: int, kg: float = 0.0, heart_rate: int = 0, impedance: float = 0.0,
           counter: int = 0, flags2: int = 0) -> bytes:
    """C20 manufacturer data: data[10] flags, [12:14] weight, [15] HR, [17:19] impedance."""
    data = bytearray(PREFIX) + bytearray(8)
    data[6] = counter & 0xFF
    data[10] = flags
    data[11] = flags2
    data[12:14] = round(kg * 100).to_bytes(2, "little")
    data[15] = heart_rate
    data[17:19] = round(impedance * 10).to_bytes(2, "little")
    return bytes(data)


def adv(manufacturer_data: dict[int, bytes]) -> SimpleNamespace:
    return SimpleNamespace(manufacturer_data=manufacturer_data)


def run(steps):
    """Feed advertisements to a fresh client; return the states passed to callbacks."""
    async def _run():
        client = EufyLifeBLEDevice(model="eufy T9130")
        client._callbacks = []  # class attribute in the library: keep tests apart
        states = []
        client.register_callback(states.append)
        for manufacturer_data in steps:
            client.update_state_from_advertisement_data(adv(manufacturer_data))
        return client, states

    return asyncio.run(_run())


STALE = packet(0x01, kg=60.0, counter=1)  # live value left over from an earlier weighing


def test_first_advertisement_only_primes():
    """The first advertisement may be replayed from the cache: not evaluated."""
    _, states = run([{0x1111: packet(0x05, kg=80.0)}])
    assert states == []


def test_unchanged_advertisement_ignored():
    first = {0x1111: packet(0x01, kg=10.0)}
    _, states = run([first, {0x1111: packet(0x01, kg=79.0, counter=2)}, {0x1111: packet(0x01, kg=79.0, counter=2)}])
    assert [s.weight_kg for s in states] == [79.0]


def test_stale_entry_not_taken():
    """Second weighing on 15.11.2026: an old entry stays in the merged dict."""
    steps = [
        {0x1111: STALE},
        {0x1111: STALE, 0x2222: packet(0x01, kg=79.5, counter=10)},
        {0x1111: STALE, 0x2222: packet(0x01, kg=80.0, counter=11)},
        {0x1111: STALE, 0x2222: packet(0x05, kg=80.0, counter=12)},
    ]
    client, states = run(steps)
    assert [s.weight_kg for s in states] == [79.5, 80.0, 80.0]
    assert client.state.final_weight_kg == 80.0


def test_final_with_other_flag_bits():
    """Flags 0x15 / 0x25 seen on 15.11.2026 were dropped by the old allow-list."""
    steps = [
        {0x1111: STALE},
        {0x1111: STALE, 0x2222: packet(0x15, kg=80.0, counter=20)},
    ]
    client, _ = run(steps)
    assert client.state.final_weight_kg == 80.0


def test_heart_rate_and_impedance():
    """Layout as documented: 0x80 heart rate in data[15], 0x40 impedance in data[17:19]."""
    steps = [
        {0x1111: packet(0x01, kg=10.0)},
        {0x1111: packet(0x65, kg=80.0, impedance=512.3, counter=1)},
        {0x1111: packet(0xA5, kg=80.0, heart_rate=72, counter=2)},
    ]
    _, states = run(steps)
    assert states[0].final_weight_kg == 80.0 and states[0].impedance == 512.3
    assert states[1].heart_rate == 72 and states[1].impedance is None
