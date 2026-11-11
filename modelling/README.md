# Modelling checks (build steps 7-8)

Read after `eda/`. These notebooks check the expectation model itself; they do **not** change the primary specification
or any published result, and they use no audit variable (SVI, CVI, rurality, tribal, hazards).

| Notebook | Build step | Question | Main findings |
|---|---|---|---|
| `01_model_settings.ipynb` | 7. Model and its settings | Where does each setting come from, is the published model reproduced, and how much do the settings matter? | Published predictions and all 510 flags reproduced exactly. Coverage is 90.0% in all 17 variants. LightGBM settings, block size and number of folds change fit and skill no more than the random seed does; removing the housing-type inputs does (R² 0.926 → 0.845, lift 5.1 → 3.6). A seed change alone alters about a quarter of the flagged tracts. |
| `02_residual_diagnostics.ipynb` | 8. Residual diagnostics | Are the errors well behaved, calibrated across tract types, free of drift, and spatially independent? | Residuals centred (sd 0.21 log points), left-skewed, no strong drift with any input. Coverage 0.89-0.93 by region, but flags concentrate in small tracts (14% of the smallest decile vs 1% of the largest) and are almost absent in eastern WA. Residuals cluster (Moran's I 0.09-0.18), and the correlation fades to about zero within 50 km, the block size. |

Files:

* `build/run_settings_grid.py`: refits the primary model and 16 one-at-a-time variants (about 30 minutes on 2 cores); writes
  `tables/01_settings_grid.csv` and the primary out-of-fold predictions `tables/oof_bldg_primary.parquet`, `tables/oof_poi_primary.parquet`.
* `build/make_modelling_notebooks.py`: writes both notebooks (written takeaways in `build/takeaways.json`); they only read the tables, so they run in seconds.
* `tables/`, `figures/`: saved outputs, prefixed with the notebook number.

Rebuild from the repo root:

```
PYTHONPATH=src python modelling/build/run_settings_grid.py      # needs data/processed/tracts_all.parquet
python modelling/build/make_modelling_notebooks.py
jupyter nbconvert --to notebook --execute --inplace modelling/0*.ipynb
```

What this means for the paper: report tract flags as a screen (a quarter change with the random seed), state that the
90% range is calibrated on average but not within tract-size classes, and note that the 50 km blocks are justified by the
residual correlation reaching about zero at that distance.
