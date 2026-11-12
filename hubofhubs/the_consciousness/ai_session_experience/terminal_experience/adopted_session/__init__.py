"""The adopted arm of Terminal Experience (``terminal-session:adopted_session``): the shared session driver drawn on a full-screen interface adopted from an existing open-source terminal agent
(the Textual interface of Mistral Vibe v2.26.1, vendored beside this folder in ``vendor/mistral_vibe_ui``). ``adapter`` turns the hub's session events into the typed entries that interface is
driven by, ``app`` is the thin binding layer that composes its widgets (a Textual application, built only when it is needed), ``words`` holds the hub's own sentences and ``session`` is the arm.
Nothing here is imported at package import, so a machine without the screen libraries loads the package."""
