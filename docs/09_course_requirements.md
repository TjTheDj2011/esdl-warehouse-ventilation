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

Working dates, **to be confirmed in class** because the week numbering is ours,
not the instructor's:

| Week | Date | What is due |
|---|---|---|
| 6 | **Wed 2026-09-30** | Formal group presentation + project complete |
| 7 | **Wed 2026-10-07** | Individual technical reports |

Weekly progress presentations are expected *every* week regardless.

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

Must follow the **ECE Department design reporting format**. We do not have a
document confirmed to be it. The College of Engineering's Capstone Design
Manual (ENGR 4500) specifies Courier 10 or TMS 12 and a chapter structure, but
that belongs to a different course and may not be what EECE 4101 means. **Ask
the instructor which document applies** rather than assuming.

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
