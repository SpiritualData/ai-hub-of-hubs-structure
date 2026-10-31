"""The deep-work runners: the arms of the act-in-the-world seat that hand open-ended work to a coding agent worker.

``launch`` is the pure argv builder, ``settings`` the frozen values a consumer hands in (timeouts, the usage-limit and prompt-budget
collaborators, the marker the worker prints when it escalates), ``contract`` the goal contract around any ``DeepRunner``, ``session``
the reading of the worker's own session record, ``subprocess_runner`` and ``stream_runner`` the two Claude Code runners, and the
``acp_*`` modules the Agent Client Protocol runner. Standard library plus ``esoi``; the ``acp`` package is imported inside one function.
Nothing here reads the environment: every setting is a constructor or function argument, and the hub never imports a consumer."""
