"""The reasoning loop's generic machinery: the pieces of a bounded plan, gather, re-plan, answer, deep or confirm loop that
carry no consumer wording.

Prompt text, tool vocabularies and settings are the consumer's: it passes them in and keeps its own copies. Standard library
only; nothing here reads the environment or imports a consumer.
"""
