// Builds deliverables/Invisible_Exposure_Project_Documentation.docx from the pipeline outputs.
// usage: node deliverables/build_project_doc.js <docdata.json>
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat, PageBreak, Footer, PageNumber,
  TableOfContents, ExternalHyperlink,
} = require("docx");

const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const M = D.macros;
const tex = (s) => String(s).replace(/\\%/g, "%").replace(/\$\+\$/g, "+").replace(/\\ /g, " ").replace(/\\emph\{([^}]*)\}/g, "$1")
  .replace(/\\\\/g, "").replace(/~\\ref\{[^}]*\}/g, "").replace(/\$/g, "");
const m = (k) => tex(M[k]);
const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => path.join(ROOT, "outputs/figures", f);

const FONT = "Arial";
const W = 9360; // content width (US Letter, 1" margins)
const BLUE = "1F4E79", LIGHT = "DCE6F1", GREY = "F2F2F2";

// ---- inline markup: **bold**, `code`
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, mm;
  while ((mm = re.exec(text))) {
    if (mm.index > last) out.push(new TextRun({ text: text.slice(last, mm.index), ...base }));
    const t = mm[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 19, ...base }));
    last = mm.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 120, line: 276 }, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (t, lvl = 0) => new Paragraph({ numbering: { reference: "bullets", level: lvl }, children: runs(t), spacing: { after: 60 } });
const N = (t, ref = "nums") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60 } });
const PB = () => new Paragraph({ children: [new PageBreak()] });
const callout = (title, lines) => {
  const border = { style: BorderStyle.SINGLE, size: 6, color: BLUE };
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA }, shading: { fill: LIGHT, type: ShadingType.CLEAR },
      borders: { top: border, bottom: border, left: border, right: border },
      margins: { top: 120, bottom: 120, left: 180, right: 180 },
      children: [new Paragraph({ children: [new TextRun({ text: title, bold: true, color: BLUE })], spacing: { after: 80 } }),
        ...lines.map((l) => B(l))],
    })] })],
  });
};

function table(header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = W / total;
  const w = widths.map((x) => Math.floor(x * scale));
  w[w.length - 1] += W - w.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (txt, i, head, shade) => new TableCell({
    width: { size: w[i], type: WidthType.DXA }, borders,
    shading: { fill: head ? BLUE : shade ? GREY : "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({ children: runs(String(txt), head ? { bold: true, color: "FFFFFF", size: opts.size || 18 } : { size: opts.size || 18 }) })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: w,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => cell(c, i, false, ri % 2 === 1)) }))],
  });
}
const space = () => new Paragraph({ children: [], spacing: { after: 60 } });
function figure(file, caption, widthIn = 6.3) {
  const buf = fs.readFileSync(FIG(file));
  const wpx = buf.readUInt32BE(16), hpx = buf.readUInt32BE(20);
  const w = Math.round(widthIn * 96), h = Math.round((w * hpx) / wpx);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h },
      altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: caption, italics: true, size: 18, color: "404040" })] }),
  ];
}
const link = (text, url) => new ExternalHyperlink({ link: url, children: [new TextRun({ text, style: "Hyperlink" })] });
const pct = (x, d = 1) => `${(100 * x).toFixed(d)}%`;
const f3 = (x) => (x === "" || x === null || x === undefined ? "" : Number(x).toFixed(3));

// ======================================================================= content
const C = [];
// ---- title page
C.push(new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "Invisible Exposure", bold: true, size: 64, color: BLUE, font: FONT })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
  children: [new TextRun({ text: "Reference-free, conformal auditing of open-map completeness and the climate-hazard exposure it hides", size: 30, font: FONT })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Complete project documentation", size: 26, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "ADA course project  |  Team: [team name]  |  November 2026", size: 22 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Team members: Chinthan, Pradeep, [others]", size: 22 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [link("github.com/GTX-Pradeep/invisible-exposure-open-map-equity", "https://github.com/GTX-Pradeep/invisible-exposure-open-map-equity")] }));
C.push(PB());
C.push(new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, size: 32, color: BLUE })], spacing: { after: 200 } }));
C.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));
C.push(P("(Word fills in this list when the file opens; if it asks to update fields, choose Yes. Otherwise right-click the list and choose Update Field.)", { spacing: { before: 120 } }));
C.push(PB());

