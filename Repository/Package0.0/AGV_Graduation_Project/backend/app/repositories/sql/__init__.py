"""SQL-backed repository adapters.

These modules provide an ORM-backed persistence layer while preserving the
current service-facing repository API. In the current A3 phase they keep an
in-process cache of model objects so the existing mutation-heavy service code
can continue to work during the migration from memory storage to SQL storage.
"""
