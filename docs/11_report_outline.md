# Report Outline — ESDL Project 1

Structure and flow follow the TSU College of Engineering technical report
format ([10_TSU_FormatsForReports.doc](10_TSU_FormatsForReports.doc)) and the
ECE Capstone Design Manual's arrangement, **scaled to a 7-week ESDL project**
rather than a two-semester capstone. Capstone-only preliminaries — signature
page, dedication, resume, hard binding — are omitted.

Reports are **individual**. This is the shared skeleton and the shared data;
the writing in each copy is the author's own.

---

## How it is graded

Two rubrics exist and they agree on where the marks are.

**Report evaluation form (100 pts):**

| | Item | Pts |
|---|---|---|
| 1 | Sufficient introduction | 15 |
| 2 | Thoroughness identifying and defining the subject and **method of solution** | 20 |
| 3 | **Logical and systematic analytical/experimental approach, correctly applied** | **30** |
| 4 | Collection, presentation and **analysis of data** | 10 |
| 5 | Sufficient number and quality of **graphs and graphics** | 10 |
| 6 | Strong conclusions with recommendations | 15 |

**Format document split:** technical content 65, written content and form 35.

Both put the weight in the same place. **Item 3 alone is 30 points** — the
largest single item — and items 2, 3 and 4 together are 60. Analysis, not
prose, is where this report is won. The repo currently has no engineering
mathematics at all, which is the one serious hole left.

Graphs and graphics is 10 points and we are already covered: schematic, wiring
diagram, engineering flowchart and Tinkercad layout are all computer-produced.

## Mechanical specification

| Item | Requirement |
|---|---|
| Paper | 8½ × 11, single sided, stapled behind cover page, no ragged spiral edges |
| Font | Courier 10 or TMS 12, same processor throughout |
| Spacing | Double, except abstract and long quotations (single) |
| Margins | 1½ in top and left; 1 in bottom and right. **2 in top on a chapter's first page** |
| Pagination | Title page is "i", unnumbered. Preliminaries small Roman from "ii", centred bottom. Main text Arabic, centred bottom, no periods or dashes |
| Citations | Square brackets after the last word of the citation `[1]`. **Footnotes are not permitted** |
| Chapters | Designated by Roman numerals |

---

## Arrangement

### Preliminaries
1. Clear front cover
2. Title page — *page i, not numbered*
3. Abstract — one page, single spaced
4. Table of Contents
5. List of Figures
6. List of Tables
7. Nomenclature — symbols used in the equations *(optional, but we have enough to justify it)*

### Text
8. Introduction
9. Theory
10. Design and Implementation
11. Testing and Results
12. Data Analysis
13. Conclusions and Recommendations

### Reference matter
14. References
15. Appendices

---

## What goes in each section

The syllabus lists nine content items; they map into the structure above rather
than being sections of their own.

| Section | Contents | Source | State |
|---|---|---|---|
| **Abstract** | What was built, how, the significant result, why it matters. One page. | — | Not started |
| **Introduction** | Subject, purpose, scope, problem statement, background. The warehouse ventilation problem and why thermal-only control. Last paragraph summarises each following section. Covers rubric item 1 (15 pts). | [00_project_brief.md](00_project_brief.md) | Have the material |
| **Design objective & requirements** | Inside Introduction. Goal, objectives, specifications, constraints. | 00_project_brief, standing constraints | Have it |
| **Theory** | **The mathematics.** Airflow, thermal load, time constant, hysteresis derivation, power budget, the ambient floor. Rubric item 3 (30 pts) lives here. | — | **Missing — top priority** |
| **Design and Implementation** | Alternative solutions and why each was rejected; the FSM; hardware architecture; pin map; non-blocking scheduler. Rubric item 2 (20 pts). | 01_pinout, 03_control_matrix, git history | Partial — decisions exist, not written as alternatives analysis |
| **Testing and Results** | Bench procedure and measured results. All five states verified, hysteresis engaged 80.8 / released 76.9, FAULT by pulling a sensor. | [../test/bench_log.md](../test/bench_log.md) | **Strong** |
| **Data Analysis** | Heat-source runs: cooling curves, measured vs theoretical τ, air changes per hour. Rubric item 4 (10 pts). | — | **Missing — needs bench time** |
| **Conclusions & Recommendations** | What was achieved against the objectives; the honest physical limit; what a next revision would change. Rubric item 6 (15 pts). | — | Not started |
| **Cost analysis** | Required by course outcome SLO-5. Put it in Design and Implementation or an appendix. | [../hardware/03_physical_build.md](../hardware/03_physical_build.md) | **Missing** — BOM exists, prices do not |
| **Appendices** | Full firmware listing, host test output, sample calculations. | `firmware/`, `test/` | Have it |
| **References** | Datasheets (DS18B20, DRV8833, SSD1306, ESP32-WROOM-32), any standards cited. | — | Not started |

## Alternative solutions — what to write

Rubric item 2 wants the *method of solution*, and the syllabus wants
alternatives judged on social, economic and societal impact, not only
technically. Real decisions from this project, all with genuine rejected
options:

| Decision | Alternatives considered | Why the choice |
|---|---|---|
| Brushless computer fans | 130-size brushed motors with propellers | Brush noise corrupts the I2C bus; brushless removes the single largest failure mode. Also quieter and easier to mount |
| Three OLED panels | One 16×2 HD44780 LCD | LCD is 5 V and would require a level shifter next to a 3.3 V MCU — the most dangerous wiring mistake the design allowed. Each value also gets a whole panel |
| `SEALED` state added | Reversing the intake fan to block backdraft | Ventilating while outside is hotter *heats* the warehouse. Stopping both fans solves it with no reversing hardware |
| Thermal-only control | Include humidity | Streamlines the control loop and removes a failure mode with no benefit to the stated goal |
| DRV8833 H-bridge | Two logic-level N-MOSFETs | Fans only switch on/off so an H-bridge is not required, but the DRV8833 needs no wiring change and its reverse capability helps bring-up |

Societal/economic angle, honestly: the system reduces energy use versus
always-on ventilation by running fans only when air exchange actually cools,
and the parts are commodity and low cost. The physical limit — no refrigeration,
so it cannot go below ambient — belongs in Conclusions rather than being hidden.

## Order of work

1. **Theory calculations** — highest value, needs no bench time
2. **Heat-source runs** — gates Data Analysis, needs the enclosure
3. **Cost analysis** — price the BOM, an hour's work
4. **Write Introduction and Design** — material already exists
5. **Abstract and Conclusions last** — they summarise the rest