// ---- 1 summary
C.push(H1("1. Executive summary"));
C.push(P("Open map data such as Overture Maps now feed disaster planning, insurance and climate-risk models. When a map is missing buildings or businesses, those places are also missing from every exposure count built on top of it. We built a method that estimates, for every census tract, how many buildings and points of interest (POIs) the map **should** contain, puts a calibrated uncertainty range around that number, and flags tracts where the map falls clearly below it. We then turned those gaps into hidden heat, wildfire and drought exposure and audited who lives in the affected tracts, under a pre-registered analysis plan."));
C.push(callout("Headline results", [
  `**Scale:** ${m("NTracts")} census tracts, ${m("NHU")} million housing units and ${m("NPop")} million people in 5 U.S. climate-hazard regions; ${m("NBldg")} million Overture buildings and ${m("NPoi")} million places.`,
  `**Calibrated ranges work:** 90% conformal ranges cover ${m("CovBldg")} (buildings) and ${m("CovPoi")} (POIs) of held-out tracts. When a whole region is held out, coverage falls to ${m("CovLoroBldg")}; calibrating within each region fixes it.`,
  `**Flags find real gaps:** against FEMA/ORNL USA Structures, flagged tracts are ${m("LiftBldg")}x more likely than chance to be real gaps. Removing half a tract's buildings gets it flagged ${m("DelFiftyBldg")} of the time.`,
  `**Maps caught up:** from 2023 to 2026, the share of tracts below 80% of the reference fell from ${m("GapShareA")} to ${m("GapShareB")}; rural tracts improved ${m("DidRuralPP")} percentage points more than urban tracts.`,
  `**A silent release regression (new finding):** Overture releases since 2026-09-23 dropped about ${m("EOneLost")} buildings from ${m("EOneTracts")} tracts in San Antonio, TX (${m("EOneResidents")} residents; ${m("EOneSviShare")} high-vulnerability tracts). Our model, using no reference at all, flagged ${m("EOneFlagAfter")} of them.`,
  `**Hidden exposure:** missing structures in high-wildfire tracts are ${m("HFiveWildRural")}x more common per housing unit in rural than urban tracts (drought: ${m("HFiveDroughtRural")}x).`,
  `**An honest limitation that is itself a contribution:** tract-level flags miss gaps shared by a whole group (rural, tribal), because the model learns much of that shortfall as normal and its error is larger than a typical gap.`,
]));
C.push(space());
C.push(P("Everything is reproducible: one script downloads the public data and regenerates every number, table, figure and the manuscript. A rerun from the GitHub repository reproduced every number and table byte-for-byte."));

// ---- 2 problem
C.push(H1("2. Problem statement"));
C.push(H2("2.1 Why this matters"));
C.push(P("Climate-risk tools count exposure by overlaying hazard maps (heat, wildfire, drought) on building and facility maps. If buildings are missing from the map, they are also missing from the exposure count, and the communities living in them look safer and less in need than they are. Open maps are known to be less complete in poorer and more rural places, so the people most exposed to climate hazards may be the ones the data under-counts."));
C.push(H2("2.2 The core difficulty"));
C.push(P("To measure how incomplete a map is, you normally need a complete reference map to compare against, and for most places and most feature types no such reference exists. Raw sparsity is ambiguous: a tract with few mapped buildings might be genuinely empty, or simply unmapped."));
C.push(H2("2.3 Problem statement"));
C.push(callout("Problem statement", [
  "Estimate, without a perfect reference map and with honest uncertainty, where open map data (Overture Maps) is incomplete at census-tract level;",
  "convert those gaps into hidden climate-hazard (heat, wildfire, drought) exposure; and",
  "test, under a pre-registered plan, whether the gaps and the hidden exposure fall disproportionately on socially vulnerable, rural and tribal communities, and whether they close as the map improves across releases.",
]));
C.push(H2("2.4 Research questions"));
["**RQ1.** Can we estimate where open maps are incomplete, with honest uncertainty, without a perfect reference map?",
 "**RQ2.** How much wildfire, heat and drought exposure is missing from the map, and does it fall on socially vulnerable, rural and tribal communities?",
 "**RQ3.** As Overture improves across releases, do vulnerable communities catch up?",
 "**RQ4.** Does dependence on a single upstream data source predict where gaps are?"].forEach((t) => C.push(B(t)));
C.push(H2("2.5 The design rule"));
C.push(P("Social vulnerability (SVI), climate vulnerability (CVI), rurality, tribal status and hazard variables **never** enter the expectation model. They are joined only in the audit phase, and a guard in the code (`assert_no_leakage`) refuses them as inputs. This keeps the model from learning existing disparities as \"normal\" through those variables."));

