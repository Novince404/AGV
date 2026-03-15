"""SQL-backed repository adapters.

In the current A3 phase these modules still proxy to memory-backed stores so
that runtime behavior stays unchanged while the backend shape is normalized.
The next stage will replace the proxies with real ORM-backed persistence.
"""
