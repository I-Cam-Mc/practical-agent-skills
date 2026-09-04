# Practical Agent Skills

A collection of small, field-derived Agent Skills for diagnostics, research, release verification, privacy and creative operations.

Each folder under `skills/` is independently installable. The skills favour read-only discovery, explicit approval before external changes, observable verification and honest reporting of blocked checks.

## Included skills

| Skill | What it helps with |
|---|---|
| [`ai-benchmark-claim-checker`](skills/ai-benchmark-claim-checker/) | Explain what an AI benchmark actually measured and whether two results are comparable |
| [`assistant-readiness-audit`](skills/assistant-readiness-audit/) | Distinguish configured assistant components from a verified end-to-end service |
| [`decision-research`](skills/decision-research/) | Build auditable evidence, claim, programme and contradiction registers around a decision |
| [`docker-deliverable-preflight`](skills/docker-deliverable-preflight/) | Verify a container hand-off from clean extraction through restricted execution evidence |
| [`html-presentation-studio`](skills/html-presentation-studio/) | Build accessible, dependency-free, self-contained HTML slide decks |
| [`mac-charging-watts`](skills/mac-charging-watts/) | Measure adapter, system-input and battery charging power without confusing the three |
| [`mac-performance-triage`](skills/mac-performance-triage/) | Diagnose CPU, memory pressure, swap and load using bounded read-only observations |
| [`personal-data-approval-pack`](skills/personal-data-approval-pack/) | Stage exact, backed-up and read-back-verifiable personal-data changes for approval |
| [`railway-burst-sandbox`](skills/railway-burst-sandbox/) | Plan and operate short-lived Railway compute with cost and cleanup controls |
| [`rekordbox-transition-miner`](skills/rekordbox-transition-miner/) | Turn DJ history into review candidates and human-confirmed transition recipes |
| [`voice-profile-builder`](skills/voice-profile-builder/) | Derive an authorised writing guide without publishing private samples |
| [`web-release-proof`](skills/web-release-proof/) | Prove that a scoped website change reached the production user experience |

## Install one skill

Copy the directory that directly contains its `SKILL.md` into the skills directory used by your agent harness. For example:

```bash
git clone https://github.com/I-Cam-Mc/practical-agent-skills.git
cp -R practical-agent-skills/skills/mac-charging-watts /path/to/your/skills/
```

For Codex, you can also use its bundled GitHub skill installer and select a path such as `skills/mac-charging-watts`.

Restart or begin a new agent turn after installation so the skill catalogue refreshes.

## Verification

Packages with deterministic helpers include standard-library unit tests. From the repository root:

```bash
for test_dir in skills/*/tests; do
  python3 -m unittest discover -s "$test_dir" -v
done
```

Skill structure and frontmatter were also checked with Codex's bundled `quick_validate.py` before release. Passing a structural validator does not prove a live provider, device or deployment result. Each skill states its own completion evidence.

## Provenance

These packages generalise workflows developed during real tasks, but contain no personal datasets, credentials, customer material or private machine identifiers. Synthetic fixtures are labelled as such.

`decision-research` contains original instructions influenced by published FS-Researcher, WebWeaver and DeepVerifier methods. It vendors none of their code, prompts, datasets or model assets. See its `ATTRIBUTION.md`.

The separately audited `video-download` and `video-transcribe` adaptations are intentionally not part of this collection. Their originals already belong to Joe Amditis's MIT-licensed video toolkit, so upstream contribution or a clearly attributed fork is the appropriate route.

## Licence

MIT. See [LICENSE](LICENSE). Third-party products and research referenced by individual skills retain their own names, rights and terms.
