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
