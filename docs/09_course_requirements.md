# Course Requirements — EECE 4101 (ESDL)

**Source:** `EECE_4101_Syllabus_Fall_2026.docx`, Dr. Saleh Zein-Sabatto.
Added 2026-09-24, taken from TJ's `Documents/Fall 26/` copy, which is the
current one. An earlier download differed in exactly one respect and is not
authoritative — see section 6. This supersedes the guesswork in
[01_weekly_requirements_log.md](01_weekly_requirements_log.md) — every open
question in that file is answered below.

Class meets **Wednesdays 2:20–5:20 pm**, in person.

---

## 1. How the grade is actually weighted

| Component | Weight |
|---|---|
| **Project Reports** | **60%** |
| Presentations | 20% |
| Demonstrations | 20% |

Two consequences we had backwards:

- **The report is the course.** Sixty percent. The working rig we just finished
  is worth 20% as a demonstration. It is the evidence the report is built from,
  not the deliverable.
- **Reports are individual.** *"Design projects will be performed on a team
  basis however reports are submitted individually and each of the team members
  is to prepare a technical report."* TJ and Tabitha each write their own, in
  their own words, from the same shared data.

Grade scale: 90–100 A, 80–89 B, 70–79 C, 60–69 D, 0–59 F.

## 2. Schedule

> *"Generally, each design project will be completed in six weeks and reports
> will be due the following week."*
> *"One formal presentation is required from the group starting in week six."*

**Confirmed by TJ 2026-09-24: we are in week 5.** Class meets Wednesdays.

| Week | Date | What is due |
|---|---|---|
| 5 | 2026-09-23 | *(current)* Hardware complete and verified |
| 6 | **Wed 2026-09-30** | Presentations begin per the syllabus — be ready |
| 7 | **Wed 2026-10-07** | **Formal presentation and report due** |

So roughly **two weeks** from 2026-09-24. Weekly progress updates are expected
every week regardless.

**Late reports lose 10 points per day** unless arranged in advance.

## 3. Required report structure

The syllabus names the sections. Missing one costs marks directly:

1. Abstract
2. Introduction
3. Description of the project
4. Design objective
5. Design requirements
6. **Alternative solutions and design procedure**
7. Presentation of design testing results
8. **Data analysis**
9. Conclusion

### The ECE Department format — found

TSU College of Engineering, *Formats for Technical Reports*, published at
<https://www.tnstate.edu/engineering/documents/FormatsForReports.doc> and filed
here as [10_TSU_FormatsForReports.doc](10_TSU_FormatsForReports.doc).

**Section order it requires** (broader than the syllabus list, and it governs):

Cover · Title Page · Table of Contents · List of Figures and List of Tables ·
Symbols/Nomenclature · Summary · Introduction · **Theory** · Discussion ·
Results · Conclusions · Bibliography · Appendices

**Mechanical specification, quoted:**

| Item | Requirement |
|---|---|
| Paper | 8½ × 11 in |
| Font | **Courier 10 or TMS 12** |
| Spacing | **Double-spaced**, except long quotations and abstracts which are single-spaced |
| Margins | **1½ in top and left**, 1 in bottom and right |
| Preliminary pages | small Roman numerals, centred at the bottom, fifth line above the edge |
| Main text | Arabic numerals, centred at the bottom, five spaces from the bottom |
| Title page | page **i**, not printed |

**How it is graded — 100 points:**

| Area | Points |
|---|---|
| Written content — preliminaries, text, reference matter, form and appearance | **35** |
| **Technical content** — problem identification, theory, assumptions, methodology, computer codes, standards | **65** |

That split is the most useful thing in the document. **Two thirds of the report
grade is technical content, and "theory" and "assumptions" are named line
items.** It confirms the calculations gap below is the single highest-value
thing left to do — a beautifully formatted report with no mathematics is
capped around a third of the marks.

Note the format demands a **Theory** section outright, which the syllabus's own
nine-section list does not name. Reconcile by mapping the syllabus content into
this structure: design objective and requirements sit inside Introduction,
alternative solutions inside Discussion, data analysis inside Results.

Worth confirming with the instructor that this is the document he means, but it
is the College of Engineering's own published format and it matches the Courier
10 / TMS 12 specification quoted elsewhere.

Two further requirements stated separately:

- *"The design project must include analytical theories and design
  calculations."*
