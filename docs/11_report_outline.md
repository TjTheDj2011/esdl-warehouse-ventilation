# Report Outline — ESDL Project 1

**Precedence: the EECE 4101 syllabus governs.** Its nine required sections are
the structure of the report. The TSU College of Engineering technical report
format ([10_TSU_FormatsForReports.doc](10_TSU_FormatsForReports.doc)) and the
ECE design manual are used only to fill what the syllabus leaves unspecified —
page mechanics, preliminaries, citation style, reference matter — and as the
fallback for any question the syllabus does not answer.

Scaled to a 7-week ESDL project. Capstone-only material (signature page,
dedication, resume, hard binding, chapter designations) does not apply.

Reports are **individual**. This is the shared skeleton and shared data; the
writing in each copy is the author's own.

---

## 1. The required structure — from the syllabus

> *"Each report should contain an abstract, introduction, description of the
> project, design objective, design requirements, alternative solutions and
> design procedure, presentation of design testing results, data analysis and
> conclusion."*

| # | Section | What goes in it | Source | State |
|---|---|---|---|---|
| 1 | **Abstract** | What was built, how, the significant result, why it matters. One page, single spaced. | — | Not started |
| 2 | **Introduction** | Subject, purpose, scope, background. The warehouse ventilation problem; why thermal-only control. | [00_project_brief.md](00_project_brief.md) | Material exists |
| 3 | **Description of the project** | The system as built: ESP32, two DS18B20s, three OLED panels, dual-fan diagonal cross-ventilation, buzzer, transparent enclosure. | 00_project_brief, [01_pinout.md](../hardware/01_pinout.md) | Material exists |
| 4 | **Design objective** | Closed-loop automated ventilation with no human intervention; drive the chamber toward the lowest temperature obtainable by air exchange; never take an action that makes it hotter. | 00_project_brief | Have it |
| 5 | **Design requirements** | Specifications and constraints: hysteresis, differential deadband, fail-loud on missing sensor data, 3.3 V throughout, separate motor supply, non-blocking control loop. | Standing constraints in 00_project_brief | **Strong** |
| 6 | **Alternative solutions and design procedure** | Options considered and why each was rejected; the FSM; design process. See §3 below. | [03_control_matrix.md](03_control_matrix.md), git history | Partial — decisions exist, not yet written as analysis |
| 7 | **Presentation of design testing results** | Bench procedure and measured results. All five states verified on hardware; hysteresis engaged 80.8 °F and released 76.9 °F; FAULT verified by physically pulling a sensor. | [../test/bench_log.md](../test/bench_log.md) | **Strong** |
| 8 | **Data analysis** | Heat-source runs: cooling curves, measured vs theoretical time constant, air changes per hour, what the numbers mean. | — | **Missing — needs bench time** |
| 9 | **Conclusion** | What was achieved against each objective; the honest physical limit; what a next revision would change. | — | Not started |

### Two further syllabus requirements, not sections

- *"The design project must include **analytical theories and design
  calculations**."* This is the syllabus's own demand, independent of the
  manual. The repo currently contains **no engineering mathematics** — the one
  serious hole. It belongs inside §6 (design procedure) and §8 (data analysis),
  or as a short section of its own between them.
- *"Graphical presentation ... must be done by computer"* and is graded.
  **Already covered:** schematic, wiring diagram, engineering flowchart and
  Tinkercad layout PDFs.
- Course outcome SLO-5 requires a **cost analysis**. BOM exists; prices do not.

## 2. What the manual supplies — fallback only

The syllabus does not specify page mechanics or preliminaries, so use these.

**Preliminaries (before §1 Abstract):** front cover, title page (counts as page
"i", not numbered), table of contents, list of figures, list of tables,
nomenclature for the equation symbols.

**Reference matter (after §9 Conclusion):** references, appendices. Appendices
carry the firmware listing, host test output and sample calculations.

**Mechanical specification:**

| Item | Requirement |
|---|---|
| Paper | 8½ × 11, single sided, stapled behind cover page, no ragged spiral edges |
| Font | Courier 10 or TMS 12, same processor throughout |
| Spacing | Double, except abstract and long quotations (single) |
| Margins | 1½ in top and left; 1 in bottom and right |
| Pagination | Preliminaries small Roman from "ii", centred bottom. Main text Arabic, centred bottom, no periods or dashes |
| Citations | Square brackets after the last word `[1]`. **Footnotes are not permitted** |

**Grading emphasis**, from the manual's report evaluation form (100 pts) — the
syllabus gives weights between report/presentation/demo but not within the
report, so this is the best guide available:

| | Item | Pts |
|---|---|---|
| 1 | Sufficient introduction | 15 |
| 2 | Thoroughness identifying and defining the subject and **method of solution** | 20 |
| 3 | **Logical and systematic analytical/experimental approach, correctly applied** | **30** |
| 4 | Collection, presentation and **analysis of data** | 10 |
| 5 | Number and quality of **graphs and graphics** | 10 |
| 6 | Strong conclusions with recommendations | 15 |

Items 2, 3 and 4 total **60 of 100**, and all three depend on the mathematics
that does not exist yet. That is why the calculations rank first below.

## 3. Alternative solutions — §6 material

The syllabus wants alternatives judged on social, economic and societal impact
(SLO-2), not only technically. Every row below is a decision this project
actually made, with a genuine rejected option:

| Decision | Alternative rejected | Why |
|---|---|---|
| Brushless computer fans | 130-size brushed motors with propellers | Brush noise corrupts the I2C bus — the largest failure mode in the earlier design. Also quieter, better balanced, easier to mount |
| Three OLED panels | One 16×2 HD44780 LCD | The LCD is 5 V and would need a level shifter beside a 3.3 V MCU, the most dangerous wiring mistake the design allowed. Each value also gets a full panel |
| `SEALED` state added | Reversing the intake fan to block backdraft | Ventilating while outside is hotter *heats* the warehouse. Stopping both fans solves it with no reversing hardware |
| Thermal-only control | Include humidity sensing | Streamlines the control loop and removes a failure mode with no benefit to the stated goal |
| DRV8833 H-bridge | Two logic-level N-MOSFETs | Fans only switch on/off so an H-bridge is not required, but the DRV8833 needs no wiring change and its reverse capability helped bring-up |

Societal and economic angle, stated honestly: the system reduces energy use
against always-on ventilation by running fans only when air exchange actually
cools; parts are commodity and low cost. The physical limit — no refrigeration,
so it cannot go below ambient — belongs in the Conclusion rather than hidden.

## 4. Order of work

1. **The calculations** — required by the syllabus outright, and the largest
   block of marks. Needs no bench time.
2. **Heat-source runs** — gates §8 Data analysis. Needs the enclosure.
3. **Cost analysis** — price the BOM. About an hour.
4. **Write §2–§7** — the material already exists.
5. **Abstract and Conclusion last** — they summarise everything else.
