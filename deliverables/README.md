# Course deliverables (ADA project, due 16/11/2026 EOD)

Upload these to a Google Drive folder named after the team, and give both TAs and Bhaskarjyoti Das sir view access.

| # | Deliverable | File(s) | Status |
|---|---|---|---|
| 1 | Final one-pager | `One_Pager.docx` | Draft; restyle to the course template |
| 2 | Code (.ipynb) | `../notebooks/Invisible_Exposure.ipynb` (executed, with outputs) | Ready |
| 3 | Dataset (link/folder) | `dataset/` (processed tract CSVs + `DATASET_LINKS.md` with all raw-source links) | Ready |
| 4 | Project PPT | `Invisible_Exposure_Slides.pptx` (11 slides, speaker notes) | Draft; move into the course template |
| 5 | Video (3-5 min) | `Video_Script.md` (timed script matched to the slides) | Script ready; team records |
| 6 | IEEE-format report | `IEEE_Report.pdf` (source: `ieee/IEEE_Report.tex`) | Ready |
| - | Full documentation | `Invisible_Exposure_Project_Documentation.docx` | Ready |
| - | Journal manuscript | `../paper/main.pdf` | Ready |

Suggested Drive layout: `1_OnePager/`, `2_Code/` (notebook + link to the GitHub repo), `3_Dataset/` (the `dataset/` folder), `4_PPT/`, `5_Video/`, `6_IEEE_Report/`.

Fill in before submitting: team name and member names (title slide, one-pager, IEEE report, documentation).

Rebuild: `node build_project_doc.js`, `node build_one_pager.js` and `node build_slides.js` take a JSON of results; `python ../notebooks/make_notebook.py` regenerates the notebook.
