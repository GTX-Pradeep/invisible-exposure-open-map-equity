// One-pager draft (restyle to the course template when available). usage: node build_one_pager.js <docdata.json>
const fs = require("fs"), path = require("path");
const { Document, Packer, Paragraph, TextRun, AlignmentType, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat } = require("docx");
const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8")); const M = D.macros;
const m = (k) => String(M[k]).replace(/\\%/g, "%");
const BLUE = "1F4E79", F = "Arial", W = 11520;
const H = (t) => new Paragraph({ spacing: { before: 160, after: 60 }, children: [new TextRun({ text: t, bold: true, color: BLUE, size: 24, font: F })] });
const P = (t) => new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: t, size: 21, font: F })] });
const B = (t) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 20 }, children: [new TextRun({ text: t, size: 21, font: F })] });
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const col = (w, kids) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none }, margins: { left: 80, right: 80 }, children: kids });
const img = (f, wIn) => { const b = fs.readFileSync(path.join(__dirname, "..", "outputs/figures", f)); const wp = b.readUInt32BE(16), hp = b.readUInt32BE(20); const w = Math.round(wIn * 96);
  return new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: b, transformation: { width: w, height: Math.round(w * hp / wp) }, altText: { title: f, description: f, name: f } })] }); };
const left = [
  H("Problem"), P("Climate-risk tools count exposed buildings from open maps. Where a map is incomplete, buildings and people vanish from the risk count, and a complete reference map rarely exists. We estimate, with calibrated uncertainty and no perfect reference, where Overture Maps is incomplete, convert gaps into hidden heat, wildfire and drought exposure, and test (pre-registered) whether gaps fall on vulnerable, rural and tribal communities and close over time."),
  H("Data"), B(`${m("NTracts")} census tracts, 5 U.S. hazard regions; ${m("NBldg")}M Overture buildings, 3 releases (2023-2026)`),
  B("Inputs: ACS housing/population, LODES jobs. Validation: FEMA/ORNL USA Structures, Census Business Patterns"), B("Audit only: SVI, CVI, rurality, tribal land, heat, wildfire, drought"),
  H("Method"), B("LightGBM quantile model of expected counts from neutral structural facts; audit variables blocked by a code guard"),
  B("Cross-fitted conformalized quantile regression on 50 km spatial blocks: a calibrated 90% range per tract; flag if below"),
  B("Spatial validation, reference skill, deletion test; pre-registered contrasts with Benjamini-Hochberg control"),
  H("Novelty"), B("First calibrated, reference-free completeness audit of Overture across releases"), B("Documents an undetected 2026 release regression and shows the method detects it"), B("Quantifies why tract-level flags miss group-wide gaps"),
];
const right = [
  H("Key results"),
  B(`Coverage ${m("CovBldg")} (target 90%); ${m("CovLoroBldg")} when a region is held out`),
  B(`Flags ${m("LiftBldg")}x better than chance vs USA Structures; 50% loss detected ${m("DelFiftyBldg")}`),
  B(`2023 to 2026: tracts below 80% of reference ${m("GapShareA")} to ${m("GapShareB")}; rural improved ${m("DidRuralPP")} pp more than urban`),
  B(`2026-09 release dropped ~${m("EOneLost")} buildings in ${m("EOneTracts")} San Antonio tracts (${m("EOneResidents")} people); model flagged ${m("EOneFlagAfter")}`),
  B(`Hidden wildfire exposure ${m("HFiveWildRural")}x higher in rural tracts; drought ${m("HFiveDroughtRural")}x`),
  img("fig6_catchup.png", 3.7),
  H("Impact"), P("A monitor for every open-map release with a known false-alarm rate, and guidance for fair climate-risk audits: pair tract flags with group-level reference comparisons."),
  H("Links"), P("Code, data, paper: github.com/GTX-Pradeep/invisible-exposure-open-map-equity"),
];
const doc = new Document({ numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 260, hanging: 180 } } } }] }] },
  styles: { default: { document: { run: { font: F, size: 17 } } } },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 500, bottom: 400, left: 360, right: 360 } } }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Invisible Exposure", bold: true, size: 36, color: BLUE, font: F })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: "Reference-free conformal auditing of open-map completeness and hidden climate-hazard exposure", size: 20, font: F })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE, space: 4 } }, children: [new TextRun({ text: "Team [name]  |  Chinthan, Pradeep, [members]  |  ADA course project, Nov 2026", size: 17, font: F })] }),
    new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W / 2, W / 2], rows: [new TableRow({ children: [col(W / 2, left), col(W / 2, right)] })] }),
  ] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(path.join(__dirname, "One_Pager.docx"), b); console.log("ok"); });