// ---- 3 novelty
C.push(H1("3. Where our novelty stands"));
C.push(P("Work on open-map completeness exists, so the contribution has to be stated precisely. The table compares our project with the closest prior work."));
C.push(table(["Aspect", "Prior work", "This project"], [
  ["Completeness without a reference", "Regression of completeness on socio-economic covariates (e.g., Herfort et al. 2023, OpenStreetMap buildings, global)", "Expectation from neutral structural facts only; audit variables excluded by a code guard"],
  ["Uncertainty", "Point estimates, no calibrated ranges", "Cross-fitted conformalized quantile regression: a calibrated 90% range for every tract"],
  ["Spatial validity", "Usually random cross-validation", "Random vs. 50 km spatial blocks vs. leave-one-region-out; shows where the coverage guarantee breaks and how per-region calibration repairs it"],
  ["External validation", "Rare at tract scale", "FEMA/ORNL USA Structures (125M structures) and Census Business Patterns, plus a controlled deletion test"],
  ["Time", "Single snapshot", "Three Overture snapshots (2023, 2026-08, 2026-10), with catch-up by group"],
  ["Release monitoring", "Not studied", "Documents a real, silent 2026 release regression and shows the reference-free model detects it"],
  ["Equity analysis", "Descriptive comparisons", "Pre-registered hypotheses, cluster-robust inference, false-discovery-rate control, robustness runs"],
  ["Method limits", "Rarely quantified", "Quantifies absorption (the model inherits 64-80% of group shortfall) and resolution limits of tract-level flags"],
  ["Same challenge data", "Dozens of Bias Bounty submissions (unreviewed GitHub write-ups) scoring coverage gaps against provided references", "Different question and method: calibrated ranges, independent references not used by the challenge, three releases, regression detection, pre-registration"],
], [2000, 3300, 4060]));
C.push(space());
C.push(H2("3.1 The four claims we make"));
[`**Method:** a conformal, leakage-guarded completeness model for open maps, with an empirical study of its calibration under spatial shift.`,
 `**Finding 1 (regression):** Overture lost about ${m("EOneLost")} buildings around San Antonio from release 2026-09-23 on, concentrated in high-vulnerability tracts, and the reference-free model flags ${m("EOneFlagAfter")} of affected tracts. To our knowledge this is undocumented.`,
 `**Finding 2 (catch-up):** rural and tribal building gaps closed faster than urban ones between 2023 and 2026 (pre-registered H3).`,
 `**Finding 3 (detectability):** tract-level flags, from a map-trained or even a reference-trained expectation, cannot see modest group-wide gaps; equity conclusions need direct reference comparison aggregated by group.`].forEach((t) => C.push(N(t)));
C.push(H2("3.2 Is it publishable?"));
C.push(P("Yes, for a good GIScience or data-science journal (suggested: Computers, Environment and Urban Systems; International Journal of Geographical Information Science; EPJ Data Science) or an ACM SIGSPATIAL / FAccT paper. Reviewers will likely raise the mostly null building-equity results, the approximate POI reference, and the five-region sample; all three are addressed in the limitations section of the paper."));

// ---- 4 data
C.push(PB());
C.push(H1("4. Datasets"));
C.push(P("All data are public. Large inputs are read from the cloud or cached under `data/raw/`, which Git ignores."));
C.push(table(["Dataset", "Version", "Role", "Access / link"], [
  ["Overture Maps buildings + places", "2026-08-19.0 (primary)", "Map under audit", "Challenge extracts on Source Cooperative (humane-intelligence/bias-bounty-mapping-equity-challenge)"],
  ["Overture Maps buildings + places", "2026-10-21.0", "Later snapshot (H3, regression)", "s3://overturemaps-us-west-2/release/2026-10-21.0/"],
  ["Overture Maps buildings", "2023-07-26-alpha.0", "Earlier snapshot (H3)", "Archived GeoParquet copy: source.coop/cholmes/overture"],
  ["Census tracts (2020)", "TIGER 2025", "Unit of analysis", "Challenge strata folder"],
  ["ACS 5-year summary file", "2020-2024", "Structural covariates", "www2.census.gov/programs-surveys/acs/summary_file/2024/"],
  ["LEHD LODES 8 (WAC)", "2022", "Job counts by sector (POI covariates)", "lehd.ces.census.gov/data/lodes/LODES8/"],
  ["FEMA/ORNL USA Structures", "v1", "Building reference (validation only)", "source.coop/wherobots/usa-structures"],
  ["ZIP / County Business Patterns", "2023", "Establishment reference (validation only)", "www2.census.gov/programs-surveys/cbp/datasets/2023/"],
  ["ZCTA-tract relationship file", "2020", "Allocation weights", "www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"],
  ["Audit strata (SVI 2022, CVI, RUCA, tribal, EPHT heat, USFS wildfire, USDM drought)", "see repo", "Audit only", "Challenge strata/national/"],
], [2600, 1500, 2100, 3160]));
C.push(space());
C.push(H2("4.1 Study regions"));
C.push(table(["Region", "Tracts", "Housing units", "Overture buildings", "Overture places", "USA Structures"],
  D.regions.map((r) => [r.region, r.tracts.toLocaleString(), r.hu.toLocaleString(), Math.round(r.bldg).toLocaleString(), Math.round(r.poi).toLocaleString(), Math.round(r.ref).toLocaleString()]),
  [2200, 1100, 1500, 1600, 1500, 1460]));
