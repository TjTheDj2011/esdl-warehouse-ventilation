# Report working folder

| File | What it is |
|---|---|
| `ESDL_Project1_Report_TEMPLATE.docx` | **The one to work in.** Opens in Word or LibreOffice. |
| `ESDL_Project1_Report_TEMPLATE.pdf` | Read-only preview of the same thing. |
| `ESDL_Project1_Report_TEMPLATE.html` | Source the other two are generated from. Ignore unless regenerating. |

## Start here

1. Copy the `.docx` to your own filename — `Report - <Your Name>.docx`.
2. Fill in the title page.
3. Delete the "How to use this template" box.
4. Write the highlighted blocks in your own words.

## Reports are individual

The syllabus is explicit: the team builds together, but each member submits
their own report. Everything already written in the template is **shared
project data** — measurements, derivations, tables, figures — which both
authors are entitled to use because both produced it. Every
**highlighted** block is prose, and prose must be your own. Do not swap
written sections with your partner.

## Already done for you

- Formatting to department spec: Times New Roman 12, double spaced,
  1.5 in top and left margins, 1 in bottom and right.
- Section structure in the order the syllabus requires.
- Design requirements table, with the rationale for every threshold.
- Alternatives analysis table.
- The analytical calculations — airflow, heat removal, the ambient floor,
  the time constant, threshold derivation from sensor tolerance, power budget.
- All measured test results from the bench sessions.
- Nomenclature table.

## Still needs doing

- **Chamber volume.** Measure the enclosure internals. The airflow and
  time-constant tables are parameterised on it.
- **Cooling curve.** Heat the box, cut the source, log inside temperature
  against time. This is the whole Data Analysis section.
- **Unit prices** for the cost analysis table.
- **Figures.** The diagrams in `../docs/` are already computer-produced:
  schematic, wiring diagram, engineering flowchart, Tinkercad layout.
  Insert them with captions and the lists of figures will build themselves.

## Background

- Requirements and grading: [../docs/09_course_requirements.md](../docs/09_course_requirements.md)
- Section-by-section guidance: [../docs/11_report_outline.md](../docs/11_report_outline.md)
- Full derivations: [../docs/12_calculations.md](../docs/12_calculations.md)
- Measured results: [../test/bench_log.md](../test/bench_log.md)

## Regenerating

Edit the `.html`, then:

```
libreoffice --headless --infilter="HTML (StarWriter)" --convert-to odt --outdir . ESDL_Project1_Report_TEMPLATE.html
libreoffice --headless --convert-to docx:"MS Word 2007 XML" --outdir . ESDL_Project1_Report_TEMPLATE.odt
libreoffice --headless --convert-to pdf --outdir . ESDL_Project1_Report_TEMPLATE.odt
```

The `HTML (StarWriter)` input filter matters — without it LibreOffice opens the
file as a web document and the page margins are lost.
