# src/clients/ — resilient clients for free external APIs.
#
# Design rule: external APIs MUST NOT be able to crash the pipeline.
# Every client returns an empty list / None on any failure (timeout, HTTP
# error, missing key, malformed payload) and logs a warning instead of
# raising. The core TK-Shield pipeline runs fully offline without any of
# these sources available.
