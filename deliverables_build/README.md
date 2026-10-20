# Building the final deliverables

These scripts produce the three documents in the project root from `outputs/report_facts.json`,
so every number comes from the pipeline outputs.

1. `python run_all.py` (or `--skip-pareto`), then `python -m src.report_facts` and `python -m src.diagram`
2. In this folder: `npm init -y; npm install pptxgenjs docx`
3. `node build_deck.js`     -> Final_Presentation_CTU_Fleet_Allocation.pptx
   `node build_report.js`   -> Progress_Report_CTU_Fleet_Allocation.docx
   `node build_synopsis.js` -> Minor_Project_Synopsis_Revised.docx
4. Open each .docx in Word and update fields (F9, or `finalize_docx.ps1 -Path <file> -OutDir <tmp>`)
   so the table of contents, lists of figures/tables and caption numbers are filled.

`build_deck.js` applies the theme with the pptx skill's `apply_theme.js`; outside this environment,
remove that call (the deck still opens, with Office's default theme colours).
