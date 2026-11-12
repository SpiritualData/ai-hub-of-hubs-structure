"""The polished arm of Terminal Experience (``terminal-session:polished_session``): a full-screen terminal with the settled rules of a polished screen, driven by the hub's own
session contract. ``words`` (the sentences), ``text`` (every rule as a plain function of a ``SessionView``), ``notices`` (warnings folded to one line), ``menu`` (the command menu),
``widgets`` and ``app`` (Textual, imported only when the screen is built) and ``session`` (the arm: the shared driver with the polished rules). Nothing here is imported at package
import, so a machine without the screen library loads the package."""
