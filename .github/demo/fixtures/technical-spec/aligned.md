# Technical specification — Assessment request path

## Requirement SPEC-R-001

The request handler MUST enqueue assessment work to the asynchronous workflow and return a job identifier.

## Operational note

A worker performs the external provider call after job acceptance.