C.push(space());
C.push(H2("4.2 Independence of the data sources"));
["Model inputs are Census and LODES counts only; none is derived from Overture, USA Structures or Business Patterns.",
 "USA Structures and Overture's machine-learned footprints are both derived from imagery, so they may share omissions (for example under tree canopy). That would understate true gaps, not invent them.",
 "Business Patterns counts employer establishments at tax addresses, a related but different universe from Overture places, so we use within-region relative ratios."].forEach((t) => C.push(B(t)));

// ---- 5 pipeline
C.push(H1("5. System architecture and pipeline"));
C.push(P("Four kinds of input feed one tract table. The model gives every tract an expected range, and three analyses consume the flags. Reference data go only to validation, and audit strata never touch the model."));
C.push(table(["Phase", "Script", "What it does", "Main output"], [
  ["Data", "`fetch_challenge.sh`, `fetch_inputs.sh`", "Download challenge extracts, strata, LODES, Business Patterns", "`data/raw/`"],
  ["Ref.", "`00b_usa_structures_counts.py`", "USA Structures counts per tract from the block-code column (no spatial join)", "`usa_structures_tract.parquet`"],
  ["Ref.", "`00c_poi_reference.py`", "ZIP establishments allocated to tracts; county totals", "`zbp_tract`, `cbp_county`"],
  ["1", "`01_count_overture.py`", "Count buildings (all and >=450 sq ft) and places per tract, with source provenance, for 3 releases", "`overture_<release>_*.parquet`"],
  ["2", "`02_build_tract_table.py`", "Join structural covariates, counts, provenance, references; strata saved separately", "`tracts_all`, `strata_audit`"],
  ["3", "`03_expectation_model.py`", "LightGBM quantile models + CQR conformal ranges, cross-fitted on spatial blocks", "`expectation.parquet`"],
  ["4", "`04_validation.py`", "CV schemes, flag skill vs references, baselines, deletion test", "`cv_schemes.csv`, `flag_skill.csv`"],
  ["Gate", "`docs/preregistration.md`", "Hypotheses frozen before any equity result", "commit 5d08b3e"],
  ["5", "`05_provenance.py`", "H4: do source-mix features improve gap detection?", "`h4_provenance.json`"],
  ["6", "`06_audit.py`, `06b_fdr.py`", "H1, H2, H5 contrasts; BH false-discovery correction", "`confirmatory_fdr.csv`"],
  ["6", "`06c_robustness.py`, `06d_original_hypotheses.py`", "Robustness runs; tests of the original template", "`robustness.csv`"],
  ["7", "`07_catchup.py`", "H3: catch-up across 2023, 2026-08, 2026-10", "`h3_*.csv`"],
  ["Expl.", "`09_exploratory.py`", "Release regression, absorption, H3 sensitivity", "`exploratory.json`"],
  ["8", "`08_figures.py`, `10_paper_numbers.py`", "Figures; every number in the paper generated from tables", "`outputs/figures/`, `paper/`"],
], [800, 2700, 3700, 2160]));

// ---- 6 methods
C.push(PB());
C.push(H1("6. Methods in detail"));
C.push(H2("6.1 Counting map features per tract"));
C.push(P("Each building or place is reduced to the centre of its bounding box and assigned to the 2020 census tract that contains it, using DuckDB's spatial join. For buildings we also count footprints of at least 450 sq ft (41.8 m2), the inclusion rule of USA Structures, so the two are comparable. Each feature's primary upstream source is recorded (OpenStreetMap, Microsoft ML Buildings, Google Open Buildings, Esri Community Maps; Meta, Microsoft and Foursquare for places)."));
C.push(H2("6.2 Structural covariates (the only model inputs)"));
["Housing units, population, households, group-quarters population, vacancy share (ACS).",
 "Units in structure: single detached, attached, 2, 3-4, 5-9, 10-19, 20-49, 50+, mobile homes, boats/RVs (ACS B25024), plus a derived 'structure-equivalents' count.",
 "Year built shares (ACS B25034), land area and densities.",
 "Workplace jobs by sector: retail, food and accommodation, health, education, and so on (LODES; no worker demographics)."].forEach((t) => C.push(B(t)));
C.push(H2("6.3 Expectation model with conformal ranges"));
C.push(P("For each layer (buildings, POIs) we model y = log(1 + count). LightGBM quantile regression predicts the 5th, 50th and 95th percentiles. Predictions are **cross-fitted**: tracts are split into 10 folds of whole 50 km spatial blocks, and each tract is predicted by models that never saw its fold, so its own deficit cannot lower its expectation."));
C.push(P("**Conformalized quantile regression (CQR)** then calibrates the range. Each tract's conformity score is how far its observed value falls outside the raw quantile band. For each fold, the band is widened by the finite-sample 90% quantile of the scores in the other folds. In the Mondrian variant, this correction is computed separately within each region."));
C.push(P("A tract is **flagged** when its observed count falls below the conformal lower bound. Its conservative shortfall is lower bound minus observed (in buildings), and its standardized deficit is (median minus observed) divided by (median minus lower bound)."));
C.push(H2("6.4 Validation"));
["**Fold schemes:** random, spatial-block and leave-one-region-out, each with global or within-region calibration.",
 "**Reference gaps:** a building gap is a tract with Overture below 80% of USA Structures; a POI gap is a tract whose places-to-establishments ratio is below half its region's median.",
 "**Metrics:** precision, recall, lift, ROC-AUC, PR-AUC; baselines are a log-log OLS on housing units and the raw map-to-housing ratio.",
 "**Deletion test:** remove a share of a tract's features from its observed count and record how often it gets flagged."].forEach((t) => C.push(B(t)));
