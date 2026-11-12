"""Third-party code kept as its authors wrote it, one folder per source, each with its licence text and a README that says what was taken and what was cut. The structure rules treat a folder named
``vendor`` as third-party (no module docstring or port rule is asked of it), and the import boundary test lets only the libraries its source needs be imported at module level there. Nothing in a
vendor folder is imported when the hub package is imported: the arm that uses it loads it inside a function."""
