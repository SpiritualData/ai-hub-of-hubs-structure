"""The act-in-the-world seat: the arms that change something outside the model (edit files, call a write operation of an MCP
server) and the helpers they share (edit-block parsing, an MCP protocol client). Standard library plus ``esoi``; vendor libraries
(``mcp``) are imported inside functions, from the per-arm extras. Nothing here reads the environment or knows a consumer."""