C.push(H2("6.5 Pre-registered audit"));
["**H1/H2:** flag rates by SVI (top vs bottom quartile), CVI, rurality (RUCA >= 4) and tribal overlap. Logistic regression with region fixed effects and county-clustered errors; risk difference with a county-cluster bootstrap.",
 "**H3:** change in reference-relative completeness 2023 to 2026-10 by group (OLS, region fixed effects), and a difference-in-differences of gap rates.",
 "**H4:** gain in spatial-CV PR-AUC from adding provenance features.",
 "**H5:** hidden exposure = conservatively missing structures in top-tercile heat, wildfire or drought tracts, per 1,000 housing units; group rate ratios with bootstrap CIs.",
 `**Multiplicity:** Benjamini-Hochberg across all ${m("NFdrFamily")} H1, H2, H3 and H5 contrasts at q = 0.05.`].forEach((t) => C.push(B(t)));

// ---- 7 results
C.push(PB());
C.push(H1("7. Results in detail"));
C.push(H2("7.1 How complete is the map?"));
C.push(P(`Overture buildings agree closely with USA Structures (log-scale correlation ${m("RefCorr")}, median ratio ${m("RefMedRatio")}). Only ${m("RefGapShare")} of tracts fall below 80% of the reference. Gaps are more common in rural (${m("RefGapRural")}) than urban (${m("RefGapUrban")}) tracts, and in tribal (${m("RefGapTribal")}) than non-tribal (${m("RefGapNonTribal")}) tracts.`));
figure("fig2_reference_scatter.png", "Figure 1. Overture buildings (>=450 sq ft) vs. USA Structures per tract; orange = flagged by the model.", 4.0).forEach((x) => C.push(x));
figure("fig1_maps.png", "Figure 2. Standardized building deficit per tract; black outlines = flagged tracts.").forEach((x) => C.push(x));
C.push(H2("7.2 Calibration under spatial shift"));
C.push(P(`Under spatial cross-fitting the building model explains R2 = ${m("RTwoBldg")} of log-count variance, the POI model R2 = ${m("RTwoPoi")}. Per-region building coverage with global calibration ranges from ${m("CovSpatRegMinBldg")} to ${m("CovSpatRegMaxBldg")}; within-region calibration narrows this to ${m("CovMondRegMinBldg")}-${m("CovMondRegMaxBldg")}. Holding out a whole region drops coverage to ${m("CovLoroBldg")} (worst region ${m("CovLoroMinBldg")}).`));
C.push(table(["Layer", "Folds", "Calibration", "Coverage", "Flag rate", "R2 (log)", "Region min", "Region max"],
  D.cv.map((r) => [r.layer, r.scheme, r.calibration, pct(r.coverage), pct(r.flag_rate), f3(r.r2_log), pct(r.cov_region_min), pct(r.cov_region_max)]),
  [900, 1000, 1500, 1100, 1100, 1000, 1100, 1100]));
C.push(space());
figure("fig3_coverage_schemes.png", "Figure 3. Coverage of 90% ranges by fold scheme and calibration.").forEach((x) => C.push(x));
C.push(H2("7.3 Do flags find real gaps?"));
C.push(table(["Layer", "Method", "Prevalence", "Flags", "Precision", "Recall", "Lift", "ROC-AUC", "PR-AUC"],
  D.skill.filter((r) => !String(r.method).includes("|")).map((r) => [r.layer, r.method, pct(r.prevalence), r.n_flag, f3(r.precision), f3(r.recall), Number(r.lift).toFixed(1), f3(r.auc), f3(r.pr_auc)]),
  [800, 1900, 1100, 800, 1000, 900, 700, 1000, 1000]));
C.push(space());
C.push(P(`Removing 30% of a tract's buildings triggers a flag ${m("DelThirtyBldg")} of the time and removing 50% does so ${m("DelFiftyBldg")} of the time. For POIs the rates are ${m("DelThirtyPoi")} and ${m("DelFiftyPoi")}. At county level, Overture places and Business Patterns establishments correlate at Spearman rho = ${m("CountyRho")} (n = ${m("CountyN")}).`));
figure("fig4_deletion.png", "Figure 4. Deletion test.", 4.0).forEach((x) => C.push(x));

