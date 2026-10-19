# Overseas Radar Skill

Turn a product, manufacturing capability, or consumer need into an evidence-backed B2B research decision and a practical validation plan.

[中文](README.md) · [Skill instructions (Chinese)](skills/overseas-radar-b2b-research/SKILL.md) · [Worked example](skills/overseas-radar-b2b-research/references/worked-example.md)

Version 0.1.0 contains a portable Markdown skill, an evidence schema and CSV template, a seven-section report outline, and a worked example. Instructions and templates are currently in Chinese; this README is an English overview.

## Two starting points

- Consumer use cases and feedback → demand hypotheses → potential business buyers → purchasing requirements → supply fit and validation.
- Products, factory capabilities or B2B inquiries → possible markets and use cases → buyers and channels → competition, conditions and next steps.

The workflow is: scope → evidence → comparison → transaction and supply checks → small experiments. Recommendations connect to source samples and explicitly separate observed content, seller claims, reasoning and unknowns. Potential buyer roles do not imply verified purchasing plans.

## Install

Download the repository or a [release](https://github.com/yaoadms-dot/overseas-radar-skill/releases). Copy the entire `skills/overseas-radar-b2b-research/` directory into your host's supported skills directory. For Codex, use the active CODEX_HOME's `skills/` directory, preserving an existing custom home. Invoke `$overseas-radar-b2b-research` with a product/capability and decision question.

For WorkBuddy and other expert tools, use the [manual adaptation guide](skills/overseas-radar-b2b-research/references/host-adaptation.md); a registered native expert package is not included. Browsing and file tools are supplied by the host. Without browsing, the skill analyzes provided materials and identifies search work still to do.

## Validate and package

Requires Python 3.10+ only:

```sh
python scripts/validate.py
python scripts/validate.py --package
```

See [validation](docs/VALIDATION.md) for what was actually checked. The worked example combines cited public product pages with explicitly fictional client conditions; it is not proof of demand or sales. This skill does not include the original application's authentication, storage, Accio/Jev integrations or document export runtime.

MIT for repository code and authored text; third-party source material and trademarks retain their respective rights. See [provenance](docs/PROVENANCE.md) and [contributing](CONTRIBUTING.md).
