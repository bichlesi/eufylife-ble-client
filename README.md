# EufyLife BLE Client

This is a library for parsing data from Eufy smart scales that use the EufyLife mobile app.

## This fork

Used by the Home Assistant integration in `bichlesi/eufylife-ble` (install
pinned to a tag of this repository).

* Heart rate and impedance for the Smart Scale C20 (T9130).
* 0.1.12: with several manufacturer data entries (Home Assistant merges them
  over all advertisements), only entries that changed since the previous
  advertisement are evaluated; the first advertisement after start only
  primes the comparison. Before, an entry left over from an earlier weighing
  could win and the new weighing was lost.

* 0.1.13: impedance also with the scale's heart rate measurement switched
  off. Then the C20 sends it in packets flagged `0x25` (no `0x40`), at the
  same position (bytes 17-18, 0.1 Ω).

C20 (T9130) advertisement, byte 10 flags: `0x01` weight, `0x04` final
weight, `0x40` impedance, `0x80` heart rate (heart rate measurement on:
`0x65`, `0xA5`); `0x20` without `0x40`/`0x80` carries the impedance when
heart rate measurement is off. Bytes 12-13 weight (LE, 10 g), byte 15 heart
rate (bpm), bytes 17-18 impedance (LE, 0.1 Ω).

Tests: `pip install . pytest && python -m pytest tests`.

# Supported Models

| Model | Name               |
| ----- | ------------------ |
| T9120 | Smart Scale A1     |
| T9130 | Smart Scale C20    |
| T9140 | Smart Scale        |
| T9146 | Smart Scale C1     |
| T9147 | Smart Scale P1     |
| T9148 | Smart Scale P2     |
| T9149 | Smart Scale P2 Pro |
| T9150 | Smart Scale P3     |

## Installation

Install this via pip:

`pip install eufylife-ble-client`