C.push(H2("7.4 Pre-registered equity contrasts (H1, H2, H3, H5)"));
const fdrRows = D.fdr.map((r) => {
  let est;
  if (r.hyp === "H1" || r.hyp === "H2") est = `RD ${Number(r.risk_diff).toFixed(3)}; aOR ${Number(r.adj_odds_ratio).toFixed(2)}`;
  else if (r.hyp === "H5") est = `RR ${Number(r.rate_ratio).toFixed(2)} [${Number(r.ci_lo).toFixed(2)}, ${Number(r.ci_hi).toFixed(2)}]`;
  else est = `diff ${Number(r.adj_diff).toFixed(3)} [${Number(r.ci_lo).toFixed(3)}, ${Number(r.ci_hi).toFixed(3)}]`;
  const hyp = r.hyp === "H5" ? `H5 ${r.hazard_name}` : r.hyp === "H3" ? (r.outcome === "d_lc" ? "H3a" : "H3b") : r.hyp;
  return [hyp, r.layer, r.contrast, est, Number(r.p).toFixed(4), Number(r.p_bh).toFixed(4), r.reject_bh === true || r.reject_bh === "True" ? "Yes" : "No"];
});
C.push(table(["Hyp.", "Layer", "Contrast", "Estimate", "p", "p (BH)", "Significant"], fdrRows, [900, 700, 2000, 2700, 900, 900, 1000], { size: 16 }));
C.push(space());
["**Buildings (H1, H2):** model flag rates do not differ significantly by SVI, CVI, rurality or tribal status.",
 `**POIs (H1, H2):** POI flags are less common in high-SVI tracts (${m("PoiSviHi")} vs ${m("PoiSviLo")}), high-CVI and rural tracts; there is no evidence that places are under-mapped in vulnerable tracts.`,
 `**Hidden exposure (H5):** ${m("HEAll")} conservatively missing structures in flagged tracts; in wildfire tracts, rural rates are ${m("HFiveWildRural")}x urban; in drought tracts ${m("HFiveDroughtRural")}x.`,
 `**H4:** provenance features do not improve building-gap detection (change in PR-AUC ${m("HFourDprBldg")}); tracts dominated by Microsoft ML footprints have twice the gap rate of OpenStreetMap-dominated tracts (${m("GapMsft")} vs ${m("GapOsm")}).`].forEach((t) => C.push(B(t)));
figure("fig7_hidden_exposure.png", "Figure 5. Hidden exposure rate ratios (H5); diamonds = significant after FDR correction.", 5.0).forEach((x) => C.push(x));

C.push(H2("7.5 Catch-up across releases (H3) and the release regression"));
C.push(table(["Snapshot", "Buildings", ">=450 sq ft", "Tracts <80% of ref.", "Rural", "Urban", "Tribal", "SVI Q4"],
  D.snap.map((r) => [r.snapshot.replace("r2023", "2023-07").replace("r2026a", "2026-08").replace("r2026b", "2026-10"), Math.round(r.buildings).toLocaleString(), Math.round(r.buildings450).toLocaleString(),
    pct(r.share_tracts_lt80), pct(r.lt80_rural_rural), pct(r.lt80_rural_urban), pct(r.lt80_tribal_tribal), pct(r.lt80_svi_Q4)]),
  [1100, 1300, 1300, 1400, 1000, 1000, 1000, 1000]));
C.push(space());
C.push(P(`From 2023 to 2026 the study area gained ${m("GainBldg")} million mapped buildings and the OpenStreetMap share rose from ${m("OsmShareA")} to ${m("OsmShareC")}. Rural tracts improved ${m("DidRuralPP")} percentage points more than urban tracts (pre-registered, significant after FDR), and tribal tracts ${m("DidTribalPP")} points more (not significant after FDR).`));
C.push(P(`**The regression.** From release 2026-09-23 on, Overture dropped about ${m("EOneLost")} footprints, almost all from Microsoft ML Buildings, from ${m("EOneTracts")} tracts (${m("EOneBexar")} of them in Bexar County, San Antonio). In those tracts the share below 80% of the reference went from 0% to ${m("EOneRefGapAfter")}. They house ${m("EOneResidents")} people, and ${m("EOneSviShare")} of them are high-vulnerability tracts (study-wide: ${m("EOneSviAll")}). Re-run on the 2026-10 release with no reference input, the model flagged ${m("EOneFlagAfter")} of them (before: ${m("EOneFlagBefore")}).`));
figure("fig6_catchup.png", "Figure 6. Share of tracts below 80% of USA Structures, by group and snapshot.").forEach((x) => C.push(x));
figure("fig8_bexar_regression.png", "Figure 7. Buildings lost between the 2026-08 and 2026-10 releases, Bexar County; outlines = flagged.", 3.8).forEach((x) => C.push(x));

