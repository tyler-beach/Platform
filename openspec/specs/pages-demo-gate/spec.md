# pages-demo-gate Specification

## Purpose
Optional shared-passphrase gate for published GitHub Pages demos; scraper friction only, disabled when DEMO_GATE_PASSPHRASE is unset.
## Requirements
### Requirement: Optional shared-passphrase gate for Pages demos

When the Pages build is configured with a demo-gate passphrase secret, the published site MUST require that passphrase before showing the React app content and the standalone pathfinder-flow explorer. Successful unlock MUST persist for the browser session. When no passphrase is configured, the site MUST remain ungated.

#### Scenario: Configured gate blocks until passphrase matches
- **GIVEN** a Pages build with demo-gate enabled
- **AND** the browser session is not unlocked
- **WHEN** a visitor opens the site
- **THEN** a passphrase prompt is shown instead of the main demo content
- **AND** entering the correct passphrase unlocks the session and reveals the site

#### Scenario: Unconfigured builds stay open
- **GIVEN** a Pages or local build without a demo-gate passphrase
- **WHEN** the site loads
- **THEN** no passphrase prompt is required

