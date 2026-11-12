"""``ahohs opencode-server``: the hub's session ``Harness`` served over the subset of opencode V2's HTTP API that the stock opencode terminal client needs, so that client (a separate program,
MIT, never vendored) draws a hub session. Modules: ``projection`` (the store a client reads and the event stream it follows), ``mapping`` (hub events to the client's events: pure), ``bridge``
(the run: starts, steers, stops, resumes, answers permissions), ``routes`` (the HTTP surface), ``server`` (the loopback HTTP server), ``client`` (launching and checking the client) and
``plugin/hub_session`` (the client plugin that shows what only the hub knows). Standard library only."""