C.push(H2("7.6 Why tract flags miss group-wide gaps (exploratory)"));
C.push(P(tex(M.ETwoText)));
figure("fig5_two_lenses.png", "Figure 8. Odds ratios of a building gap by group under three lenses.", 5.2).forEach((x) => C.push(x));
C.push(H2("7.7 Original pre-registered hypotheses"));
C.push(table(["Hypothesis (original wording)", "n (a / b)", "Mean a", "Mean b", "Rank-biserial", "p (BH)"],
  D.orig.map((r) => [r.hyp, `${r.n_a} / ${r.n_b}`, Number(r.mean_a).toFixed(3), Number(r.mean_b).toFixed(3), Number(r.rank_biserial).toFixed(3), Number(r.p_bh).toFixed(4)]),
  [4000, 1200, 900, 900, 1200, 1160]));
C.push(space());
C.push(H2("7.8 Robustness"));
C.push(P(tex(M.RobustText)));

// ---- 8 changes from plan
C.push(H1("8. What changed from the original plan, and why"));
C.push(table(["Original plan", "What we did", "Reason"], [
  ["5 states: AZ, CA, OK, TX, GA", "5 challenge regions (Maricopa AZ, northern CA, eastern OK, south-central TX, eastern WA), 9,794 tracts", "The audit strata (SVI, CVI, tribal, hazards) are distributed for these regions"],
  ["Overture 2025-09-24.0", "2026-08-19.0 primary, plus 2026-10-21.0 and archived 2023-07-26-alpha.0", "Overture deletes releases after about 60 days; the archived copy gives a 3-year time span"],
  ["Gate: buildings or POIs lead", "Both layers reported", "Only 1.9% of tracts below 80% (gate says POIs lead), but buildings carry the regression and catch-up findings"],
  ["ACS covariates only", "ACS + LODES workplace jobs", "Without jobs the POI model explained only R2 = 0.42; with jobs 0.82"],
  ["Split-conformal (MAPIE)", "Cross-fitted CQR on spatial blocks", "Avoids a tract's own deficit shrinking its expectation; adapts width to noise"],
  ["Pre-registration template with blanks", "Completed and frozen before Phases 5-7; original preserved and tested as worded", "Required to run the tests; both are reported for transparency"],
  ["Census County Business Patterns", "ZIP Business Patterns allocated to tracts + county totals", "Tract-level CBP does not exist"],
], [2600, 3600, 3160]));

// ---- 9 github
C.push(H1("9. What is in the GitHub repository"));
C.push(P("Repository: github.com/GTX-Pradeep/invisible-exposure-open-map-equity (branch `main`)."));
C.push(table(["Path", "Contents"], [
  ["`README.md`", "Overview, reproduction steps, headline results"],
  ["`config/config.yaml`", "All settings: regions, releases, ACS tables, model and conformal parameters"],
  ["`src/coverage_risk/db.py`", "DuckDB connection for cloud parquet (proxy-aware), Source Cooperative listing"],
  ["`src/coverage_risk/aggregate.py`", "Per-tract counting of buildings/places with provenance for each release"],
  ["`src/coverage_risk/features.py`", "ACS download and structural features; LODES jobs; audit-only column list"],
  ["`src/coverage_risk/provenance.py`", "Source shares, entropy, single-source flag"],
  ["`src/coverage_risk/model.py`", "Spatial folds, cross-fitted LightGBM quantile + CQR, leakage guard"],
  ["`src/coverage_risk/validation.py`", "CV comparison, flag skill, deletion test"],
  ["`src/coverage_risk/audit.py`", "Group definitions, contrasts, fast cluster bootstrap, BH correction"],
  ["`scripts/`", "One numbered script per phase, `run_all.sh` end to end"],
  ["`docs/preregistration.md`", "Frozen pre-registration with deviations; original template alongside"],
  ["`docs/data_sources.md`", "Versions, licences, independence check"],
  ["`outputs/tables/`", "All result tables (CSV/JSON)"],
  ["`outputs/figures/`", "All figures (PNG/PDF)"],
  ["`paper/`", "Manuscript (LaTeX + PDF); `numbers.tex` is generated"],
  ["`notebooks/`", "Course notebook (`.ipynb`) walking through the pipeline and results"],
  ["`deliverables/`", "This document, IEEE report, one-pager, slides, video script, dataset links"],
], [3400, 5960]));
C.push(H2("9.1 How to reproduce"));
["`python -m venv .venv && . .venv/bin/activate && pip install -e .`",
 "`bash scripts/run_all.sh` (downloads public data and runs everything; about 1.5 hours on 4 cores)",
 "Every number in the paper is written by `scripts/10_paper_numbers.py` from the result tables."].forEach((t) => C.push(N(t, "nums2")));

