---
name: reference-driven-design
description: >-
  Mandatory reference-first art direction and design workflow for all visual and graphic design tasks
  (logos, book covers, presentations/pitch decks, editorial layouts in InDesign, vector artwork in Illustrator,
  brand identity, posters, banners, packaging, and web/UI design). Always activate this skill BEFORE creating
  any design so that every concept is grounded in real-world references from Behance, Pinterest, Dribbble,
  Fonts In Use, Pentagram, BP&O, and Awwwards, visually displayed as real images to the user, and explicitly
  approved by the user before executing the design.
---

# Reference-Driven Design (Референс-ориентированный дизайн с показом картинок)

## Core Philosophy: Never Design in a Vacuum & Always Show Visual References First

**STRICT MANDATE:**
1. You must **NEVER** invent a visual design (logo, book cover, presentation, poster, editorial layout, brand identity, banner, or UI) purely from abstract imagination.
2. You must **ALWAYS download and visually display the real reference images** to the user so they can see with their own eyes what references you selected.
3. You must **NEVER** start generating final images, writing UI/slide code, or building layouts in Illustrator/InDesign **until the user sees the reference images and explicitly approves them**.

---

## Mandatory 5-Step Workflow (with Visual Moodboard & Approval Gate)

Whenever the user asks for any design artifact, execute these phases in strict sequence. **STOP at Phase 3 (Approval Gate) and wait for the user's answer before executing Phase 4 & 5.**

### Phase 1: Fetch Real Visual References & Curated Font Pairings (`scripts/fetch_references.py`)

Before proposing a concept or touching any design tool, run the built-in reference & typography fetcher script via `run_command` to download **4 real reference images** from Behance, Pinterest, BP&O, Fonts In Use, Dribbble, or Awwwards AND generate **3 visual Font Pairing Specimen Cards** (rendered with real `.ttf` fonts from Google Fonts in Cyrillic & Latin) directly into the current conversation's artifact directory (`<artifact_dir>`):

```powershell
python "C:\Users\rusla\.gemini\config\skills\reference-driven-design\scripts\fetch_references.py" `
  -q "behance.net <topic/industry> <design medium> <style>" `
  -q "pinterest.com <topic/industry> <design medium> typography" `
  --sample-title "<Заголовок под тему задачи>" `
  --sample-sub "<Подзаголовок под тему задачи>" `
  --font-presets "editorial,literary,avantgarde" `
  -o "<artifact_dir>" `
  -c 4 `
  -p "ref"
```
*(Available `--font-presets`: `editorial` [Cormorant Garamond + Manrope], `literary` [Playfair Display + Golos Text], `avantgarde` [Unbounded + Onest], `sculptural` [Forum + Manrope], `swiss` [Oswald + Inter]).*

What this script automatically produces in `<artifact_dir>`:
1. `ref_1.jpg` .. `ref_4.jpg` & `ref_moodboard.jpg` — the individual high-res reference images and stitched 2×2 visual moodboard sheet (`REF #1` .. `REF #4`).
2. `ref_font_1.jpg` .. `ref_font_3.jpg` & `ref_fonts_sheet.jpg` — real typographic specimen cards (`FONT #A`, `FONT #B`, `FONT #C`) rendered with your task's sample headline in Cyrillic/Latin.
3. `ref_widget.html` — a self-contained interactive tabbed HTML widget (`1. Визуальные референсы` / `2. Шрифтовые пары`) ready to render inline in chat via `<agent-embed>`.
4. `ref_manifest.json` — metadata with project titles, source page URLs (`purl`), Google Fonts CSS imports, and local paths.

**Inspect the images yourself:** Always call `view_file` on `<artifact_dir>/ref_moodboard.jpg` and `<artifact_dir>/ref_fonts_sheet.jpg` immediately after running the script so you visually see the exact composition, typography, and colors!

---

### Phase 2: Visually Display the References + Font Pairings to the User

You **MUST** show both the downloaded reference images and the curated font pairing specimens to the user so they see them with their own eyes in the UI:

