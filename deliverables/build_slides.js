// Project slide deck (draft; restyle to the course template when it arrives).
// usage: node deliverables/build_slides.js <docdata.json>
const fs = require("fs"), path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/7ef6eba7-fcba-400b-9290-39e248729aee_532e3f45-ffe5-4df0-90a0-60861357a899/pptx/scripts/apply_theme.js");

const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const M = D.macros; const m = (k) => String(M[k]).replace(/\\%/g, "%");
const FIG = (f) => path.join(__dirname, "..", "outputs/figures", f);

const THEME = { name: "Invisible Exposure", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B1F24", lt1: "FFFFFF", dk2: "16324F", lt2: "EEF2F6", accent1: "16324F", accent2: "D9622B",
    accent3: "2F8F83", accent4: "E3A72F", accent5: "7A8796", accent6: "B23A3A", hlink: "2F6FB0", folHlink: "6B4E9B" } };
const HEX = { ink: "16324F", ember: "D9622B", teal: "2F8F83", gold: "E3A72F", slate: "7A8796", light: "EEF2F6", text: "1B1F24", grid: "D5DCE4" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Invisible Exposure"; pres.author = "Invisible Exposure team";
const C = pres.SchemeColor;

pres.defineSlideMaster({ title: "TITLE_DARK", background: { color: C.text2 }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 11.7, h: 1.4, fontSize: 48, bold: true, color: C.background1, fontFace: "Cambria", valign: "bottom", align: "left" }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.75, w: 11.7, h: 1.6, fontSize: 20, color: C.background2, valign: "top", align: "left" }, text: "" } },
] });
pres.defineSlideMaster({ title: "CONTENT", background: { color: C.background1 }, margin: [0.5, 0.6, 0.6, 0.6],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.9, fontSize: 32, bold: true, color: C.text2, fontFace: "Cambria", valign: "middle", align: "left" }, text: "" } },
    { text: { text: "Invisible Exposure  |  ADA course project", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: C.accent5 } } },
  ] });

let n = 0;
const content = (title, section) => { const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section }); s.addText(title, { placeholder: "title" }); n++; return s; };
const txt = (s, t, o) => s.addText(t, { isTextBox: true, fontSize: 16, color: C.text1, valign: "top", margin: 0.05, ...o });
const card = (s, x, y, w, h, fill, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, objectName: name,
  shadow: { type: "outer", color: "9AA5B1", opacity: 0.25, blur: 6, offset: 2, angle: 90 } });
const stat = (s, x, y, w, big, label, col, name) => {
  card(s, x, y, w, 1.55, C.background2, name);
  txt(s, big, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.8, fontSize: 36, bold: true, color: col, fontFace: "Cambria", valign: "middle" });
  txt(s, label, { x: x + 0.2, y: y + 0.92, w: w - 0.4, h: 0.55, fontSize: 13, color: C.text1 });
};
const bullets = (s, items, o) => s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 8 } })),
  { isTextBox: true, fontSize: 16, color: C.text1, valign: "top", ...o });
const img = (s, f, x, y, w, name) => { const b = fs.readFileSync(FIG(f)); const r = b.readUInt32BE(20) / b.readUInt32BE(16);
  s.addImage({ path: FIG(f), x, y, w, h: w * r, objectName: name, altText: name }); return w * r; };
const numCircle = (s, x, y, k, col) => { s.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color: col }, line: { color: col } });
  txt(s, String(k), { x, y, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0 }); };