- *"Graphical presentation of the design project will be evaluated as a
  component of the design project and must be done by computer."*
- Course outcome (SLO-5) requires **cost analysis**.
- Course outcome (SLO-2) requires evaluating **alternatives on social, economic
  and societal impact** — not just technical trade-offs.

**Physical format:** 8.5 × 11, stapled behind a cover page, no ragged spiral
edges, single-sided (back of each page blank).

## 4. Where this project stands against that list

| Requirement | Status |
|---|---|
| Description, objective, requirements | **Have it** — [00_project_brief.md](00_project_brief.md) |
| Design testing results | **Have it** — [../test/bench_log.md](../test/bench_log.md), all five states verified on hardware |
| Graphical presentation by computer | **Have it** — schematic, wiring, flowchart, Tinkercad PDFs |
| Alternative solutions | **Partial.** Real decisions are documented (brushed → brushless, LCD → OLED, reversing intake → SEALED state) but not written up as a formal alternatives analysis, and not evaluated on social/economic/societal impact |
| **Analytical theories and design calculations** | **Missing.** Largest technical gap |
| **Cost analysis** | **Missing** as a section |
| **Data analysis** | **Missing.** Needs real heat-source runs, not bench verification |
| Abstract, introduction, conclusion | Not started |

### The calculations gap

Nothing in the repo currently does engineering *math*. The syllabus demands it
explicitly and it is the easiest place to lose report marks. Candidates, all
defensible from this design:

- **Airflow.** Fan rating in CFM against chamber volume → air changes per hour,
  and the theoretical time to displace one chamber volume.
- **Thermal.** Sensible heat equation `Q = m·c·ΔT` for the chamber air; heat
  removal rate at measured airflow and measured ΔT.
- **Time constant.** Measured cooling curve fitted to `T(t) = T∞ + (T₀−T∞)e^(−t/τ)`,
  giving τ, then compared against the theoretical value.
- **Hysteresis band.** Justify 80.0/77.0 from DS18B20 accuracy: ±0.5 °C each,
  so a differential carries ~±1.8 °F of uncertainty. The 3 °F band and the 2 °F
  deadband fall out of that arithmetic rather than being chosen by feel.
- **Power budget.** Fan stall and running current, DRV8833 limits, supply
  headroom.
- **Physical limit.** No refrigeration, so the floor is ambient. State it as an
  equation, not a caveat.

The hysteresis one is already half-derived in the design constraints — it just
needs writing out as arithmetic.

## 5. The second project

> *"Students must select two design projects from two different areas."*
> *"Each student is expected to lead the effort in one of the two design
> projects."*

This ventilation build is **project 1 of 2**, which is why the repo is scoped
`ESDL_Project_1`. A second project in a *different* area follows, with the
other partner leading. Worth deciding early what it is.

Our project is not on the syllabus's suggested list — the nearest entry is
"Sensor-based Warehouse Packages Diverter System using PLC" — so it was an
instructor-approved own idea, which the syllabus explicitly permits.

## 6. AI tools — no restriction in the current syllabus

Two copies of the syllabus exist and they differ in exactly one place. An
earlier downloaded copy carried a section titled *"Use of AI Tools and Academic
Honesty Policy"* which prohibited AI for graded work while simultaneously
requiring that any AI tool used be referenced.

**That section is absent from the current copy** in `Documents/Fall 26/`, which
is the version filed here. Diffed against the older copy, it is the only
substantive difference — grading weights, schedule, report structure and every
other requirement are identical.

This matches what the instructor stated verbally on 2026-09-24: **AI may be
used in all aspects of this project.** Both the current written syllabus and the
verbal instruction agree, so there is no conflict to manage.

Still worth doing: a short **AI use acknowledgment** in each report naming the
tools and what they were used for. It is ordinary academic practice, it costs a
few lines, and it documents the position. Reports are individual and written in
your own words regardless.

## 7. Do these next

1. **Confirm the week numbering in class.** If week 6 is 2026-09-30, the formal
   presentation is next Wednesday. Everything below depends on this.
2. **Get the ECE Department design reporting format** document.
3. **Run the real heat-source tests** — the data analysis section cannot be
   written without them, and they take bench time.
4. **Do the calculations.** Airflow, thermal, time constant, power budget.
5. **Price the BOM** for the cost analysis.
6. **Start the presentation deck.** Group, every member presents a part.
