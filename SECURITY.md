# Security Policy

## Supported versions

Security fixes target the latest release and the current `main` branch. Older
versions may not receive fixes, so please confirm the issue against a current
version when practical.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability.

Use [GitHub private vulnerability reporting](https://github.com/yenns7/freeglm/security/advisories/new)
to send the maintainers:

- the affected version or commit;
- the impact and conditions required to reproduce it;
- a minimal proof of concept, if available; and
- any suggested mitigation or fix.

Remove API keys, credentials, private media, and other sensitive data from the
report. If private vulnerability reporting is unavailable, open a public issue
without vulnerability details and ask the maintainers to arrange a private
reporting channel.

The maintainers will acknowledge the report, investigate it, and coordinate a
fix and disclosure with the reporter. Please allow time for a fix before making
the vulnerability public.

## Credential handling

FreeGLM credentials must enter a process only through a trusted secret manager
or the private `~/.freeglm/config` file. From a source checkout, use
`bash install.sh configure`; the installer accepts secrets through hidden input
and writes the configuration with mode `0600`.

Never put a credential value in chat, an agent message, a tool argument, shell
history, logs, screenshots, generated scripts, committed files, or vulnerability
reports. Agents and diagnostic commands may check only whether a credential is
present; they must not read or display its value. If a value is exposed, revoke
or rotate it before continuing and remove it from every retained artifact.

The vendored Blender addon contains a provider-published, shared free-trial
identifier. It is public, quota-limited vendor data rather than a user secret, so
its presence alone is not a secret-scanning failure. Do not replace it with a
private credential or reuse it outside the vendor's documented trial path. Any
user-specific credential remains subject to the environment/private-config rule
above.

## External services and data egress

Some capabilities send prompts, URLs, images, audio, video, search queries, or
derived media to third-party services. Before using one, identify the provider,
the data leaving the local environment, and the applicable retention, residency,
and access-control policy. Obtain user approval when the data or destination is
not already explicit in the request.

Local reverse-image search requires making the image reachable to the search
provider. Use a public host only with explicit user consent; otherwise do not run
that workflow. Local file reading and rendering can remain local when no
external-provider capability is selected. The capability-specific boundaries
are maintained in [the project map](docs/en/project-map.md#network-and-data-egress).
