# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please follow the responsible disclosure process below.

### GitHub Private Vulnerability Reporting

This repository has [GitHub Private Vulnerability Reporting](https://github.com/D-sorganization/Programmatic-PID/security/advisories) enabled. You can report vulnerabilities directly through GitHub's Security Advisories feature.

### Email Disclosure

Alternatively, you may email the maintainers directly at the contact address listed in the repository profile.

### What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Impact**: The potential impact if exploited
- **Affected Versions**: Which versions are affected
- **Suggested Fix**: If you have a suggestion for remediation

### Response Timeline

- **Acknowledgment**: Within 48 hours of receiving your report
- **Initial Assessment**: Within 7 days
- **Fix and Disclosure**: Within 30 days, depending on severity and complexity

### Security Measures

This repository uses the following security practices:

- **Static Analysis**: `bandit` is run in CI to detect common Python security issues
- **Dependency Auditing**: `pip-audit` checks for known vulnerabilities in dependencies
- **Pre-commit Hooks**: Security-focused linting runs before each commit

Thank you for helping keep Programmatic-PID secure.