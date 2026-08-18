"""Prompt templates for material extraction and verification passes."""

CATALYST_EXTRACTION_PROMPT = """
Extract detailed information about Layered Double Hydroxides (LDHs) used as catalysts for CO2 hydrogenation from the research paper.
Focus on:
1. Synthesis methods (co-precipitation, hydrothermal, etc.) with full conditions (temperature, time, pH, aging, calcination, reduction). If synthesis involves multiple sequential steps (e.g., co-precipitation followed by exfoliation), list every step in order, not just the last one.
2. Metal compositions (M2+ and M3+ metals) and M2+/M3+ ratios.
3. Catalytic test conditions: reaction temperature, pressure, H2/CO2 ratio, feed composition, space velocity (GHSV/WHSV), catalyst mass.
4. Catalytic performance: CO2 conversion (%), selectivities to CO, CH4, methanol, and other products, yields, reaction rates, TOF.

Extract data for every distinct LDH material which receives a unique identifier (including different metal ratios and synthesis conditions).
Be exhaustive and include all quantitative values with units. If no values are reported for a specific property, set it to null.

IMPORTANT -- multi-row materials: many papers test the same material under several reaction conditions (e.g. a temperature-scan or pressure-scan table). In that case, `catalytic_performances` for that material MUST contain one entry per condition/row, not a single averaged or "most representative" entry. Scan every row of every results table and add a separate entry for each one, even if several rows share the same material.

Paper content (parsed from PDF via GROBID, includes both body text and tables):
---
{document_text}
---
""".strip()


CATALYST_VERIFICATION_PROMPT = """
You are validating one previously extracted LDH material against the original paper text.

Task:
1. Review the JSON for this material.
2. Re-check the source text and fill any missing details that are explicitly reported.
3. Correct incorrect values if contradicted by the source text.
4. Keep values as null when not explicitly present in the source text.

Hard constraints to minimize hallucination:
- Do not invent values, units, conditions, compositions, or IDs.
- Do not infer from unrelated materials in the same paper.
- Preserve the same material identity and output only one material in the exact schema.
- Numeric fields must contain numbers only when directly supported by source text.
- Lists must be empty lists when unknown (never null for list fields).
- Do not drop or merge existing `catalytic_performances` entries: if the input JSON already lists N conditions, your output must still have at least N entries (add missing ones found in the source text, never collapse distinct conditions into one).

Current material JSON:
{material_json}

Source paper content:
---
{document_text}
---
""".strip()


ADSORPTION_EXTRACTION_PROMPT = """
Extract detailed information about Layered Double Hydroxides (LDHs) used for CO2 adsorption from the research paper.

Focus on:
1. Study identity fields matching the adsorption table format: title and DOI.
2. Material identity and synthesis: preparation method (list every step in order if synthesis involves multiple sequential steps, e.g., co-precipitation followed by exfoliation), calcination temperature.
3. Material properties: metal composition ratios/doping (M2+, M3+), anions, and impregnation.
4. Adsorption test conditions and outcomes: adsorption temperature, pressure, gas composition, and CO2 adsorption capacity.

Extraction policy:
- Extract every distinct LDH material and all reported adsorption-condition rows.
- Keep units aligned to the table columns: temperature in C, pressure in bar, capacity in mmol/g.
- If a value is not explicitly reported in the paper, set it to null.
- Avoid inference and do not invent values.

IMPORTANT -- multi-row materials: many papers test the same material under several adsorption conditions (e.g. a temperature-scan or pressure-scan table). In that case, `adsorption_measurements` for that material MUST contain one entry per condition/row, not a single averaged or "most representative" entry. Scan every row of every results table and add a separate entry for each one, even if several rows share the same material.

Paper content (parsed from PDF via GROBID, includes both body text and tables):
---
{document_text}
---
""".strip()


ADSORPTION_VERIFICATION_PROMPT = """
You are validating one previously extracted LDH adsorption material against the original paper text.

Task:
1. Review the JSON for this material.
2. Re-check the source text and fill any missing details that are explicitly reported.
3. Correct incorrect values if contradicted by the source text.
4. Keep values as null when not explicitly present in the source text.

Hard constraints to minimize hallucination:
- Do not invent values, units, conditions, composition ratios, or impregnation details.
- Do not infer from unrelated materials in the same paper.
- Preserve the same material identity and output only one material in the exact schema.
- Numeric fields must contain numbers only when directly supported by source text.
- Output adsorption_measurements as an empty list when no measurement rows are explicitly reported.
- Do not drop or merge existing `adsorption_measurements` entries: if the input JSON already lists N conditions, your output must still have at least N entries (add missing ones found in the source text, never collapse distinct conditions into one).

Current extracted record (JSON):
{material_json}

Source paper content:
---
{document_text}
---
""".strip()
