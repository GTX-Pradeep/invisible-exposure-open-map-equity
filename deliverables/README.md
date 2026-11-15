# Course deliverables

These are the files to submit (Drive folder named after the team, shared with both TAs and Bhaskarjyoti Das sir).

| # | Deliverable | File(s) |
|---|---|---|
| 1 | Final one-pager | `One_Pager.docx` |
| 2 | Code (.ipynb) | `../notebooks/Invisible_Exposure.ipynb` (executed, with outputs) |
| 3 | Dataset (link/folder) | `dataset/` (processed tract CSVs + `DATASET_LINKS.md` with all raw-source links) |
| 4 | Project PPT | `Invisible_Exposure_Slides.pptx` (the copy in the course template is submitted through the Drive folder) |
| 5 | Video (3-5 min) | Recorded by the team and uploaded to the Drive folder |
| 6 | IEEE-format report | `IEEE_Report.pdf` (source: `ieee/IEEE_Report.tex`) |
| - | Full documentation | `Invisible_Exposure_Project_Documentation.docx` |
| - | Journal manuscript | `../paper/main.pdf` |

Rebuild: `node build_project_doc.js`, `node build_one_pager.js` and `node build_slides.js` take a JSON of results; `python ../notebooks/make_notebook.py` regenerates the notebook; the IEEE report builds with `latexmk -pdf IEEE_Report.tex` in `ieee/`.
