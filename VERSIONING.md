# Versioning Strategy

## Overview

This repository uses **per-component semantic versioning** with automated git tagging. Each Helm chart maintains its own version independently, and every merge to main creates a unique, traceable release.

## Version Format

Each component version follows semantic versioning:

```
X.Y.Z
```

Where:
- `X` - Major version (breaking changes)
- `Y` - Minor version (new features, backwards-compatible)
- `Z` - Patch version (bug fixes)

Examples:
```
ingestion-pipeline-0.2.18
ingestion-pipeline-0.2.19
llama-stack-0.3.0
mcp-servers-0.1.0
```

## Chart.yaml Fields

Each Helm chart has two version fields that are **kept in sync**:

```yaml
# Chart.yaml
version: 0.2.18        # Chart version
appVersion: "0.2.18"   # Always equals version
```

**Note:** `version` and `appVersion` are always the same. The workflow automatically updates both fields together.

### When to Update Version

Bump the version when you make changes to:
- Source code
- Helm templates
- Configuration
- Dependencies

Follow [Semantic Versioning](https://semver.org/):
- **PATCH** (0.2.18 → 0.2.19): Bug fixes, small changes
- **MINOR** (0.2.18 → 0.3.0): New features, backwards-compatible
- **MAJOR** (0.2.18 → 1.0.0): Breaking changes

**Dependency Versions:**
- LlamaStack version is configured in `llama-stack/helm/values.yaml`
- LlamaStack client version is pinned in `ingestion-pipeline/src/requirements.txt`
- No build args or templating needed

## Automated Build Process

On every merge to `main` (when not from github-actions[bot]), the GitHub workflow:

1. **Detects changed components** - scans which charts were modified

2. **Updates Chart.yaml versions and creates commits**:
   - For each changed component:
     - Reads current `version` from Chart.yaml (e.g., `0.2.18`)
     - Checks if git tag `component-0.2.18` already exists
     - **If tag exists**: Auto-increments patch version (`0.2.18` → `0.2.19`)
     - **If tag doesn't exist**: Uses the version as-is (developer manually bumped it)
     - Updates both `version` and `appVersion` to the same value
     - Creates commit: `chore(component): bump version to 0.2.19`
     - Creates annotated tag: `component-0.2.19`
   - Pushes all commits and tags together

3. **Builds container images** (in parallel for each component):
   - Each component builds from its own tagged commit
   - Reads version from Chart.yaml
   - Creates 3 image tags:
     - `0.2.19` (version, matches chart version)
     - `a1b2c3d` (git commit SHA - first 7 chars)
     - `latest` (always points to newest)

4. **Publishes Helm charts**:
   - Packages charts with updated versions
   - Publishes to gh-pages repository

## Git Tags

Git tags are automatically created following this pattern:

```
{component-name}-{version}
```

Examples:
- `ingestion-pipeline-0.2.18`
- `ingestion-pipeline-0.2.19`
- `llama-stack-0.3.0`
- `mcp-servers-0.1.0`

You can list all tags for a component:
```bash
git tag -l "ingestion-pipeline-*"
```

## Container Image Tags

Images are pushed to Quay.io with three tags per build:

```bash
# Version (primary reference, matches chart version)
quay.io/rh-ai-quickstart/ingestion-pipeline:0.2.19

# Git commit SHA (for exact code traceability)
quay.io/rh-ai-quickstart/ingestion-pipeline:a1b2c3d

# Latest (convenience tag)
quay.io/rh-ai-quickstart/ingestion-pipeline:latest
```

Components with container images:
- `ingestion-pipeline`
- `mcp-weather`
- `oracle-sqlcl`
- `oracle23ai-tpcds`

### Image Tag Synchronization

Helm templates reference images using `.Chart.Version`, ensuring perfect alignment between chart version and image tag:

```yaml
# Helm template
image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.Version }}"

# When chart version is 0.2.19, resolves to:
image: "quay.io/rh-ai-quickstart/ingestion-pipeline:0.2.19"
```

This means:
- **Chart version = Image tag** (both use `X.Y.Z` semver format)
- **Works in subcharts** - `.Chart.Version` refers to the subchart version, not parent
- **No manual values.yaml updates needed** - defaults to chart version automatically

## Git Commit Strategy

The workflow creates **one commit per component** (not a single commit for all changes):

```
When ingestion-pipeline and mcp-servers both change:

commit abc123 (tag: ingestion-pipeline-0.2.19)
  chore(ingestion-pipeline): bump version to 0.2.19

commit def456 (tag: mcp-servers-0.1.1)
  chore(mcp-servers): bump version to 0.1.1
```

Each component builds from its own tagged commit, ensuring precise traceability.

## Developer Workflow

### Making Changes to a Component

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Edit code, templates, configs, etc.

3. **(Optional) Bump the chart version** in `component/helm/Chart.yaml`

   **You can either:**
   - **Manually bump the version** if you want specific control:
     ```yaml
     version: 0.3.0  # Manual bump for major/minor changes
     ```
   - **Leave it unchanged** and let the workflow auto-increment the patch version

4. **Commit and create PR**
   ```bash
   git add .
   git commit -m "feat(ingestion-pipeline): add new feature"
   git push origin feature/my-feature
   ```

5. **Merge to main**
   - On merge, workflow automatically:
     - Checks if version tag exists
     - If tag exists: Auto-increments patch (`0.2.18` → `0.2.19`)
     - If tag doesn't exist: Uses your manual version
     - Updates both `version` and `appVersion` to match
     - Commits version update to main
     - Builds image with tags: `0.2.19`, `a1b2c3d`, `latest`
     - Creates and pushes git tag: `ingestion-pipeline-0.2.19`
     - Publishes Helm chart

### Upgrading Upstream Dependencies

Dependency versions are managed directly in their configuration files:

**LlamaStack version:**
```yaml
# llama-stack/helm/values.yaml
llamastackVersion: "0.0.58"  # Update the LlamaStack container version
```

**LlamaStack client version:**
```txt
# ingestion-pipeline/src/requirements.txt
llama-stack-client==0.2.20  # Update the Python client version
```

Then bump the chart version and commit:
```yaml
# component/helm/Chart.yaml
version: 0.3.0  # Bump for the dependency upgrade
```

### Auto-Increment Behavior

If you don't manually bump the version, the workflow auto-increments the patch version:

```
Scenario: Merge without version bump

Chart.yaml has: version: 0.2.18
Tag ingestion-pipeline-0.2.18 exists
  → Workflow auto-increments to: 0.2.19
  → Tag: ingestion-pipeline-0.2.19

Next merge without version bump:
  → Workflow auto-increments to: 0.2.20
  → Tag: ingestion-pipeline-0.2.20

Manual version bump to 0.3.0:
  → Workflow uses: 0.3.0
  → Tag: ingestion-pipeline-0.3.0
```

This ensures every merge creates a unique version, even if you forget to bump manually.

## Traceability

### Finding Source Code for a Running Image

**From version tag:**
```bash
# Check out the exact tagged commit
git checkout ingestion-pipeline-0.2.19

# Or view what changed
git show ingestion-pipeline-0.2.19
```

**From SHA tag:**
```bash
# Check out exact commit
git checkout a1b2c3d

# Or view commit details
git show a1b2c3d
```

**From a running pod:**
```bash
# Get the image tag
oc get pod my-pod -o jsonpath='{.spec.containers[0].image}'
# → quay.io/rh-ai-quickstart/ingestion-pipeline:0.2.19

# Check out that version
git checkout ingestion-pipeline-0.2.19
```

### Finding All Versions of a Component

```bash
# List all tags for a component
git tag -l "ingestion-pipeline-*"

# See what changed between versions
git diff ingestion-pipeline-0.2.18..ingestion-pipeline-0.2.19

# View all images on Quay.io
skopeo list-tags docker://quay.io/rh-ai-quickstart/ingestion-pipeline
```

## Helm Chart Versioning

Helm charts are published to: `https://rh-ai-quickstart.github.io/ai-architecture-charts`

Each chart version is preserved:
```bash
# Search for all versions
helm search repo ai-architecture-charts/ingestion-pipeline --versions

# Install specific version
helm install my-release ai-architecture-charts/ingestion-pipeline --version 0.2.18
```

The chart `version` field determines the Helm package version, while `appVersion` is informational.

## Components and Their Versioning

| Component | Builds Container? | Current Version | appVersion Tracks |
|-----------|------------------|-----------------|-------------------|
| ingestion-pipeline | Yes (via build.yaml) | 0.2.18 | LlamaStack client |
| llama-stack | No | 0.2.18 | LlamaStack upstream |
| mcp-servers | Yes (via build.yaml) | 0.1.0 | MCP protocol |
| llm-service | No | 0.1.0 | N/A |
| pgvector | No | 0.1.0 | PostgreSQL/pgvector |
| minio | No | 0.1.0 | MinIO server |
| oracle23ai | Yes (via build.yaml) | 0.1.0 | Oracle Database |
| configure-pipeline | No | 0.1.0 | Jupyter |

## Adding Container Builds to a Component

To enable container image building for a component, create a `build.yaml` file in the component directory:

```yaml
# component/build.yaml
builds:
  - name: component-name
    containerfile: Containerfile
    context: src
```

For components with multiple images (like mcp-servers):

```yaml
# mcp-servers/build.yaml
builds:
  - name: mcp-weather
    containerfile: weather/Containerfile
    context: weather/src
  - name: oracle-sqlcl
    containerfile: oracle-sqlcl/Containerfile
    context: oracle-sqlcl
```

The workflow automatically discovers `build.yaml` files and builds the specified images.

## Best Practices

### Do's

✅ **Bump version for significant changes** - major/minor changes should be explicit
✅ **Use semantic versioning correctly** - patch for fixes, minor for features, major for breaking changes
✅ **Use conventional commits** - `feat:`, `fix:`, `docs:`, etc. for clear git history
✅ **Let auto-increment handle small fixes** - workflow will bump patch version automatically
✅ **Test locally before merging** - `helm install --dry-run`

### Don'ts

❌ **Don't reuse version numbers** - versions are immutable, always increment
❌ **Don't manually create git tags** - workflow handles it automatically
❌ **Don't merge breaking changes without bumping major version**
❌ **Don't manually edit appVersion** - it's automatically synced with version

## Troubleshooting

### Version didn't auto-increment

The workflow checks if a tag exists before deciding to auto-increment:
```bash
# Check if tag exists
git tag -l "ingestion-pipeline-0.2.18"

# If tag exists, workflow will auto-increment to 0.2.19
# If tag doesn't exist, workflow uses the version as-is
```

### Wrong image tag in production

Every image has a SHA tag for exact traceability:
```bash
# Find the SHA tag from the running image
oc get pod -o jsonpath='{.spec.containers[0].image}'

# Check out that exact commit
git checkout <sha>
```

### Need to find what version introduced a bug

```bash
# List all tags for a component
git tag -l "ingestion-pipeline-*" --sort=-version:refname

# Test each version
git checkout ingestion-pipeline-0.2.20
# ... test ...
git checkout ingestion-pipeline-0.2.19
# ... test ...
```

### Multiple components changed, different versioning

That's fine! Each component versions independently:
```
ingestion-pipeline-0.3.0  (manually bumped to minor)
llama-stack-0.2.19        (auto-incremented patch)
```

## Future Enhancements

Possible improvements to consider:

- **Automated version bumping** based on conventional commits
- **Pre-release versions** (alpha, beta, rc)
- **Release notes generation** from git commits and annotated tags
- **Version compatibility matrix** between components

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Conventional Commits](https://www.conventionalcommits.org/)
