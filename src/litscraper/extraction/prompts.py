"""Prompt templates for material extraction and verification passes."""

CATALYST_EXTRACTION_PROMPT = """
Extract detailed information about Layered Double Hydroxides (LDHs) used as catalysts for CO2 hydrogenation from the research paper.
Focus on:
1. Synthesis methods (co-precipitation, hydrothermal, etc.) with full conditions (temperature, time, pH, aging, calcination, reduction).
2. Metal compositions (M2+ and M3+ metals) and M2+/M3+ ratios.
3. Catalytic test conditions: reaction temperature, pressure, H2/CO2 ratio, feed composition, space velocity (GHSV/WHSV), catalyst mass.
4. Catalytic performance: CO2 conversion (%), selectivities to CO, CH4, methanol, and other products, yields, reaction rates, TOF.

Extract data for every distinct LDH material which receives a unique identifier (including different metal ratios and synthesis conditions).
Be exhaustive and include all quantitative values with units. If no values are reported for a specific property, set it to null.

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
1. Study identity fields matching the adsorption table format: abstract and DOI.
2. Material identity and synthesis: preparation method, calcination temperature.
3. Material properties: metal composition ratios/doping (M2+, M3+), anions, and impregnation.
4. Adsorption test conditions and outcomes: adsorption temperature, pressure, gas composition, and CO2 adsorption capacity.

Extraction policy:
- Extract every distinct LDH material and all reported adsorption-condition rows.
- Keep units aligned to the table columns: temperature in C, pressure in bar, capacity in mmol/g.
- If a value is not explicitly reported in the paper, set it to null.
- Avoid inference and do not invent values.

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

Current extracted record (JSON):
{material_json}

Source paper content:
---
{document_text}
---
""".strip()