1. **Create a Visual Reference & Typography Artifact (`<artifact_dir>/visual_references.md`)** using `write_to_file` with `ArtifactMetadata: {UserFacing: true, RequestFeedback: true, Summary: "Визуальный мудборд референсов и витрина шрифтовых пар"}` containing:
   - The stitched moodboard image: `![Визуальный мудборд референсов](/C:/Users/rusla/.gemini/antigravity/brain/<conversation-id>/ref_moodboard.jpg)`
   - The stitched font pairings sheet: `![Витрина шрифтовых пар](/C:/Users/rusla/.gemini/antigravity/brain/<conversation-id>/ref_fonts_sheet.jpg)`
   - A ````carousel` with `ref_1.jpg`..`ref_4.jpg` and `ref_font_1.jpg`..`ref_font_3.jpg`
   - A brief DNA breakdown of each reference and font pairing.
2. **Also render the inline tabbed widget in your chat message**:
   - Include `<agent-embed src="file:///C:/Users/rusla/.gemini/antigravity/brain/<conversation-id>/ref_widget.html"></agent-embed>` in your chat response so the user can click between the **Референсы** and **Шрифтовые пары** tabs directly inside the chat stream!

---

### Phase 3: MANDATORY USER APPROVAL GATE (Согласование картинок-референсов и формата)

**🛑 HARD STOP — DO NOT BUILD OR GENERATE ANYTHING YET!**

End your message in Phase 2 by showing the visual references (`<agent-embed>` + link to `visual_references.md`) and asking the user directly in chat:
> *«Вот реальные визуальные референсы (REF #1 – #4) и шрифтовые пары (FONT #A – #C). Какие из них тебе нравятся по стилю и композиции? Берем их в работу, или поищем другие?»*
> *(Если задача — презентация и пользователь еще не указал формат, обязательно добавь: «В каком формате собрать итоговую презентацию — **PDF (`.pdf`)** или **PowerPoint (`.pptx`)** (или сразу в обоих)?»)*

- **Note on `ask_question`**: Do **NOT** call `ask_question` in the same turn before the user has seen your chat message and images (because `ask_question` blocks the turn before your message/images render!). Instead, simply output the images + text question and end your turn so the user can look at the pictures with their own eyes and reply!
- **If the user says NO ("не нравится / ищи еще")**: Run `fetch_references.py` again with new search queries/styles (using a new prefix like `-p "ref_v2"`), show the new images, and ask again.
- **If the user says YES ("да, берем" / "нравится #1 и #4")**: Proceed to Phase 4 & 5!

---

### Phase 4: Design System Extraction + Creative Synthesis (Строгая дизайн-система + Творческая фантазия)

Once the user approves the visual references and font pairing, apply the **"Same Studio, New Project" (70% System / 30% Imagination) Principle**:
Imagine you are the art director of the studio that created the reference, designing a **brand-new, original project** within the same design system.

1. **What you lock in STRICTLY from the Reference (The Design System)**:
   - **Spatial System & Spacing**: Margins, column grid, negative-space-to-content ratio («воздух»), padding rhythm, border widths (`1px` hairlines vs. `3px` bars), and corner radii.
   - **Color System**: Exact color tokens, surface contrast polarity, and dominant/secondary/accent color proportions.
   - **Typographic System**: The approved font pairing, scale hierarchy, line-height, tracking, and running metadata/index logic.
2. **Where you MUST use your own creative imagination (Original Art Direction)**:
   - **DO NOT clone the reference's literal blocks 1:1** (e.g., never copy irrelevant phone mockups, literal `"A | B | C"` or `"ON & OFF"` labels, or identical block arrangements just because they were on the reference).
   - **Invent fresh compositions and visual metaphors** inside the reference's grid and spacing rules: design original diagrams, expressive photo crops, custom thematic infographics, dynamic typographic focal points, and bespoke layouts that organically tell the story of the user's specific topic.

---

### Phase 5: Tool-Specific Execution (Реализация в рамках дизайн-системы)

Translate the extracted Design System + your original creative layouts into the target deliverable:
- **When building Presentations / Pitch Decks (`.pdf` or `.pptx` — NEVER just an HTML site)**:
  - **Deliverable Rule**: Presentations must **always** be delivered as a **PDF (`.pdf`)** or **PowerPoint (`.pptx`)** file (or both, depending on what the user requested) — **never** leave a presentation as just an HTML webpage.
  - Build the 16:9 vector slide source (`.slide` sections with Google Fonts and custom SVG diagrams) and run the built-in exporter script `scripts/export_presentation.py` via `run_command`:
    ```powershell
    python "C:\Users\rusla\.gemini\config\skills\reference-driven-design\scripts\export_presentation.py" `
      --input "<slide_source.html>" `
      --pdf "<output_presentation.pdf>" `
      --pptx "<output_presentation.pptx>" `
      --preview "<artifact_dir>/slides_export_preview.jpg" `
      --slides 10 `
      --base-width 800
    ```
    *(Pass `--pdf`, `--pptx`, or both according to the user's preference, and always inspect `<artifact_dir>/slides_export_preview.jpg` with `view_file` to verify that every slide rendered without clipping or layout issues!)*
- **When using `generate_image`**: Pass the 1–3 user-approved reference images (`<artifact_dir>/ref_X.jpg`) into `ImagePaths`, and explicitly instruct the prompt to **adopt the reference's color palette, grid discipline, spacing, and typography style while inventing a fresh, original composition and visual metaphor** for the subject (not a literal 1:1 trace of the reference's objects).
- **When writing Websites / Landing Pages (HTML/CSS/JS)**: Lock in the reference's CSS tokens (`--bg`, `--ink`, `--accent`, grid columns, spacing scale, border styles, font pairings), and compose original, varied section layouts tailored to the content.
- **When using Illustrator / InDesign MCP**: Lock in the reference's document grid, margins, swatches, and paragraph styles, then compose an original graphic layout within that grid and export to `.pdf`.

---

## Anti-Patterns Checklist (Чего делать категорически нельзя)

- ❌ **NO Execution Without Approval**: Never generate the final design before the user has seen the reference images + font pairings and approved them.
- ❌ **NO Presentations Delivered as Websites**: When the user asks for a presentation, never deliver an HTML website as the final result — always export and deliver `.pdf` and/or `.pptx` (as requested by the user) using `scripts/export_presentation.py`.
- ❌ **NO Blind 1:1 Layout Cloning**: Never mindlessly copy the exact blocks, dummy widgets (like random phone frames), or literal text labels of the reference. Extract the **design system** (grid, spacing, colors, typography, micro-details) and invent **original compositions** inside those rules.
- ❌ **NO Breaking the Design System**: Your creative imagination must operate *inside* the reference's spacing, grid, color ratios, and typographic rules — never drift back into generic AI gradients or unrelated styles.
