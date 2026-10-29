"""Ports: the neutral Protocols and helpers a consumer's core codes against. Importing them runs nothing; they know no consumer.

Each module was moved out of a consumer's core; the consumer re-exports its names at the old paths.

The Protocols are written ``typing.Protocol`` like the seats in ``hubofhubs.seats``: esoi's port scan (S7) does not read intent-mode solutions."""
