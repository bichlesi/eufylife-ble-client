"""Advertisement handling of the Smart Scale C20 (T9130)."""

import asyncio
from types import SimpleNamespace

from eufylife_ble_client import EufyLifeBLEDevice

# Bytes 0-9 (device-specific in real packets; byte 6 counts up). Neutral
# values here: no data of a real device or person in this repository.
PREFIX = bytes.fromhex("0f0102030400a0b0c0d0")


def packet(flags: int, kg: float = 0.0, heart_rate: int = 0, impedance: float = 0.0,
           counter: int = 0, flags2: int = 0, length: int = 18) -> bytes:
    """C20 manufacturer data: data[10] flags, [12:14] weight, [15] HR, [17:19] impedance."""
    data = bytearray(PREFIX) + bytearray(length - len(PREFIX))
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


def test_impedance_without_heart_rate_measurement():
    """Heart rate measurement off (sequence seen on 15.11.2026, values made up).

    Live 0x01, final 0x05, 0x15, then 0x25 with the impedance (no 0x40 flag),
    0x25 with 0x80 in byte 11 (24 bytes), and 0x0d/0x40 when the scale turns off.
    """
    steps = [
        {0x1111: packet(0x00)},
        {0x1111: packet(0x01, kg=70.0, counter=1)},
        {0x1111: packet(0x01, kg=80.0, counter=2)},
        {0x1111: packet(0x05, kg=80.0, counter=3)},
        {0x1111: packet(0x15, kg=80.0, counter=4)},
        {0x1111: packet(0x25, kg=80.0, impedance=420.5, counter=5, length=24)},
        {0x1111: packet(0x25, kg=80.0, impedance=420.5, counter=5, flags2=0x80, length=24)},
        {0x1111: packet(0x0D, counter=6, flags2=0x40)},
    ]
    _, states = run(steps)
    finals = [s for s in states if s.final_weight_kg is not None]
    assert {s.final_weight_kg for s in finals} == {80.0}
    assert [s.impedance for s in finals if s.impedance is not None] == [420.5]  # same state twice: one callback
    assert all(s.heart_rate is None for s in states)
    assert states[-1].weight_kg is None and states[-1].impedance is None


def test_heart_rate_packet_does_not_give_impedance():
    """0xA5 (heart rate) keeps ignoring bytes 17-18, as before."""
    steps = [
        {0x1111: packet(0x01, kg=10.0)},
        {0x1111: packet(0xA5, kg=80.0, heart_rate=70, impedance=999.9, counter=1)},
    ]
    _, states = run(steps)
    assert states[-1].heart_rate == 70 and states[-1].impedance is None
