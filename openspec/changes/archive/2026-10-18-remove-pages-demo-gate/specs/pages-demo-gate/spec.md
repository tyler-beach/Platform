## REMOVED Requirements

### Requirement: Optional shared-passphrase gate for Pages demos

**Reason**: Client-side shared passphrase is not meaningful protection (hash is public in the build; unlock is only a session flag). Operating it is not worth the hassle.

#### Scenario: Pages demo loads without passphrase prompt
- **GIVEN** the published GitHub Pages site
- **WHEN** a visitor opens the React app or pathfinder-flow explorer
- **THEN** no shared-passphrase unlock form is required
