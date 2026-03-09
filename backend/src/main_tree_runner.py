"""Main tree orchestration — case-level workflow."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .models import CaseInput, MainLineItem, PanelOutput, ReportOutput, ValidationResult
from .panel_runner import PanelRunner
from .template_selector import select_template
from .text_renderer import render_output_lines, render_text
from .transformers import deduplicate_markers, markers_to_display, sort_main_line_items
from .validators import run_validations


class MainTreeRunner:
    """Execute the main tree orchestration for a complete case."""

    def __init__(self, main_tree_spec: dict, panel_registry: dict[str, dict]):
        self.spec = main_tree_spec
        self.panel_registry = panel_registry

    def run(self, case_input: CaseInput) -> ReportOutput:
        ctx = EvaluationContext(self.spec)

        # Push case-level scope
        case_scope: dict[str, Any] = {
            "specimen_type": case_input.specimen_type,
            "clinical_data": case_input.clinical_data,
            "adequacy_status": case_input.adequacy_status,
        }
        if case_input.inadequate_reason:
            case_scope["inadequate_reason"] = case_input.inadequate_reason
        if case_input.viability_percent is not None:
            case_scope["viability_percent"] = case_input.viability_percent
        ctx.push_scope(case_scope)

        # Run main-tree validations
        all_validations: list[ValidationResult] = []
        main_validations = self.spec.get("validations", [])
        all_validations.extend(run_validations(main_validations, ctx))

        # Branch on adequacy
        is_adequate = case_input.adequacy_status == "ADEQUACY_ADEQUATE"
        panel_outputs: list[PanelOutput] = []

        if is_adequate:
            panel_outputs = self._run_panels(case_input, ctx)
            self._compute_adequate_derived(panel_outputs, ctx, case_input)

        # Render outputs
        general = self._render_general(ctx, is_adequate)
        main_line = self._render_main_line(ctx, is_adequate)
        comment = self._render_comment(ctx, is_adequate)

        ctx.pop_scope()

        return ReportOutput(
            general=general,
            main_line=main_line,
            comment=comment,
            validation_errors=all_validations,
        )

    def _run_panels(self, case_input: CaseInput, ctx: EvaluationContext) -> list[PanelOutput]:
        """Invoke panel runners for each selected panel."""
        results: list[PanelOutput] = []
        for panel_input in case_input.selected_panels:
            panel_id = panel_input.panel_id
            panel_spec = self.panel_registry.get(panel_id)
            if not panel_spec:
                continue
            runner = PanelRunner(panel_spec, ctx)
            panel_data = panel_input.model_dump()
            output = runner.run(panel_data)
            results.append(output)
        return results

    def _compute_adequate_derived(
        self, panel_outputs: list[PanelOutput], ctx: EvaluationContext, case_input: CaseInput
    ) -> None:
        """Compute main-tree derived values for adequate cases."""
        # Collect and deduplicate antibody markers
        all_marker_lists = [po.antibody_panel_markers for po in panel_outputs]
        deduped_markers = deduplicate_markers(all_marker_lists)

        # Build merged marker catalog from all panel specs
        panel_catalogs = []
        for po in panel_outputs:
            panel_spec = self.panel_registry.get(po.panel_id, {})
            catalog = panel_spec.get("marker_catalog", {})
            panel_catalogs.append(catalog)

        antibody_display = markers_to_display(deduped_markers, panel_catalogs)

        # Collect all main line items across panels
        all_main_items: list[MainLineItem] = []
        for idx, po in enumerate(panel_outputs):
            for item in po.main_line_items:
                item.selection_order = idx
                all_main_items.append(item)

        ordered_texts = sort_main_line_items(all_main_items)

        # Collect all comment lines
        all_comment_lines: list[str] = []
        for po in panel_outputs:
            all_comment_lines.extend(po.comment_lines)

        # Check viability caution
        viability_threshold = self.spec.get("constants", {}).get(
            "viability_caution_threshold_percent", 50
        )
        if case_input.viability_percent is not None and case_input.viability_percent < viability_threshold:
            precision = self.spec.get("constants", {}).get("percent_precision_decimals", 1)
            v_str = f"{case_input.viability_percent:.{precision}f}"
            caution = (
                f"Given the reduced specimen viability ({v_str}%), "
                f"these results need to be interpreted with caution"
            )
            all_comment_lines.append(caution)

        # Format viability line
        precision = self.spec.get("constants", {}).get("percent_precision_decimals", 1)
        viability_str = ""
        if case_input.viability_percent is not None:
            viability_str = f"{case_input.viability_percent:.{precision}f}"

        # Store in context
        ctx.set_derived("antibody_panel_markers_deduped", deduped_markers)
        ctx.set_derived("antibody_panel_display", antibody_display)
        ctx.set_derived("ordered_main_line_texts", ordered_texts)
        ctx.set_derived("panel_comment_lines", all_comment_lines)
        ctx.set_derived("general_viability_line", f"Viability = {viability_str}%, by using 7-AAD")
        ctx.set_derived("general_antibody_panel_line", f"Antibody Panel Performed: {antibody_display}")

    def _render_general(self, ctx: EvaluationContext, is_adequate: bool) -> list[str]:
        """Render the General section using the YAML template."""
        templates = self.spec.get("main_tree", {}).get("general_generation", {}).get("templates", [])
        if not templates:
            templates = self._get_general_templates()

        # Use template selector if available, otherwise use hardcoded logic
        lines = ["Clinical Pathology Consultation Report"]
        lines.append(f"Specimen: {ctx.get('specimen_type') or ''}")
        lines.append(f"Clinical data: {ctx.get('clinical_data') or ''}")

        if is_adequate or ctx.get("inadequate_reason") == "INADEQUATE_LOW_VIABILITY":
            viability_line = ctx.get("general_viability_line")
            if viability_line:
                lines.append(viability_line)

        if is_adequate:
            antibody_line = ctx.get("general_antibody_panel_line")
            if antibody_line:
                lines.append(antibody_line)

        # Lab disclaimer
        lab_disclaimer = self.spec.get("constants", {}).get("lab_disclaimer_text", "")
        if lab_disclaimer and lab_disclaimer != "__LAB_DISCLAIMER__":
            lines.append(lab_disclaimer)

        return lines

    def _get_general_templates(self):
        return self.spec.get("general_generation", {}).get("templates", [])

    def _render_main_line(self, ctx: EvaluationContext, is_adequate: bool) -> list[str]:
        """Render the Main Line section matching the YAML templates."""
        lines: list[str] = []
        specimen = ctx.get("specimen_type") or ""

        if not is_adequate:
            reason = ctx.get("inadequate_reason")
            if reason == "INADEQUATE_LOW_CELLULAR_EVENTS":
                lines.append(f"{specimen}, flow cytometry analysis:")
                lines.append(
                    "Flow cytometry was attempted but could not be performed due to "
                    "extremely low cellular events in the specimen. "
                    "Examination of the cytospin prepared slide shows no atypical cells"
                )
            elif reason == "INADEQUATE_VISCOUS_SPECIMEN":
                lines.append(f"{specimen}:")
                lines.append("- Unable to perform flow cytometry, see comment")
            elif reason == "INADEQUATE_LOW_VIABILITY":
                viability = ctx.get("viability_percent")
                precision = self.spec.get("constants", {}).get("percent_precision_decimals", 1)
                v_str = f"{viability:.{precision}f}" if viability is not None else "N/A"
                lines.append(f"{specimen}, flow cytometry analysis:")
                lines.append(
                    f"- Flow cytometry analysis is attempted. However, meaningful interpretation "
                    f"is hindered by extensive background staining due to low viability "
                    f"({v_str}% viable cells based on 7-AAD exclusion assay). "
                    f"Correlation with tissue specimen is recommended"
                )
            return lines

        # Adequate path
        lines.append(f"{specimen}, flow cytometry analysis:")
        ordered = ctx.get("ordered_main_line_texts") or []
        for text in ordered:
            lines.append(text)
        terminal = self.spec.get("constants", {}).get("mainline_terminal_text", "See comment")
        lines.append(terminal)
        return lines

    def _render_comment(self, ctx: EvaluationContext, is_adequate: bool) -> list[str]:
        """Render the Comment section matching the YAML templates."""
        if not is_adequate:
            reason = ctx.get("inadequate_reason")
            if reason == "INADEQUATE_VISCOUS_SPECIMEN":
                return [
                    "The received specimen is very viscous. Unable to dilute or process "
                    "for flow cytometry. Consider sending for cytology for creating a "
                    "cell block preparation"
                ]
            return []

        comment_lines = ctx.get("panel_comment_lines") or []
        return list(comment_lines)
