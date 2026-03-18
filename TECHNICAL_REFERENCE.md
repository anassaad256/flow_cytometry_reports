# Flow Cytometry Report Generator — Technical Reference

This document is the authoritative technical reference for the flow cytometry clinical report generation system. It is intended for developers (including AI assistants) who need to understand, modify, or extend the system.

---

## Table of Contents

1. [System Purpose](#1-system-purpose)
2. [Execution Pipeline](#2-execution-pipeline)
3. [Decision Tree DSL](#3-decision-tree-dsl)
4. [The Evaluation Context](#4-the-evaluation-context)
5. [Predicate System](#5-predicate-system)
6. [Template Selection](#6-template-selection)
7. [Tag Engine](#7-tag-engine)
8. [Derived Value Computers](#8-derived-value-computers)
9. [Text Rendering](#9-text-rendering)
10. [Three-Layer Marker Architecture](#10-three-layer-marker-architecture)
11. [Comment Assembly (Per-Region Paragraphs)](#11-comment-assembly-per-region-paragraphs)
12. [Main Line Assembly and PANEL_NEGATIVE Suppression](#12-main-line-assembly-and-panel_negative-suppression)
13. [Panel-Specific Logic](#13-panel-specific-logic)
14. [Frontend Architecture](#14-frontend-architecture)
15. [Data Models](#15-data-models)
16. [Number Formatting](#16-number-formatting)
17. [Known Design Decisions and Gotchas](#17-known-design-decisions-and-gotchas)
18. [Adding a New Panel](#18-adding-a-new-panel)
19. [File Reference](#19-file-reference)

---

## 1. System Purpose

This system generates deterministic clinical pathology consultation reports for flow cytometry specimens. A clinician enters structured case data (specimen type, viability, adequacy, selected panels, regions, populations with marker states), and the engine produces a standardized three-section report:

- **General**: Header block (specimen, clinical data, viability, antibody panel list, lab disclaimer)
- **Main Line**: Priority-sorted diagnostic findings
- **Comment**: Detailed immunophenotypic narrative organized as one paragraph per region

The system is **fully deterministic** — identical inputs always produce identical outputs. There is no AI/LLM in the report generation pipeline; the engine is a rule-based decision tree evaluator.

---

## 2. Execution Pipeline

The full execution flow for an adequate case:

```
CaseInput (JSON from frontend)
    │
    ▼
ReportGenerator.generate(case_input)
    │
    ▼
MainTreeRunner.run(case_input)
    ├── Push case-level scope (specimen_type, viability, etc.)
    ├── Run case-level validations
    ├── For each selected panel:
    │   ├── PanelRunner.run(panel_input)
    │   │   ├── Push panel-level scope (e.g., cyto_tube_performed)
    │   │   ├── Resolve antibody panel markers (template selection → constant ref)
    │   │   ├── For each region in panel spec:
    │   │   │   ├── Push region scope (region_pct_total, etc.)
    │   │   │   ├── Render region-level comment template (if any)
    │   │   │   ├── For each population instance in that region:
    │   │   │   │   ├── Push population scope (fields + marker_states)
    │   │   │   │   ├── Auto-compute pct_gated_events from region_pct_total × pct_region
    │   │   │   │   ├── Determine active markers (template selection)
    │   │   │   │   ├── Compute tags (static, from_fields, auto_from_markers)
    │   │   │   │   ├── Evaluate rules (incremental tag addition)
    │   │   │   │   ├── Apply normalizations (set_fields from tag conditions)
    │   │   │   │   ├── Compute derived values (marker_list, percent_pick, etc.)
    │   │   │   │   ├── Store population tags for panel-level queries
    │   │   │   │   ├── Run population validations
    │   │   │   │   ├── Select & render comment template
    │   │   │   │   ├── Select & render main line item template
    │   │   │   │   ├── Clear tags, pop scope
    │   │   │   │   └── Return (comment_lines, main_items, validations)
    │   │   │   └── Pop region scope
    │   │   ├── Assemble comments (one paragraph per region)
    │   │   ├── Assemble main line items (panel-level template selection)
    │   │   └── Return PanelOutput
    │   └── (repeat for next panel)
    ├── Collect & deduplicate antibody markers across panels
    ├── Collect & sort main line items (priority ascending, then selection order)
    ├── Suppress PANEL_NEGATIVE items if any real findings exist
    ├── Collect all comment lines across panels
    ├── Append viability caution if viability < 50%
    ├── Render General section
    ├── Render Main Line section
    ├── Render Comment section
    └── Return ReportOutput
```

### Key files involved:
- `backend/src/report_generator.py` — Entry point, loads YAML, creates MainTreeRunner
- `backend/src/main_tree_runner.py` — Case-level orchestration
- `backend/src/panel_runner.py` — Per-panel execution engine

---

## 3. Decision Tree DSL

All clinical logic lives in YAML files in `decision_trees/`. The engine never hardcodes clinical rules — it evaluates what the YAML describes.

### Main Tree (`Main-tree.txt`)
- Defines global enums (marker states, adequacy, inadequate reasons)
- Defines global constants (expressed states, precision, viability threshold, lab disclaimer)
- Declares the panel registry (which panel IDs map to which YAML packs)
- Specifies case-level validations
- Defines output generation templates for General, Main Line, and Comment sections

### Panel Rule Packs (e.g., `acute_norm.yaml`)
Each panel YAML file contains:
- `shared_refs` — References to main tree constants (expressed states, precision, etc.)
- `constants` — Panel-specific constants (marker ID lists, display orders)
- `marker_catalog` — Maps marker IDs to display names (e.g., `M_CD34` → `"CD34"`)
- `enums` — Panel-specific enum values
- `panel` section:
  - `inputs` — Required/optional panel-level fields
  - `antibody_panel_markers_generation` — Templates selecting which marker list to use
  - `regions` — Array of region definitions, each containing:
    - `inputs` — Region-level fields (e.g., `region_pct_total`)
    - `region_comment_line_generation` — Region-level comment templates
    - `populations` — Array of population specs, each containing:
      - `inputs` — Population-level fields
      - `active_markers_generation` — Which markers are active for this population
      - `default_marker_states` — Default marker selections per condition
      - `tags` — Tag computation spec (static, from_fields, auto_from_markers)
      - `rules` — Conditional rules that set tags based on predicates
      - `normalizations` — Set field values based on tag conditions
      - `derived` — Computed values (marker lists, percentages, ratios)
      - `comment_line_generation` — Comment templates with helper clauses
      - `main_line_item_generation` — Main line item templates
      - `validations` — Input validation rules
  - `comment_lines_generation` — How to order comment output (region comment → populations)
  - `main_line_items_generation` — Panel-level main line assembly

---

## 4. The Evaluation Context

**File**: `backend/src/context.py`

`EvaluationContext` is the central state object threaded through the entire pipeline. It provides:

### Hierarchical Scope Stack
```python
ctx.push_scope({"field": "value"})  # Add a new scope level
ctx.get("field")                     # Walk scopes bottom-up to find field
ctx.set_derived("key", value)        # Set value in current (topmost) scope
ctx.pop_scope()                      # Remove current scope level
```

Scopes are stacked: case → panel → region → population. `get()` walks bottom-up, so population fields shadow region fields, which shadow panel fields, etc.

### Tag Store
Tags are boolean flags computed from marker states and rules:
```python
ctx.add_tags({"TAG_CD5_POSITIVE", "TAG_KAPPA_EXPRESSED"})
ctx.has_tag("TAG_CD5_POSITIVE")  # True
ctx.clear_tags()                  # Cleared between population instances
```

### Population Tag Tracking
After processing each population instance, its tags are stored for later panel-level queries:
```python
ctx.store_population_tags("POP_B_CELLS", tags_set)
ctx.population_exists_with_tag("B_CELL_RESTRICTED")  # Check across all instances
ctx.count_populations_with_tag("ABNORMAL")
```

### Constant/Reference Resolution
```python
ctx.get_constant("marker_ids_no_cyto")           # Panel or main tree constants
ctx.resolve_ref("shared_refs.expressed_states_ref")  # Follow ref chain to main tree
ctx.get_marker_catalog()                            # Current panel's marker catalog
```

---

## 5. Predicate System

**File**: `backend/src/predicates.py`

Predicates are the conditional logic of the DSL. Every `when` clause in YAML is evaluated by `evaluate_predicate()`.

### Supported Predicates

| Predicate | YAML Syntax | Description |
|---|---|---|
| `all` | `all: [pred1, pred2]` | AND — all children must be true |
| `any` | `any: [pred1, pred2]` | OR — at least one child must be true |
| `not` | `not: pred` | Negation |
| `default` | `default: true` | Always true (catch-all) |
| `field_present` | `field_present: "field_name"` | Field exists and is not None |
| `field_equals` | `field_equals: {field: "x", value: "Y"}` | Field equals a specific value |
| `field_gte` | `field_gte: {field: "x", value: 20}` | Field >= value (numeric) |
| `field_lt` | `field_lt: {field: "x", value: 0.01}` | Field < value (numeric) |
| `list_nonempty` | `list_nonempty: "field_name"` | List/string field has length > 0 |
| `tag_present` | `tag_present: "TAG_NAME"` | Tag exists in context |
| `any_tag` | `any_tag: ["TAG_A", "TAG_B"]` | Any of the listed tags exist |
| `marker_state_is` | `marker_state_is: {marker: "M_CD5", state: "STATE_POSITIVE"}` | Specific marker has specific state |
| `marker_state_in` | `marker_state_in: {marker: "M_CD5", states_ref: "..."}` | Marker state is in a set |
| `marker_states_all_equal` | `marker_states_all_equal: {state: "STATE_NA"}` | All markers have the same state |
| `marker_states_all_na_except` | `marker_states_all_na_except: {except: [...]}` | All markers are N/A except listed ones |
| `context_region_equals` | `context_region_equals: "REGION_BLASTS"` | Current region matches |
| `context_population_equals` | `context_population_equals: "POP_B_CELLS"` | Current population matches |
| `population_count_with_tag` | `population_count_with_tag: {tag: "X", op: "gte", value: 1}` | Count of population instances with tag |
| `population_count_with_tag_any` | `population_count_with_tag_any: {tags: [...], op: "gte", value: 1}` | Count with any of listed tags |

A bare string predicate is treated as a reference to a derived boolean value in context.

---

## 6. Template Selection

**File**: `backend/src/template_selector.py`

Templates are selected using priority-based matching:

```yaml
templates:
  - id: HIGH_PRIORITY_TEMPLATE
    priority: 300
    when:
      field_equals: { field: "blast_type", value: BLAST_MYELOBLASTS }
    text: "..."

  - id: DEFAULT_TEMPLATE
    priority: 100
    when: { default: true }
    text: "..."
```

**Algorithm**: Sort templates by priority descending → evaluate `when` predicate for each → first match wins. If `when` is absent, the template always matches (acts as catch-all).

---

## 7. Tag Engine

**File**: `backend/src/tag_engine.py`

Tags are boolean flags computed from marker states and field values. They bridge raw marker states to template predicates.

### Tag Sources (in evaluation order)

1. **Static tags** — Always applied:
   ```yaml
   tags:
     static: ["IS_B_CELL"]
   ```

2. **from_fields tags** — Based on field values:
   ```yaml
   tags:
     from_fields:
       - when: { field_equals: { field: "fsc_cell_size", value: "FSC_SMALL_TO_INTERMEDIATE" } }
         set_tags: ["FSC_SMALL_INTERMEDIATE"]
   ```

3. **auto_from_markers tags** — Auto-generated from marker states using patterns:
   ```yaml
   tags:
     auto_from_markers:
       expressed_tag_pattern: "TAG_{marker}_EXPRESSED"
       negative_tag_pattern: "TAG_{marker}_NEGATIVE"
       modifier_tag_patterns:
         STATE_DIM: "TAG_{marker}_DIM"
         STATE_BRIGHT: "TAG_{marker}_BRIGHT"
   ```
   For example, if M_CD5 is STATE_POSITIVE → generates `TAG_CD5_EXPRESSED`.

### Rule Evaluation (Incremental)

Rules are evaluated **after** initial tags are computed. Tags are added to context incrementally so later rules can depend on tags set by earlier rules:

```yaml
rules:
  - when: { all: [tag_present: "TAG_KAPPA_EXPRESSED", tag_present: "TAG_LAMBDA_NEGATIVE"] }
    set_tags: ["KAPPA_RESTRICTED"]

  - when: { tag_present: "KAPPA_RESTRICTED" }  # depends on tag set by previous rule
    set_tags: ["B_CELL_RESTRICTED"]
```

This was a critical bug fix — previously all rules were evaluated against the initial tag set only, so chained dependencies didn't work.

### Normalizations

After rules, normalizations can override field values based on tag state:
```yaml
normalizations:
  - when: { tag_present: "KAPPA_RESTRICTED" }
    set_fields:
      restriction_type: "kappa"
```

---

## 8. Derived Value Computers

**File**: `backend/src/derived.py`

Derived values are computed from context and stored back in context for use by templates.

### Types

| Type | Description |
|---|---|
| `marker_list` | Ordered list of marker display names filtered by state. Uses `order_const` for ordering, `include_states_ref` for filtering, `state_suffix_ref` for modifiers like "(dim)". Only includes markers in the active marker set. |
| `percent_pick` | Picks first available percentage field from `preference_fields`, formats to precision. Supports `fixed_precision: true` for always showing decimal places (used by plasma panel). |
| `ratio_text` | Computes ratio between two fields with directional formatting (e.g., "3.2:1" or "1:2.1"). |
| `enum_string` | Maps a tag or field value to a display string. |
| `cd4_cd8_status_from_marker_states` | Determines CD4/CD8 phenotype phrase from marker states. |
| `aberrancy_phrase_from_marker_states` | Finds first aberrant marker and generates a descriptive phrase. |
| `population_exists_with_tag` | Boolean — does any population instance have a specific tag? |
| `boolean_or` | OR multiple derived boolean values. |
| `collect_population_outputs` | Collects outputs from all instances of a population type. |

### enabled_when Guard

Every derived value can have an `enabled_when` predicate. If it evaluates to false, the derived value returns a type-appropriate default (empty list, empty string, False, None).

---

## 9. Text Rendering

**File**: `backend/src/text_renderer.py`

### Variable Interpolation

Templates use `{variable_name}` syntax. The renderer:
1. Resolves helper clauses first (if any)
2. Replaces `{var}` with context value (walks scope stack)
3. Lists are joined with ", "
4. Floats are formatted with `f"{val:g}"` (strips trailing zeros)
5. Multi-space runs are collapsed to single spaces
6. Result is stripped of leading/trailing whitespace

### Helper Clauses

Helper clauses are conditional text fragments used within comment templates:

```yaml
comment_line_generation:
  helper_clauses:
    restriction_clause:
      when: { tag_present: "KAPPA_RESTRICTED" }
      text: " kappa light chain"
      else_when: { tag_present: "LAMBDA_RESTRICTED" }
      else_text: " lambda light chain"
      fallback_text: ""

    negatives_clause:
      when: { list_nonempty: "negative_markers" }
      text: " and negative for {negative_markers}"
      else_text: ""

  templates:
    - text: "...positive for {positive_markers},{restriction_clause}{negatives_clause}."
```

**Important**: Leading spaces in clause text (like `" and negative for..."`) are intentional and preserved by `_render_clause_text()`. The main `render_text()` function strips whitespace, so `_render_clause_text()` restores the leading space if the original text had one.

---

## 10. Three-Layer Marker Architecture

Markers flow through three layers with progressively narrower scope:

### Layer 1: Performed (Panel Level)
All markers in the panel's antibody marker list. Selected by `antibody_panel_markers_generation` templates based on panel-level conditions (e.g., cyto tube status).

Example: Acute Leukemia with cyto tube → all 22 markers. Without cyto tube → 18 markers (no TdT, MPO, cyto CD79a, cyto CD3).

These appear in the "Antibody Panel Performed" line in the General section.

### Layer 2: Asked About (Population Level)
The **active markers** for a specific population, determined by `active_markers_generation`. This controls which markers appear in the UI grid and which markers are included in derived marker lists.

Example: Monocyte population uses `marker_ids_monocyte` (doesn't include TdT, MPO, cyto markers).

Stored in context as `_active_markers` (a set). The `marker_list` derived computer respects this.

### Layer 3: Reported (User Selection)
The user sets each active marker to a state (Positive, Negative, Dim, Bright, Subset, Variable, N/A). The `marker_list` derived computer filters by `include_states` and formats the display:

- `positive_markers` → includes states in `expressed_states` (Positive, Bright, Dim, Subset, Variable)
- `negative_markers` → includes only `STATE_NEGATIVE`

N/A markers are excluded from all derived lists.

### Default Marker States

Population specs can define `default_marker_states` — conditional defaults applied when a population is first created or when a key field (like `blast_type`) changes:

```yaml
default_marker_states:
  - when:
      field_equals: { field: "blast_type", value: BLAST_MYELOBLASTS }
    states:
      STATE_POSITIVE: [M_CD34, M_CD117, M_CD13, M_CD33, M_CD38, M_HLA_DR]
      STATE_NEGATIVE: [M_CD4, M_CD5, M_CD7, M_CD10, M_CD14, M_CD19, M_CD20, M_CD22, M_CD56, M_CD64]
```

The frontend resolves these via `resolveDefaultMarkerStates()` in `PopulationForm.jsx`. Markers not listed default to `STATE_NA`.

---

## 11. Comment Assembly (Per-Region Paragraphs)

**File**: `backend/src/panel_runner.py` → `_assemble_comments()`

Comments are assembled as **one paragraph per region**. All comment parts within the same region (region comment + population comments) are joined with spaces into a single string.

### How It Works

1. During panel execution, comments are tracked per-region:
   - `region_comments[region_id]` → list of region-level comment strings
   - `region_pop_comments[region_id][pop_id]` → list of (list of comment strings per instance)

2. The `comment_lines_generation.order` config determines population ordering:
   ```yaml
   order:
     - region_comment
     - populations_of_type: POP_BLASTS
     - populations_of_type: POP_MONOCYTES
   ```

3. Assembly iterates regions in encounter order, collecting:
   - Region comment lines first
   - Then population comments in configured order
   - All parts joined with `" ".join(parts)` → single paragraph string

4. The main tree prepends `"Comment:"` header to the final list.

---

## 12. Main Line Assembly and PANEL_NEGATIVE Suppression

### Main Line Item Properties

Each `MainLineItem` has:
- `text` — The display text
- `finding_priority` — Lower = higher priority (100 = acute leukemia, 350 = blast finding, 750 = panel negative)
- `finding_class` — Category (e.g., `"ACUTE_LEUKEMIA"`, `"BLAST_FINDING"`, `"PANEL_NEGATIVE"`)
- `panel_id` / `population_id` — Source tracking
- `selection_order` — Panel selection order (for stable sorting)

### Sorting
Items are sorted by `(finding_priority ascending, selection_order ascending)`. This ensures acute leukemia findings appear before blast findings, which appear before panel negatives.

### PANEL_NEGATIVE Suppression
When multiple panels are selected and some produce real findings while others produce "No significant immunophenotypic abnormalities", the negatives are suppressed:

```python
has_real_findings = any(item.finding_class != "PANEL_NEGATIVE" for item in all_main_items)
if has_real_findings:
    all_main_items = [item for item in all_main_items if item.finding_class != "PANEL_NEGATIVE"]
```

This prevents showing "no significant immunophenotype" alongside a lymphoma finding from another panel.

---

## 13. Panel-Specific Logic

### Acute Leukemia (`acute_norm.yaml`)

- **Cyto tube gating**: `cyto_tube_performed` determines active marker set (18 vs 22 markers)
- **Regions**: REGION_BLASTS (with `region_pct_total`), REGION_MONOCYTES
- **Blast populations**: Select `blast_type` (Myeloblasts / B Lymphoblasts / T Lymphoblasts)
- **Auto-compute**: `pct_gated_events = region_pct_total × pct_region / 100`. If `pct_region` is empty, `pct_gated_events = region_pct_total` (assumes 100% of region).
- **0% templates**: Special comment/mainline templates for B/T lymphoblasts when `pct_gated_events < 0.01`
- **AML threshold**: Myeloblasts ≥ 20% → "Acute myeloid leukemia" (priority 100); < 20% → "detects around X% myeloblasts" (priority 350)
- **Default marker states**: Myeloblasts and B Lymphoblasts have predefined defaults
- **Monocyte defaults**: Common monocyte immunophenotype pre-selected

### Lymphoproliferative / T-NK (`lympro_tnk_norm.yaml`)

- **Single region**: REGION_LYMPHOCYTES with `region_pct_total`
- **Populations**: POP_B_CELLS, POP_T_CELLS, POP_TLGL
- **B cells**: Complex tag system for kappa/lambda restriction, FSC cell size
  - Auto-tags from markers: `TAG_KAPPA_EXPRESSED`, `TAG_LAMBDA_NEGATIVE`, etc.
  - Rules: restriction detection → `KAPPA_RESTRICTED` or `LAMBDA_RESTRICTED` → `B_CELL_RESTRICTED`
  - FSC rules: `FSC_SMALL_INTERMEDIATE` tag → dependent rule for FSC text inclusion
  - Helper clauses for restriction text, negative markers, FSC description
- **T cells**: CD4/CD8 status, aberrancy detection, kappa/lambda ratio if applicable
- **Add-on markers**: Hairy cell markers and T/NK markers are conditionally included

### Plasma Cell Myeloma (`plasma_norm.yaml`)

- **Outcome-driven**: User selects `pc_outcome` (Insufficient / Polyclonal / Kappa Restricted / Lambda Restricted)
- **Fixed precision**: Main line percentages use `fixed_precision: true` (always 2 decimal places)
- **CD56 aberrancy**: Detected and included in comment text
- **Region-level % used**: `region_pct_total` for the percentage display

### MDS (`mds_norm.yaml`)

- **Simplified acute leukemia**: Only myeloblast logic, no cyto tube
- **Smaller marker set**: 9 markers (CD34, CD117, CD33, CD13, CD7, CD19, CD14, CD64, CD45)
- **Same structure**: Blasts and Monocytes regions with default marker states

---

## 14. Frontend Architecture

### Wizard Flow

```
CaseInfoStep → AdequacyStep → Details → PanelWizard → ReportOutput
                                  │
              Inadequate ─────────┤─── InadequateReasonStep → generate
              Adequate ───────────┘─── AdequateSetupStep → PanelWizard → generate
```

### Key Components

- **`App.jsx`** — Main wizard state machine, step navigation, report generation
- **`useCaseState.js`** — Hook managing all case state with localStorage persistence
- **`PanelWizard.jsx`** — Iterates selected panels, loads schemas dynamically via `/api/panel/{id}/schema`
  - Contains `RegionsEditor` for managing regions and populations within panels
  - Contains `PanelLevelInputs` for panel-level field entry
- **`PopulationForm.jsx`** — Renders fields for a single population instance
  - `getActiveMarkers()` — Client-side template matching to determine which markers to show
  - `resolveDefaultMarkerStates()` — Matches `default_marker_states` from population spec against current fields
  - Tracks `blast_type` changes to re-apply defaults
  - Auto-calculates `pct_gated_events ↔ pct_region` bidirectionally
- **`MarkerStateGrid.jsx`** — Grid of markers with state selection dropdowns

### Schema-Driven UI

The frontend is entirely schema-driven. It fetches panel schemas from `/api/panel/{id}/schema` and dynamically renders:
- Panel-level inputs (radio groups for enums, text inputs)
- Region-level inputs (percentage fields)
- Population-level inputs (enum selects, percentage fields)
- Active marker grid (determined by client-side template matching against panel fields)
- Default marker states (resolved from population spec conditions)

---

## 15. Data Models

**File**: `backend/src/models.py`

### Input Models

```
CaseInput
├── specimen_type: str
├── clinical_data: str
├── adequacy_status: str ("ADEQUACY_ADEQUATE" | "ADEQUACY_INADEQUATE")
├── inadequate_reason: Optional[str]
├── viability_percent: Optional[float]
└── selected_panels: list[PanelInput]
    └── PanelInput
        ├── panel_id: str
        ├── fields: dict
        └── regions: list[RegionInput]
            └── RegionInput
                ├── region_id: str
                ├── fields: dict
                └── populations: list[PopulationInput]
                    └── PopulationInput
                        ├── population_id: str
                        ├── fields: dict
                        └── marker_states: list[MarkerStateInput]
                            └── MarkerStateInput
                                ├── marker_id: str
                                └── state: str
```

### Output Models

```
ReportOutput
├── general: list[str]           # Lines for the General section
├── main_line: list[str]         # Lines for the Main Line section
├── comment: list[str]           # Lines for the Comment section (first is "Comment:")
└── validation_errors: list[ValidationResult]
    └── ValidationResult
        ├── id: str
        ├── severity: str ("ERROR" | "WARN")
        └── message: str
```

### Internal Models

```
PanelOutput (per-panel, not exposed to API)
├── panel_id: str
├── antibody_panel_markers: list[str]   # Marker IDs
├── comment_lines: list[str]            # One paragraph per region
└── main_line_items: list[MainLineItem]
    └── MainLineItem
        ├── text: str
        ├── finding_priority: int
        ├── finding_class: str
        ├── panel_id: str
        ├── population_id: str
        └── selection_order: int
```

---

## 16. Number Formatting

Two formatting paths exist and both must be consistent:

### In derived.py (for derived values like percentages)
```python
def _fmt_number(value: float, precision: int) -> str:
    return f"{value:.{precision}f}".rstrip('0').rstrip('.')
```
Strips trailing zeros: `5.00` → `"5"`, `5.10` → `"5.1"`, `5.12` → `"5.12"`

For `fixed_precision: true` (plasma panel): uses `f"{fval:.{precision}f}"` without stripping.

### In text_renderer.py (for {variable} interpolation)
```python
def _fmt_val(val) -> str:
    if isinstance(val, float):
        return f"{val:g}"
    return str(val)
```
Python's `g` format auto-strips trailing zeros. This handles floats that appear directly in templates (e.g., `{viability_percent}`).

**Both paths are needed** because some values go through derived computers (formatted in derived.py) while others are raw context values interpolated directly by the text renderer.

---

## 17. Known Design Decisions and Gotchas

1. **Tags are cleared between population instances** (`ctx.clear_tags()` in `_process_population`). Population tags are preserved separately via `ctx.store_population_tags()` for panel-level queries.

2. **Rule evaluation is incremental** — tags set by earlier rules are visible to later rules within the same population. This is essential for chained logic (e.g., restriction → B_CELL_RESTRICTED → FSC comment inclusion).

3. **`render_text()` strips whitespace** — This means helper clause text with intentional leading spaces (like `" and negative for..."`) would lose the space. `_render_clause_text()` detects and restores it.

4. **Multi-space collapse** — `render_text()` collapses multiple spaces to one and strips leading/trailing whitespace. This means empty `{variables}` don't leave double-spaces.

5. **YAML `>` folded strings** — Template text using `>` folding in YAML gets newlines replaced with spaces. This is desired for long comment templates that need to be a single paragraph.

6. **`pct_gated_events` auto-computation** — When `region_pct_total` is set at the region level and `pct_region` is provided at the population level, `pct_gated_events` is auto-computed as `region_pct_total × pct_region / 100`. If `pct_region` is empty/absent, `pct_gated_events` defaults to `region_pct_total` (assumes the population is 100% of the region).

7. **Frontend active marker resolution** — The frontend duplicates some template matching logic (in `getActiveMarkers()` and `matchesPredicate()`) to determine which markers to show without a server round-trip. This must stay in sync with backend logic.

8. **Antibody panel markers are deduplicated across panels** preserving first-seen order. If both acute leukemia and lymphoproliferative panels are selected, shared markers like CD19 only appear once.

9. **`finding_priority` determines mainline sort order** — Lower values = higher clinical priority. Acute leukemia (100) appears before blast findings (350) which appear before panel negatives (750).

10. **The "Comment:" header** is added by `MainTreeRunner._render_comment()`, not by panel runners. Panel runners return comment lines without the header.

---

## 18. Adding a New Panel

To add a new panel:

1. **Create YAML file** in `decision_trees/` following the structure of existing panels
2. **Register the panel** in `Main-tree.txt` under `main_tree.panel_registry`
3. **Define**:
   - `marker_catalog` with all marker IDs and display names
   - `constants` with marker ID lists and display orders
   - `panel` section with regions, populations, templates
4. **Add frontend labels** in `PanelWizard.jsx` (`PANEL_LABELS`, `REGION_LABELS`) and `PopulationForm.jsx` (`getPopulationLabel`)
5. **Run tests**: `cd backend && python -m pytest tests/ -q`

The backend will automatically discover the new YAML file and register the panel.

---

## 19. File Reference

| File | Purpose | Key Functions/Classes |
|---|---|---|
| `backend/src/api.py` | FastAPI endpoints | `generate_report()`, `get_panel_schema()` |
| `backend/src/report_generator.py` | Entry point | `ReportGenerator.generate()`, `get_panel_schema()` |
| `backend/src/main_tree_runner.py` | Case orchestration | `MainTreeRunner.run()`, `_compute_adequate_derived()`, `_render_general/main_line/comment()` |
| `backend/src/panel_runner.py` | Panel execution | `PanelRunner.run()`, `_process_population()`, `_assemble_comments()`, `_resolve_antibody_markers()` |
| `backend/src/context.py` | State management | `EvaluationContext` (scopes, tags, population tracking) |
| `backend/src/tag_engine.py` | Tag computation | `compute_tags()`, `evaluate_rules()`, `apply_normalizations()` |
| `backend/src/template_selector.py` | Template matching | `select_template()` |
| `backend/src/text_renderer.py` | Text interpolation | `render_text()`, `_render_clause_text()`, `_resolve_helper_clause()` |
| `backend/src/derived.py` | Computed values | `compute_derived()`, `compute_marker_list()`, `compute_percent_pick()`, `compute_ratio_text()` |
| `backend/src/predicates.py` | Predicate evaluation | `evaluate_predicate()` + 15 pred_* functions |
| `backend/src/transformers.py` | Output transforms | `deduplicate_markers()`, `markers_to_display()`, `sort_main_line_items()` |
| `backend/src/validators.py` | Validation rules | `run_validations()` |
| `backend/src/panel_loader.py` | YAML loading | `load_main_tree()`, `build_panel_registry()` |
| `backend/src/models.py` | Data models | `CaseInput`, `ReportOutput`, `PanelOutput`, `MainLineItem`, etc. |
| `decision_trees/Main-tree.txt` | Global config | Enums, constants, panel registry, output templates |
| `decision_trees/acute_norm.yaml` | Acute leukemia | Cyto gating, blast types, 20% AML threshold |
| `decision_trees/lympro_tnk_norm.yaml` | Lymphoproliferative | B cell restriction, T cell aberrancy, hairy cell markers |
| `decision_trees/plasma_norm.yaml` | Plasma cell | Outcome-driven, fixed precision, CD56 aberrancy |
| `decision_trees/mds_norm.yaml` | MDS | Simplified blast/monocyte panel |
| `frontend/src/App.jsx` | Main wizard | Step navigation, report generation |
| `frontend/src/components/PanelWizard.jsx` | Panel data entry | Schema loading, region/population management |
| `frontend/src/components/PopulationForm.jsx` | Population entry | Active markers, defaults, marker grid |
| `frontend/src/hooks/useCaseState.js` | State management | localStorage persistence, case building |
