# orientation: does the view put a reader in the right part of the code?

A free proxy, with no model. The cases are the 63 file-finding tasks of `cards_from_files`; each asks for the neighbourhood of its one
file. A case passes (`folder_hit`) when one of the first three files of the view is in the target's own folder. `area_hit` counts the
cases where the first card's files have a common folder that is the target's folder or its parent (never the root). It measures
nearness, not that a reader found the file, and it favours a card per file because the target is one file; read it beside `needed_set`,
not instead of it. The corpus, the single build per run and the fixed selector are those of `cards_from_files`.