// 1 title
pres.addSection({ title: "Introduction" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Introduction" });
s.addText("Invisible Exposure", { placeholder: "title" });
s.addText([{ text: "Where open maps miss buildings, who lives there, and whether it is getting better", options: { breakLine: true } },
  { text: "Team [name]  |  Chinthan, Pradeep, [members]  |  ADA course project, November 2026", options: { fontSize: 14 } }], { placeholder: "body" });
s.addNotes("Introduce the team and the one-line idea: climate-risk tools count buildings from open maps, so missing buildings mean missing risk.");

// 2 problem
s = content("Missing buildings mean missing climate risk", "Introduction");
card(s, 0.6, 1.5, 5.9, 5.2, C.background2, "why card");
txt(s, "Why it matters", { x: 0.85, y: 1.7, w: 5.4, h: 0.5, fontSize: 20, bold: true, color: C.text2, fontFace: "Cambria" });
bullets(s, ["Heat, wildfire and drought risk is counted by overlaying hazards on building maps",
  "A building missing from the map is missing from the risk count",
  "Open maps are often less complete in poorer and rural places",
  "A perfect reference map to check against rarely exists"], { x: 0.85, y: 2.3, w: 5.4, h: 4.2 });
card(s, 6.85, 1.5, 5.9, 5.2, C.text2, "problem card");
txt(s, "Problem statement", { x: 7.1, y: 1.7, w: 5.4, h: 0.5, fontSize: 20, bold: true, color: C.background1, fontFace: "Cambria" });
txt(s, "Estimate, without a perfect reference and with honest uncertainty, where Overture Maps is incomplete for every census tract; turn the gaps into hidden climate exposure; and test, under a pre-registered plan, whether gaps fall on vulnerable, rural and tribal communities and close over time.",
  { x: 7.1, y: 2.3, w: 5.4, h: 2.6, fontSize: 16, color: C.background1 });
txt(s, "Design rule: vulnerability and hazard data never enter the model. They are used only in the audit.", { x: 7.1, y: 5.2, w: 5.4, h: 1.2, fontSize: 15, italic: true, color: C.accent4 });
s.addNotes("State the problem statement and the design rule.");

// 3 data
pres.addSection({ title: "Data and method" });
s = content("A large, multi-release study area", "Data and method");
stat(s, 0.6, 1.5, 2.85, m("NTracts"), "census tracts in 5 hazard regions", C.accent1, "tracts");
stat(s, 3.7, 1.5, 2.85, `${m("NBldg")}M`, "Overture buildings (2026-08)", C.accent2, "buildings");
stat(s, 6.8, 1.5, 2.85, "3", "Overture releases: 2023, 2026-08, 2026-10", C.accent3, "releases");
stat(s, 9.9, 1.5, 2.85, `${m("NPop")}M`, "residents", C.accent1, "residents");
const rows = [["Source", "Role"], ["Overture Maps buildings + places", "Map under audit"], ["ACS 2020-2024, LODES 2022 jobs", "Model inputs (structural only)"],
  ["FEMA/ORNL USA Structures, Business Patterns", "Independent references (validation only)"], ["SVI, CVI, rurality, tribal land, heat, wildfire, drought", "Audit only"]];
s.addTable(rows.map((r, i) => r.map((c) => ({ text: c, options: { bold: i === 0, color: i === 0 ? C.background1 : C.text1, fill: { color: i === 0 ? C.text2 : (i % 2 ? C.background1 : C.background2) }, fontSize: 15 } }))),
  { x: 0.6, y: 3.4, w: 12.15, colW: [6.6, 5.55], rowH: 0.55, border: { type: "solid", pt: 0.5, color: HEX.grid }, objectName: "data table" });
txt(s, "Regions: Maricopa AZ, northern CA, eastern OK, south-central TX, eastern WA (Bias Bounty: Mapping Equity challenge)", { x: 0.6, y: 6.35, w: 12.1, h: 0.4, fontSize: 13, color: C.accent5 });
s.addNotes("Describe the data and the three roles: model inputs, references, audit strata.");

// 4 method
s = content("How the method works", "Data and method");
const steps = [["Structural facts", "Housing units, population, land area, jobs per tract"],
  ["Expected count", "LightGBM quantile model, cross-fitted on 50 km spatial blocks"],
  ["Calibrated range", "Conformalized quantile regression: a 90% range for every tract"],
  ["Flag and audit", "Map below the range = flagged; then pre-registered equity tests"]];
steps.forEach(([h, b], i) => { const x = 0.6 + i * 3.1; card(s, x, 1.7, 2.85, 3.0, C.background2, `step ${i + 1}`); numCircle(s, x + 0.25, 1.95, i + 1, i === 3 ? HEX.ember : HEX.ink);
  txt(s, h, { x: x + 0.25, y: 2.65, w: 2.4, h: 0.5, fontSize: 18, bold: true, color: C.text2, fontFace: "Cambria" });
  txt(s, b, { x: x + 0.25, y: 3.2, w: 2.4, h: 1.4, fontSize: 14 });
  if (i < 3) s.addShape(pres.shapes.CHEVRON, { x: x + 2.88, y: 3.0, w: 0.2, h: 0.4, fill: { color: HEX.slate }, line: { color: HEX.slate }, objectName: `arrow ${i + 1}` }); });
card(s, 0.6, 5.1, 12.15, 1.6, C.text2, "guard");
txt(s, "Leakage guard", { x: 0.85, y: 5.25, w: 3, h: 0.45, fontSize: 18, bold: true, color: C.accent4, fontFace: "Cambria" });
txt(s, "The code refuses vulnerability, rurality, tribal and hazard columns as model inputs, so the model cannot learn existing disparities as normal through them. Hypotheses were frozen in a pre-registration before any equity result was seen.",
  { x: 0.85, y: 5.7, w: 11.6, h: 0.9, fontSize: 15, color: C.background1 });
s.addNotes("Walk the four steps left to right; emphasise the guard and pre-registration.");

// 5 validation
pres.addSection({ title: "Results" });
s = content("The ranges are calibrated, and the flags find real gaps", "Results");
stat(s, 0.6, 1.5, 2.9, m("CovBldg"), "coverage of 90% ranges (spatial CV)", C.accent3, "coverage");
stat(s, 0.6, 3.2, 2.9, m("CovLoroBldg"), "when a whole region is held out", C.accent2, "loro");
stat(s, 0.6, 4.9, 2.9, `${m("LiftBldg")}x`, "flags vs chance against USA Structures", C.accent1, "lift");
const del = D.deletion; const xs = [...new Set(del.map((r) => `${Math.round(r.removed_share * 100)}%`))];
s.addChart(pres.charts.LINE, [
  { name: "Buildings", labels: xs, values: del.filter((r) => r.layer === "bldg").map((r) => Math.round(r.detection_rate * 100)) },
  { name: "POIs", labels: xs, values: del.filter((r) => r.layer === "poi").map((r) => Math.round(r.detection_rate * 100)) }],
  { x: 3.85, y: 1.5, w: 8.9, h: 4.95, chartColors: [HEX.ink, HEX.ember], lineSize: 3, lineDataSymbolSize: 8,
    showTitle: true, title: "Deletion test: tracts flagged (%) after removing a share of mapped features", titleFontSize: 15, titleColor: HEX.text, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valAxisMaxVal: 100, valAxisMinVal: 0, valGridLine: { color: HEX.grid, size: 0.5 }, catGridLine: { style: "none" },
    showValue: false, objectName: "deletion chart" });
txt(s, `Removing half of a tract's buildings gets it flagged ${m("DelFiftyBldg")} of the time.`, { x: 3.85, y: 6.5, w: 8.9, h: 0.4, fontSize: 14, italic: true, color: C.accent5 });
s.addNotes("Coverage hits the target; transfer to an unseen region needs local calibration; flags are validated.");

// 6 catch-up
s = content("Open maps caught up from 2023 to 2026", "Results");
const sn = D.snap; const lab = ["2023-07", "2026-08", "2026-10"];
s.addChart(pres.charts.BAR, [
  { name: "Rural", labels: lab, values: sn.map((r) => +(r.lt80_rural_rural * 100).toFixed(1)) },
  { name: "Urban", labels: lab, values: sn.map((r) => +(r.lt80_rural_urban * 100).toFixed(1)) },
  { name: "Tribal", labels: lab, values: sn.map((r) => +(r.lt80_tribal_tribal * 100).toFixed(1)) },
  { name: "Non-tribal", labels: lab, values: sn.map((r) => +(r["lt80_tribal_non-tribal"] * 100).toFixed(1)) }],
  { x: 0.6, y: 1.5, w: 7.6, h: 5.2, barDir: "col", barGrouping: "clustered", chartColors: [HEX.ember, HEX.ink, HEX.gold, HEX.teal],
    showTitle: true, title: "Tracts below 80% of the reference (%)", titleFontSize: 15, titleColor: HEX.text, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.text, dataLabelFormatCode: "0.0", dataLabelFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: HEX.grid, size: 0.5 }, catGridLine: { style: "none" }, objectName: "catch-up chart" });
stat(s, 8.6, 1.5, 4.15, `${m("GapShareA")} to ${m("GapShareB")}`, "all tracts below 80% of reference, 2023 to 2026-08", C.accent3, "gap share");
stat(s, 8.6, 3.25, 4.15, `-${m("DidRuralPP")} pp`, "faster rural catch-up than urban (pre-registered, FDR-significant)", C.accent2, "rural did");
txt(s, "The 2026-10 uptick is a release regression, not real-world change (next slide).", { x: 8.6, y: 5.1, w: 4.15, h: 1.2, fontSize: 15, italic: true, color: C.accent5 });
s.addNotes("Gaps shrank everywhere, fastest in rural and tribal tracts.");

// 7 regression
s = content("A silent release regression in San Antonio", "Results");
img(s, "fig8_bexar_regression.png", 0.6, 1.4, 5.3, "Bexar regression map");
stat(s, 6.4, 1.5, 3.05, `~${m("EOneLost")}`, "buildings dropped from release 2026-09-23 on", C.accent2, "lost");
stat(s, 9.7, 1.5, 3.05, m("EOneResidents"), "residents in the affected tracts", C.accent1, "residents");
stat(s, 6.4, 3.25, 3.05, m("EOneSviShare"), "of affected tracts are high-vulnerability (SVI Q4)", C.accent6, "svi");
stat(s, 9.7, 3.25, 3.05, m("EOneFlagAfter"), "flagged by our model, using no reference", C.accent3, "flagged");
txt(s, `${m("EOneTracts")} tracts lost more than 20% of their buildings between the August and October 2026 releases, almost all Microsoft ML footprints. Before the loss the model flagged only ${m("EOneFlagBefore")} of them; so it can monitor every new release.`,
  { x: 6.4, y: 5.05, w: 6.35, h: 1.6, fontSize: 15 });
s.addNotes("This is our most novel finding: an undocumented data regression that our reference-free model detects.");

// 8 hidden exposure
s = content("Hidden climate exposure concentrates in rural tracts", "Results");
img(s, "fig7_hidden_exposure.png", 0.6, 1.45, 7.0, "hidden exposure chart");
stat(s, 8.0, 1.5, 4.75, `${m("HFiveWildRural")}x`, "missing structures per home in wildfire tracts, rural vs urban", C.accent6, "wildfire");
stat(s, 8.0, 3.2, 4.75, `${m("HFiveDroughtRural")}x`, "same for drought tracts", C.accent4, "drought");
bullets(s, ["Building flags do not differ by social vulnerability", `POI flags are less common in high-SVI tracts (${m("PoiSviHi")} vs ${m("PoiSviLo")})`, "Provenance features did not improve detection (H4 null)"],
  { x: 8.0, y: 4.95, w: 4.75, h: 1.8, fontSize: 14 });
s.addNotes("Pre-registered results with false-discovery-rate control; report nulls honestly.");

// 9 limitation
s = content("What tract-level flags cannot see", "Results");
img(s, "fig5_two_lenses.png", 0.6, 1.45, 6.6, "two lenses chart");
card(s, 7.6, 1.5, 5.15, 2.4, C.background2, "absorption");
txt(s, "Absorption", { x: 7.85, y: 1.65, w: 4.7, h: 0.45, fontSize: 19, bold: true, color: C.text2, fontFace: "Cambria" });
txt(s, `The map-trained model reproduces ${Math.round(D.expl.E2_absorbed_share_rural * 100)}% of the rural shortfall and ${Math.round(D.expl.E2_absorbed_share_tribal * 100)}% of the tribal one: it learns under-mapping as normal.`, { x: 7.85, y: 2.15, w: 4.7, h: 1.6, fontSize: 15 });
card(s, 7.6, 4.15, 5.15, 2.55, C.background2, "resolution");
txt(s, "Resolution", { x: 7.85, y: 4.3, w: 4.7, h: 0.45, fontSize: 19, bold: true, color: C.text2, fontFace: "Cambria" });
txt(s, "Prediction noise per tract is larger than a 20% gap, so even a reference-trained model misses modest gaps. Equity audits need group-level reference comparisons.", { x: 7.85, y: 4.8, w: 4.7, h: 1.8, fontSize: 15 });
s.addNotes("The reference shows rural and tribal gaps 3-4x more often; flags do not. Two mechanisms explain why.");

// 10 novelty
pres.addSection({ title: "Conclusion" });
s = content("Where our novelty stands", "Conclusion");
const nov = [["Uncertainty", "Point estimates", "Calibrated 90% range per tract"], ["Validation", "Random CV", "Spatial blocks, unseen regions, independent references"],
  ["Time", "One snapshot", "Three releases, 2023 to 2026"], ["Monitoring", "Not studied", "Detects a real 2026 release regression"], ["Rigor", "Descriptive", "Pre-registered, FDR-controlled, robustness runs"],
  ["Limits", "Rarely measured", "Quantifies absorption and resolution"]];
s.addTable([[{ text: "Aspect" }, { text: "Prior work" }, { text: "This project" }], ...nov.map((r) => r.map((c) => ({ text: c })))].map((r, i) => r.map((c, j) => ({ text: c.text,
  options: { bold: i === 0 || j === 0, color: i === 0 ? C.background1 : (j === 2 ? C.text2 : C.text1), fill: { color: i === 0 ? C.text2 : (i % 2 ? C.background1 : C.background2) }, fontSize: 16 } }))),
  { x: 0.6, y: 1.5, w: 12.15, colW: [2.6, 3.4, 6.15], rowH: 0.62, border: { type: "solid", pt: 0.5, color: HEX.grid }, objectName: "novelty table" });
txt(s, "Target venues: Computers, Environment and Urban Systems; IJGIS; EPJ Data Science; ACM SIGSPATIAL / FAccT", { x: 0.6, y: 6.15, w: 12.1, h: 0.5, fontSize: 14, italic: true, color: C.accent5 });
s.addNotes("Contrast with prior work (e.g., Herfort et al. 2023) and the challenge submissions.");

// 11 conclusion
s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Conclusion" });
s.addText("Conclusions", { placeholder: "title" });
s.addText([
  { text: "Calibrated completeness estimates, validated against independent references", options: { bullet: true, breakLine: true } },
  { text: "Rural and tribal building gaps closed fastest, 2023 to 2026", options: { bullet: true, breakLine: true } },
  { text: "A silent 2026 regression removed buildings from vulnerable San Antonio tracts, and our model caught it", options: { bullet: true, breakLine: true } },
  { text: "Equity audits must pair tract flags with group-level reference comparisons", options: { bullet: true, breakLine: true } },
  { text: "Code, data and paper: github.com/GTX-Pradeep/invisible-exposure-open-map-equity", options: { breakLine: false, color: HEX.gold } }],
  { placeholder: "body", fontSize: 18, paraSpaceAfter: 6 });
s.addNotes("Summarise and point to the repository; everything reproduces with one command.");

(async () => {
  const out = path.join(__dirname, "Invisible_Exposure_Slides.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out, n + 2, "slides");
})();
