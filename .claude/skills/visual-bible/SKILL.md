---
name: visual-bible
description: Walks a new kit through defining its own DESIGN.md visual bible via clarifying questions, section by section. Not a fill-in-the-blank template — asks follow-up questions per section the way M1/M2 did for Office Pack.
---

Produces a new kit's `DESIGN.md` — the single reference document a kit's asset scripts are built against, concrete enough that meshes/materials can be authored consistently without further style clarification per-asset.

This is a generic authoring tool, not Office Pack content: never reuse Office Pack's own color palette, poly budgets, scale sheet, or reference imagery as answers. Every value in the output must come from this kit's own author, gathered through the questions below.

**Arguments** (optional, passed as `$ARGUMENTS`):

- `--output-file <path>` — Where to write the result (default: `./DESIGN.md`)

## Execution steps

1. **Check for an existing `DESIGN.md`** at the output path. If one exists, read it first and treat this as a revision pass — confirm with the user which sections to redo vs. leave alone, rather than overwriting silently.
2. **Work through the sections below in order, one at a time.** For each section: ask the listed questions (via `AskUserQuestion` where the answer is a choice among a few concrete options, plain conversation where it's open-ended description), react to the answer with at least one follow-up before moving on — don't accept the first vague answer and move to the next section. The goal is the same depth [m1-create-aesthetic.md](../../../plan/m1-create-aesthetic.md) and [m2-visual-bible.md](../../../plan/m2-visual-bible.md) reached for Office Pack, arrived at through dialogue rather than assumed.
3. **Write each section's answer into the output file as you finish it**, rather than holding everything until the end — a kit author reviewing progress should be able to read what's been locked in so far at any point.
4. **After all sections are done**, reread the full document once for internal consistency (e.g. the poly budget's tiers should match the scale sheet's asset categories; the color palette's group names should match the material spec's roughness/metallic table) and flag any mismatch to the user before finishing.

## Sections (ask about each, in this order)

1. **Style statement** — What's the aesthetic in one line (low-poly? flat-shaded? stylized-realistic?)? Name 2-3 reference packs/games/scenes it should feel like. Push for specifics over adjectives — "clean and modern" isn't enough; ask what makes a *specific* reference feel that way.

2. **Reference mood board** — Ask for reference images or a description of the scene/mood if no images are available yet. Probe for: dominant color temperature, how cluttered vs. sparse, what light source (natural/artificial, hard/soft shadows).

3. **Poly budget** — What are this kit's asset size tiers (small props / hero items / large pieces, or a different breakdown entirely — don't assume the office pack's three tiers apply)? Ask for a target and hard-max tri count per tier, and an absolute hard max across the whole kit.

4. **Shape language rules** — How are edges/corners treated (hard bevels, soft, none)? How much silhouette detail survives vs. gets omitted? Ask whether this kit needs any of Office Pack's structural patterns (resizable modular segments, repeatable module kits, hollow-container variants) or has its own — don't assume these carry over.

5. **Scale & proportion sheet** — What's the human-scale reference (standing height) this kit's proportions are checked against? Ask whether per-asset dimensions will be tracked in a separate asset-list doc (as Office Pack does) or inline here.

6. **Color palette** — Ask for the actual swatch list: name + hex per color, grouped however makes sense for this kit (neutrals, metals, accents, etc.). Apply the color-identity naming convention decided in [m9-environment-character-kit.md](../../../plan/m9-environment-character-kit.md) deliverable 2 — name swatches for what they look like (`Chrome_Grey`, `Forest_Green`), never for their intended role (`Wall_White`, `Foliage_Green`) — so the palette can be shared across future kits. Ask how many colors are allowed per asset.

7. **Material/shading spec** — Confirm flat-color PBR, no texture maps (Office Pack's convention) still applies, or ask what's different. Ask for metallic/roughness values per palette group. Confirm which render pipeline(s) this kit targets (Built-in, URP, both, HDRP) — don't assume both like Office Pack.

8. **Lighting reference** — Ask for the intended lighting rig (key light type/color temperature, fill, any accent lights) used to judge material values consistently across renders.

9. **Naming & pivot conventions** — Ask for the pivot-placement rule per attachment type this kit actually needs (floor-sitting, wall-mounted, hinged, etc. — not necessarily all of Office Pack's categories). Confirm the object/sub-part naming pattern (`<AssetName>`, `<AssetName>_<PartName>`).

10. **Annotated example asset** — Once at least one hero asset is scoped, ask the user to pick one representative asset and walk through it against every rule above (objects, dimensions, shape language, poly budget, materials) — same purpose as Office Pack's Chair example: a concrete "if in doubt, match this" reference.

## Output format

Write to the output file in the same section structure Office Pack's own `DESIGN.md` uses (see that file in this repo for the exact heading/table conventions), numbered `## 1. Style statement` through `## 10. Annotated example asset`, each linking back to this kit's own plan docs where relevant rather than Office Pack's.

## Definition of done

The visual bible is complete when a new hero asset for this kit could be described using only the resulting `DESIGN.md` plus the item's name, with no further aesthetic clarification needed — only bug fixes.