// ---- 10 limitations
C.push(H1("10. Limitations and future work"));
["USA Structures and Overture's ML footprints both come from imagery, so shared omissions would understate gaps.",
 "The POI reference counts employer establishments and is allocated to tracts by land area, so POI validation is approximate.",
 "Hazard tables are tract averages; hidden exposure assumes missing structures share their tract's hazard.",
 "The 2023 snapshot is a third-party copy of an alpha release.",
 "The five regions were chosen for their hazards, not to represent the United States.",
 "**Future work:** national release-regression monitoring; check whether the San Antonio buildings return; group-level reference comparisons for other feature types (roads, facilities)."].forEach((t) => C.push(B(t)));

// ---- 11 deliverables
C.push(H1("11. Course deliverables checklist"));
C.push(table(["Deliverable", "Status", "Location"], [
  ["1. Final one-pager", "Draft ready; restyle to the course template", "`deliverables/One_Pager.docx`"],
  ["2. Code (.ipynb)", "Ready", "`notebooks/Invisible_Exposure.ipynb`"],
  ["3. Dataset (link/folder)", "Ready", "`deliverables/dataset/` (links + processed tract tables)"],
  ["4. Project PPT", "Draft ready; restyle to the template when it arrives", "`deliverables/Invisible_Exposure_Slides.pptx`"],
  ["5. Video (3-5 min)", "Script ready; team records", "`deliverables/Video_Script.md`"],
  ["6. IEEE-format report", "Ready", "`deliverables/IEEE_Report.pdf` (+ LaTeX source)"],
  ["Google Drive folder", "Team uploads; give TAs and Bhaskarjyoti Das sir view access", "Deadline 16/11/2026 EOD"],
], [2600, 3400, 3360]));

// ---- 12 glossary
C.push(H1("12. Glossary"));
C.push(table(["Term", "Meaning"], [
  ["Overture Maps", "Open map dataset merging OpenStreetMap, machine-learned footprints and other sources"],
  ["Census tract", "Census statistical area of roughly 1,200-8,000 people; the unit of analysis"],
  ["Conformal prediction", "Method that turns any model's predictions into ranges with a guaranteed coverage rate"],
  ["CQR", "Conformalized quantile regression: conformal calibration of a quantile model's band"],
  ["Cross-fitting", "Predicting each tract with a model trained without that tract's fold"],
  ["Mondrian calibration", "Computing the conformal correction separately within each group (here, region)"],
  ["SVI / CVI", "CDC Social Vulnerability Index / Climate Vulnerability Index"],
  ["RUCA", "USDA Rural-Urban Commuting Area codes (>= 4 = rural here)"],
  ["Hidden exposure", "Missing structures in high-hazard tracts, per 1,000 housing units"],
  ["BH / FDR", "Benjamini-Hochberg control of the false discovery rate across many tests"],
  ["Pre-registration", "Hypotheses and tests fixed in advance, before seeing results"],
], [2400, 6960]));

// ---- references
C.push(H1("13. Key references"));
["Haklay, M. (2010). How good is volunteered geographical information? Environment and Planning B, 37(4), 682-703.",
 "Herfort, B. et al. (2023). A spatio-temporal analysis investigating completeness and inequalities of global urban building data in OpenStreetMap. Nature Communications, 14, 3985.",
 "Barrington-Leigh, C., & Millard-Ball, A. (2017). The world's user-generated road map is more than 80% complete. PLOS ONE, 12(8).",
 "Romano, Y., Patterson, E., & Candes, E. (2019). Conformalized quantile regression. NeurIPS 32.",
 "Lei, J. et al. (2018). Distribution-free predictive inference for regression. JASA, 113(523).",
 "Roberts, D. R. et al. (2017). Cross-validation strategies for data with spatial structure. Ecography, 40(8).",
 "Flanagan, B. E. et al. (2011). A social vulnerability index for disaster management. J. Homeland Security & Emergency Mgmt, 8(1).",
 "Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. JRSS-B, 57(1).",
 "Obermeyer, Z. et al. (2019). Dissecting racial bias in an algorithm used to manage the health of populations. Science, 366.",
 "Overture Maps Foundation (2026); ORNL/FEMA USA Structures (2023); Humane Intelligence & Zindi, Bias Bounty: Mapping Equity (2026)."].forEach((t) => C.push(B(t)));

// ======================================================================= document
const doc = new Document({
  creator: "Invisible Exposure team",
  features: { updateFields: true },
  title: "Invisible Exposure: complete project documentation",
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: BLUE }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, color: "2E75B6" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 22, bold: true }, paragraph: { spacing: { before: 180, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }, { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1080, hanging: 270 } } } }] },
    { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    { reference: "nums2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "Invisible Exposure  |  page ", size: 16, color: "808080" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "808080" })] })] }) },
    children: C,
  }],
});
const out = path.join(__dirname, "Invisible_Exposure_Project_Documentation.docx");
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(out, b); console.log("wrote", out); });
