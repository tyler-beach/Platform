## Specification and tests

- [x] 1.1 Add RED-first tests for same-origin snapshot credentials, cross-origin rejection, and credential-free GitHub API requests.

## Implementation

- [x] 2.1 Implement the same-origin JSON fetch boundary with bounded, explicit request options.
- [x] 2.2 Use it for both synthetic and internal static JSON snapshots.

## Verification

- [x] 3.1 Demonstrate RED then GREEN and run browser-core tests.
- [x] 3.2 Run the deterministic suite, strict MkDocs build, and OpenSpec validation.
- [x] 3.3 Verify the API adapter still omits browser credentials and no cross-origin snapshot is fetched.
