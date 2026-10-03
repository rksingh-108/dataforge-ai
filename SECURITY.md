# Security Policy

DataForge AI handles customer business data, database credentials and AI
executions. We take security reports seriously and we will not penalise anyone who
reports a problem responsibly.

## Reporting a vulnerability

**Do not open a public issue, PR or discussion for a security vulnerability.**

Report privately using **either**:

- GitHub's private vulnerability reporting: *Security → Report a vulnerability* on
  this repository, or
- Email: **security@dataforge.example** (PGP key on request).

Please include:

1. What the issue is and where (component, endpoint, file if known).
2. Steps to reproduce, ideally a minimal proof of concept.
3. The realistic impact — what an attacker gains.
4. Any authentication/role needed to reach it.
5. Whether you intend to disclose publicly and on what timeline.
6. A way to contact you.

Redact any real customer data, credentials or tokens from screenshots and logs.

## What to expect

| Stage | Target |
| ----- | ------ |
| Acknowledgement | 2 business days |
| Initial assessment (severity + validity) | 5 business days |
| Fix or mitigation plan for High/Critical | 7 days |
| Fix or mitigation plan for Medium | 30 days |
| Coordinated disclosure | By agreement, default 90 days after the fix |

We will keep you informed, credit you in the advisory if you wish, and tell you
honestly if we do not consider the report a vulnerability — including our reasoning.

## In scope

- Cross-tenant data exposure (the highest-severity class here).
- Authentication bypass, session or token weaknesses.
- Privilege escalation; missing or incorrect authorization checks.
- SQL injection or a bypass of the read-only query validator.
- SSRF reaching internal or cloud-metadata addresses.
- Prompt-injection paths that cause an unsafe *effect* (not merely a wrong answer).
- Credential disclosure (stored credentials, secrets, tokens).
- File-upload validation bypass.
- Remote code execution.

## Out of scope (without a demonstrated impact)

- Missing security headers with no exploit path (we track these as gaps).
- Rate limiting that can be bypassed by distributing requests.
- Vulnerabilities in third-party services we do not control.
- Social engineering, physical attacks, or denial of service by brute volume.
- Automated scanner output without a demonstrated impact.
- Reports based only on version strings.
- The absence of a feature we have documented as not implemented
  (see [docs/development/known-limitations.md](docs/development/known-limitations.md)).

## Our commitments

- We disclose known limitations publicly rather than hiding them: see
  [docs/development/known-limitations.md](docs/development/known-limitations.md)
  and [security/vulnerability-management/README.md](security/vulnerability-management/README.md).
- We do not claim a control exists unless it is implemented and tested. Every
  control in [security/README.md](security/README.md) names the test that proves it.
- We do not pursue legal action against researchers acting in good faith under this
  policy.

## For contributors

If you find a security issue while working on the codebase:

1. Do not fix it in a public PR with a detailed description.
2. Contact the security owner listed in [CODEOWNERS](.github/CODEOWNERS) privately.
3. If a fix is straightforward, prepare `security/<description>` branch and a
   regression test, and coordinate the PR with the security owner.

Security-relevant changes require a security-owner approval before merge. See
[security/policies/README.md](security/policies/README.md) for the engineering
rules and [security/security-testing/README.md](security/security-testing/README.md)
for how to write the test.
