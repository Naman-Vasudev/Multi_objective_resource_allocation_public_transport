# Study guide

Three deliverables for learning, presenting and defending the project. All demand in the project is synthetic and
illustrative.

| File | What it is |
|---|---|
| `textbook/textbook.pdf` | 92-page textbook, high-school maths upwards: variables → LP → MILP → bus operations → waiting → fuzzy demand → goal programming → Pareto fronts → simulation → the full model → how to read all 15 figures → results and limitations, with a glossary |
| `notebook/CTU_walkthrough.ipynb` | Executed notebook: 2-variable toy → one route → 3-route toy (brute-force checked) → the real 68-route pipeline, ending with a full `run_all.py` rerun that reproduces the saved outputs |
| `cheatsheet/cheatsheet.pdf` | 2-minute pitch, 10-minute demo script, what to point at in every figure, 30 Q&As, limitations, key numbers |

Rebuild:
- textbook figures: `python textbook/make_figures.py`, then `pdflatex textbook.tex` twice in `textbook/`
- notebook: `python notebook/build_notebook.py`, then
  `jupyter nbconvert --to notebook --execute --inplace notebook/CTU_walkthrough.ipynb` (about 11 minutes)
- cheat sheet: `pdflatex cheatsheet.tex` twice in `cheatsheet/`
