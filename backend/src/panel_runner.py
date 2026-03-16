"""Generic panel execution engine."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .derived import compute_derived
from .models import MainLineItem, PanelOutput, ValidationResult
from .predicates import evaluate_predicate
from .tag_engine import apply_normalizations, compute_tags, evaluate_rules
from .template_selector import select_template
from .text_renderer import render_text
from .validators import run_validations


class PanelRunner:
    """Execute a panel rule pack and produce PanelOutput."""

    def __init__(self, panel_spec: dict, ctx: EvaluationContext):
        self.spec = panel_spec
        self.ctx = ctx
        self.panel_section = panel_spec.get("panel", {})
        self.panel_id = self.panel_section.get("panel_id", "")

    def run(self, panel_input: dict) -> PanelOutput:
        """Execute the panel and return structured outputs."""
        ctx = self.ctx
        ctx.set_current_panel_spec(self.spec)
        ctx.clear_population_state()

        # Push panel-level scope with panel fields
        panel_scope: dict[str, Any] = {}
        panel_scope.update(panel_input.get("fields", {}))
        ctx.push_scope(panel_scope)

        # 1. Resolve antibody panel markers
        antibody_markers = self._resolve_antibody_markers()

        # 2. Process regions
        all_comment_lines: list[str] = []
        all_main_line_items: list[MainLineItem] = []
        all_validations: list[ValidationResult] = []

        regions_spec = self.panel_section.get("regions", [])
        regions_input = panel_input.get("regions", [])

        # Build region input lookup
        region_input_map: dict[str, dict] = {}
        for ri in regions_input:
            rid = ri.get("region_id", "") if isinstance(ri, dict) else ri.region_id
            region_input_map[rid] = ri if isinstance(ri, dict) else ri.model_dump()

        # Track region comments and population comments separately for ordering
        region_comments: dict[str, list[str]] = {}
        population_comments: dict[str, list[list[str]]] = {}  # pop_type -> [instance_comments]

        for region_spec in regions_spec:
            region_id = region_spec.get("region_id", "")
            region_input = region_input_map.get(region_id, {})
            region_fields = region_input.get("fields", {})

            # Push region scope
            region_scope = {"_current_region": region_id}
            region_scope.update(region_fields)
            ctx.push_scope(region_scope)

            # Generate region-level comment lines
            region_comment_templates = region_spec.get("region_comment_line_generation", {}).get("templates", [])
            region_cmt_lines = []
            if region_comment_templates:
                tmpl = select_template(region_comment_templates, ctx)
                if tmpl and tmpl.get("text"):
                    rendered = render_text(tmpl["text"], ctx)
                    if rendered:
                        region_cmt_lines.append(rendered)
            region_comments[region_id] = region_cmt_lines

            # Process populations
            populations_spec = region_spec.get("populations", [])
            populations_input = region_input.get("populations", [])

            # Group input populations by population_id
            pop_input_groups: dict[str, list[dict]] = {}
            for pi in populations_input:
                pid = pi.get("population_id", "") if isinstance(pi, dict) else pi.population_id
                pop_input_groups.setdefault(pid, []).append(
                    pi if isinstance(pi, dict) else pi.model_dump()
                )

            for pop_spec in populations_spec:
                pop_id = pop_spec.get("population_id", "")
                pop_instances = pop_input_groups.get(pop_id, [])

                if pop_id not in population_comments:
                    population_comments[pop_id] = []

                for instance_idx, pop_input in enumerate(pop_instances):
                    instance_comments, instance_main_items, instance_validations = (
                        self._process_population(pop_spec, pop_input, instance_idx)
                    )
                    population_comments[pop_id].append(instance_comments)
                    all_main_line_items.extend(instance_main_items)
                    all_validations.extend(instance_validations)

            ctx.pop_scope()  # region scope

        # 3. Assemble comment lines in configured order
        comment_order_spec = self.panel_section.get("comment_lines_generation", {})
        order = comment_order_spec.get("order", [])
        all_comment_lines = self._assemble_comments(order, region_comments, population_comments)

        # 4. Assemble main line items via panel-level generation
        main_line_gen = self.panel_section.get("main_line_items_generation", {})
        final_main_items = self._assemble_main_line_items(main_line_gen, all_main_line_items)

        ctx.pop_scope()  # panel scope
        ctx.set_current_panel_spec(None)

        output = PanelOutput(
            panel_id=self.panel_id,
            antibody_panel_markers=antibody_markers,
            comment_lines=all_comment_lines,
            main_line_items=final_main_items,
        )
        return output

    def _resolve_antibody_markers(self) -> list[str]:
        """Select antibody panel markers based on panel-level conditions."""
        gen = self.panel_section.get("antibody_panel_markers_generation", {})
        templates = gen.get("templates", [])
        tmpl = select_template(templates, self.ctx)
        if tmpl:
            markers_ref = tmpl.get("markers_ref", "")
            markers = self.ctx.get_constant(markers_ref)
            if markers:
                return list(markers)
        return []

    def _process_population(
        self, pop_spec: dict, pop_input: dict, instance_idx: int
    ) -> tuple[list[str], list[MainLineItem], list[ValidationResult]]:
        """Process a single population instance."""
        ctx = self.ctx
        pop_id = pop_spec.get("population_id", "")
        pop_fields = pop_input.get("fields", {})
        marker_states_raw = pop_input.get("marker_states", [])

        # Convert marker states to list of dicts
        marker_states = []
        for ms in marker_states_raw:
            if isinstance(ms, dict):
                marker_states.append(ms)
            else:
                marker_states.append({"marker_id": ms.marker_id, "state": ms.state})

        # Push population scope
        pop_scope: dict[str, Any] = {
            "_current_population": pop_id,
            "_instance_idx": instance_idx,
        }
        pop_scope.update(pop_fields)
        pop_scope["marker_states"] = marker_states

        # Auto-compute pct_gated_events from region_pct_total and pct_region
        region_pct = ctx.get("region_pct_total")
        if region_pct is not None:
            try:
                rp = float(region_pct)
                pct_region = pop_scope.get("pct_region")
                if pct_region is not None and pct_region != "":
                    pop_scope["pct_gated_events"] = round(rp * float(pct_region) / 100, 2)
                elif "pct_gated_events" not in pop_scope or pop_scope.get("pct_gated_events") in (None, ""):
                    pop_scope["pct_gated_events"] = rp
            except (ValueError, TypeError):
                pass

        ctx.push_scope(pop_scope)

        # Determine active markers
        active_markers_gen = pop_spec.get("active_markers_generation", {})
        active_templates = active_markers_gen.get("templates", [])
        if active_templates:
            tmpl = select_template(active_templates, ctx)
            if tmpl:
                markers_ref = tmpl.get("markers_ref", "")
                active = ctx.get_constant(markers_ref)
                if active:
                    ctx.set_derived("_active_markers", set(active))

        # Compute tags (if the population has tags spec)
        tags = compute_tags(pop_spec, ctx)
        ctx.add_tags(tags)

        # Evaluate rules
        rules = pop_spec.get("rules", [])
        if rules:
            rule_tags = evaluate_rules(rules, ctx)
            ctx.add_tags(rule_tags)
            tags.update(rule_tags)

        # Apply normalizations
        normalizations = pop_spec.get("normalizations", [])
        if normalizations:
            apply_normalizations(normalizations, ctx)

        # Compute derived values
        derived_specs = pop_spec.get("derived", [])
        for d_spec in derived_specs:
            d_id = d_spec.get("id", "")
            value = compute_derived(d_spec, ctx)
            ctx.set_derived(d_id, value)

        # Store population tags for panel-level queries
        ctx.store_population_tags(pop_id, ctx.get_tags())

        # Run validations
        validations = pop_spec.get("validations", [])
        validation_results = run_validations(validations, ctx)

        # Generate comment line
        comment_gen = pop_spec.get("comment_line_generation", {})
        comment_templates = comment_gen.get("templates", [])
        helper_clauses = comment_gen.get("helper_clauses")
        comment_lines = []
        tmpl = select_template(comment_templates, ctx)
        if tmpl and tmpl.get("text"):
            rendered = render_text(tmpl["text"], ctx, helper_clauses)
            if rendered:
                comment_lines.append(rendered)

        # Generate main line items
        main_gen = pop_spec.get("main_line_item_generation", {})
        main_templates = main_gen.get("templates", [])
        main_items: list[MainLineItem] = []
        tmpl = select_template(main_templates, ctx)
        if tmpl and tmpl.get("item"):
            item_spec = tmpl["item"]
            item_text = render_text(item_spec.get("text", ""), ctx, helper_clauses)
            main_item = MainLineItem(
                text=item_text,
                finding_priority=item_spec.get("finding_priority", 750),
                finding_class=item_spec.get("finding_class", ""),
                panel_id=item_spec.get("panel_id", self.panel_id),
                population_id=item_spec.get("population_id", pop_id),
                selection_order=instance_idx,
            )
            main_items.append(main_item)

        # Store outputs for panel-level collection
        ctx.store_population_output(pop_id, "comment_line", comment_lines)
        ctx.store_population_output(pop_id, "main_line_item", main_items)

        # Clear tags for next population instance
        ctx.clear_tags()
        ctx.pop_scope()

        return comment_lines, main_items, validation_results

    def _assemble_comments(
        self,
        order: list,
        region_comments: dict[str, list[str]],
        population_comments: dict[str, list[list[str]]],
    ) -> list[str]:
        """Assemble comment lines in the configured order."""
        result: list[str] = []
        for entry in order:
            if isinstance(entry, str):
                if entry == "region_comment":
                    for lines in region_comments.values():
                        result.extend(lines)
            elif isinstance(entry, dict):
                pop_type = entry.get("populations_of_type", "")
                if pop_type and pop_type in population_comments:
                    for instance_lines in population_comments[pop_type]:
                        result.extend(instance_lines)
        return result

    def _assemble_main_line_items(
        self, main_line_gen: dict, collected_items: list[MainLineItem]
    ) -> list[MainLineItem]:
        """Assemble panel-level main line items."""
        ctx = self.ctx

        # Compute panel-level derived values for main line generation
        derived_specs = main_line_gen.get("derived", [])
        for d_spec in derived_specs:
            d_id = d_spec.get("id", "")
            value = compute_derived(d_spec, ctx)
            ctx.set_derived(d_id, value)

        templates = main_line_gen.get("templates", [])
        tmpl = select_template(templates, ctx)
        if not tmpl:
            return collected_items

        # Handle output_items_from (pass through collected items)
        if "output_items_from" in tmpl:
            result: list[MainLineItem] = []
            for list_name in tmpl["output_items_from"]:
                items = ctx.get(list_name)
                if items:
                    for item in items:
                        if isinstance(item, MainLineItem):
                            result.append(item)
                        elif isinstance(item, dict):
                            result.append(MainLineItem(**item))
            return result if result else collected_items

        # Handle output_items (static items)
        if "output_items" in tmpl:
            return [
                MainLineItem(
                    text=item.get("text", ""),
                    finding_priority=item.get("finding_priority", 750),
                    finding_class=item.get("finding_class", ""),
                    panel_id=item.get("panel_id", self.panel_id),
                )
                for item in tmpl["output_items"]
            ]

        return collected_items
