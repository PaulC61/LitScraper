"""Prompt templates for material extraction and verification passes."""

CATALYST_EXTRACTION_PROMPT = """
Extract detailed information about Layered Double Hydroxides (LDHs) used as catalysts for CO2 hydrogenation from the research paper.
Focus on:
1. Synthesis methods (co-precipitation, hydrothermal, etc.) with full conditions (temperature, time, pH, aging, calcination, reduction). If synthesis involves multiple sequential steps (e.g., co-precipitation followed by exfoliation), list every step in order, not just the last one.
2. Metal compositions (M2+ and M3+ metals) and M2+/M3+ ratios.
3. Catalytic test conditions: reaction temperature, pressure, H2/CO2 ratio, feed composition, space velocity (GHSV/WHSV), catalyst mass.
4. Catalytic performance: CO2 conversion (%), selectivities to CO, CH4, methanol, and other products, yields, reaction rates, TOF.

Return one `LDH_materials` entry for every material-condition-measurement triplet in the paper. For a results table with several rows, return several entries and repeat the material, synthesis, and composition metadata in each applicable entry. Never combine several test conditions into one entry. Be exhaustive and include all quantitative values with units. If no values are reported for a specific property, set it to null.

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
1. Study identity fields matching the adsorption table format: material name/label, publication year, title and DOI.
2. Material identity and synthesis: preparation method (list every step in order if synthesis involves multiple sequential steps, e.g., co-precipitation followed by exfoliation), calcination temperature.
3. Material properties: metal composition ratios/doping (M2+, M3+), anions, and impregnation.
4. Adsorption test conditions and outcomes: adsorption temperature, pressure, gas composition, and CO2 adsorption capacity.

Extraction policy:
- Return one `materials` entry for every material-condition-measurement triplet. For a results table with several rows, return several entries and repeat the material, synthesis, and composition metadata in each applicable entry.
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

Current extracted record (JSON):
{material_json}

Source paper content:
---
{document_text}
---
""".strip()


CATALYST_FLAT_EXTRACTION_PROMPT = """
Extract every reported LDH catalyst material-condition-performance result from
the paper.

Return a top-level `rows` list. Each list item MUST represent exactly one
material-condition-performance triplet. Repeat the material's metadata in
each item when the same material was tested under multiple conditions. Scan
every table row and include every distinct temperature, pressure, feed
composition, and performance result. Never put multiple performances in one
item and never return only a representative condition.

If a value is not explicitly reported, set it to null; lists must be empty
when unknown. Do not invent or merge distinct conditions.

Paper content:
---
{document_text}
---
""".strip()


ADSORPTION_FLAT_EXTRACTION_PROMPT = """
Extract every reported LDH adsorption material-condition-measurement result
from the paper.

Return a top-level `rows` list. Each list item MUST represent exactly one
material-condition-measurement triplet. Repeat the material's metadata in
each item when the same material was tested under multiple conditions. Scan
every table row and include every distinct adsorption temperature, pressure,
gas composition, wet/dry state, and capacity result. Never put multiple
measurements in one item and never return only a representative condition.

If a value is not explicitly reported, set it to null; lists must be empty
when unknown. Do not invent or merge distinct conditions.

Paper content:
---
{document_text}
---
""".strip()


USECASE_FLAT_EXTRACTION_PROMPT = """
Identify every distinct Layered Double Hydroxide (LDH) material in the paper
and list all of its use cases.

Return a top-level `rows` list with exactly one item per distinct material.
Never split one material across multiple items and never merge two different
materials into one item.

For each material, fill `use_cases` with every application the paper reports
the material being used for, evaluated for, or explicitly proposed for. Use
short "<role> <target>" phrases, e.g. "adsorbent CO2", "adsorbent heavy
metals", "catalyst CO2 hydrogenation", "paint stabilizer", "drug delivery".
List each distinct use case once and leave the list empty when the paper
reports none.

Also fill the study metadata, synthesis, and composition fields for the
material. If a value is not explicitly reported, set it to null; lists must
be empty when unknown. Do not invent values or infer use cases that the
paper does not state.

Paper content:
---
{document_text}
---
""".strip()


USECASE_FLAT_VERIFICATION_PROMPT = """
Verify this single LDH material row against the source paper. Return exactly
one row object, preserving its material identity. Correct values only when
directly supported by the text, and add any reported use case that is
missing from `use_cases`. Do not merge rows, add other materials, or invent
values or use cases.

Current row:
{row_json}

Source paper:
---
{document_text}
---
""".strip()


USECASE_BATCH_ASSESSMENT_PROMPT = """
You are the batch assessor for LDH use-case extraction records from ONE
paper. The JSON batch below may contain multiple LLM views of the same
material. Consolidate only those duplicates.

Return the same flat `rows` schema with one best-supported record per unique
material, unioning the `use_cases` of the merged duplicates and dropping
repeated or near-identical phrasings of the same use case. For the remaining
fields, retain the most complete directly reported values across the
variants. Never invent values. Do not merge records that differ in material
identity or composition.

Extracted batch JSON:
---
{batch_json}
---
""".strip()


CATALYST_FLAT_VERIFICATION_PROMPT = """
Verify this single catalyst material-condition-performance row against the
source paper. Return exactly one row object, preserving its material and
condition identity. Correct values only when directly supported by the text.
Do not add another condition, merge rows, or invent values.

Current row:
{row_json}

Source paper:
---
{document_text}
---
""".strip()


ADSORPTION_FLAT_VERIFICATION_PROMPT = """
Verify this single adsorption material-condition-measurement row against the
source paper. Return exactly one row object, preserving its material and
condition identity. Correct values only when directly supported by the text.
Do not add another condition, merge rows, or invent values.

Current row:
{row_json}

Source paper:
---
{document_text}
---
""".strip()


CATALYST_BATCH_ASSESSMENT_PROMPT = """
You are the batch assessor for catalyst extraction records from ONE paper.
The JSON batch below may contain multiple LLM views of the same
material-condition-measurement triplet. Consolidate only those duplicates.

Return the same flat `rows` schema with one best-supported record per unique triplet.
For duplicates, retain the most complete directly reported values across the
variants. Never invent values. Do not merge records that differ in material
identity/composition, reaction condition (temperature, pressure, or feed),
or measured performance. Preserve every genuinely distinct test condition.

Extracted batch JSON:
---
{batch_json}
---
""".strip()


ADSORPTION_BATCH_ASSESSMENT_PROMPT = """
You are the batch assessor for adsorption extraction records from ONE paper.
The JSON batch below may contain multiple LLM views of the same
material-condition-measurement triplet. Consolidate only those duplicates.

Return the same flat `rows` schema with one best-supported record per unique triplet.
For duplicates, retain the most complete directly reported values across the
variants. Never invent values. Do not merge records that differ in material
identity/composition, adsorption condition (temperature, pressure, gas, or
wet/dry state), or measured capacity. Preserve every genuinely distinct test
condition.

Extracted batch JSON:
---
{batch_json}
---
""".strip()
