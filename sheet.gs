// Keeps the "Openings" tab of the tracker sheet in sync with the digest.
// Setup (README → "Google Sheet"): paste this into the sheet's Extensions → Apps Script,
// set the TOKEN script property, and deploy it as a web app.
//
// jobdigest.py posts every open job after each run; this adds new ones, refreshes the
// rest and marks jobs that disappeared as Closed. "Applied on" and "Notes" are yours:
// the script never changes them, except "applied" calls you ask Claude to make.

const HEADERS = ["Status", "Applied on", "Company", "Title", "Region", "Locations",
  "Sponsorship", "Posted", "Via", "First seen", "Last seen", "Closed on", "Notes",
  "Key", "Sources"];
const COL = Object.fromEntries(HEADERS.map((h, i) => [h, i]));
// Alert emails just stop mentioning a job, so they can't tell us it closed.
const UNCHECKABLE = ["email alerts"];

function doPost(e) {
  const req = JSON.parse(e.postData.contents);
  const token = PropertiesService.getScriptProperties().getProperty("TOKEN");
  if (!token || req.token !== token) return reply({error: "bad token"});
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);  // a digest run and an "applied" call could overlap
  try {
    if (req.action === "sync") return reply(sync(req));
    if (req.action === "find") return reply(find(req.query));
    if (req.action === "applied") return reply(markApplied(req.key, req.date));
    return reply({error: "unknown action " + req.action});
  } finally {
    lock.releaseLock();
  }
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function tab() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName("Openings");
  if (!sh) {
    sh = ss.getSheets()[0];
    sh.setName("Openings");
  }
  if (sh.getLastRow() === 0) setUp(sh);
  return sh;
}

function setUp(sh) {
  sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight("bold");
  sh.setFrozenRows(1);
  sh.hideColumns(COL.Key + 1, 2);  // Key and Sources are for the script
  for (const name of ["Applied on", "Posted", "First seen", "Last seen", "Closed on"]) {
    sh.getRange(2, COL[name] + 1, sh.getMaxRows() - 1, 1).setNumberFormat("yyyy-mm-dd");
  }
  const rows = sh.getRange(2, 1, sh.getMaxRows() - 1, HEADERS.length);
  sh.setConditionalFormatRules([  // the first matching rule wins
    SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=$B2<>""')
      .setBackground("#e6f4ea").setRanges([rows]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=$A2="Closed"')
      .setFontColor("#9aa0a6").setRanges([rows]).build(),
  ]);
  sh.getRange(1, 1, sh.getMaxRows(), HEADERS.length).createFilter();
}

function readRows(sh) {
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  const values = sh.getRange(2, 1, n, HEADERS.length).getValues();
  const title = sh.getRange(2, COL.Title + 1, n, 1).getRichTextValues();
  const via = sh.getRange(2, COL.Via + 1, n, 1).getRichTextValues();
  return values.map((row, i) => ({row, title: title[i][0], via: via[i][0]}));
}

function link(text, url) {
  const b = SpreadsheetApp.newRichTextValue().setText(text);
  if (url) b.setLinkUrl(url);
  return b.build();
}

function links(bySource) {
  const names = Object.keys(bySource);
  const b = SpreadsheetApp.newRichTextValue().setText(names.join(" · "));
  let at = 0;
  for (const name of names) {
    b.setLinkUrl(at, at + name.length, bySource[name]);
    at += name.length + 3;
  }
  return b.build();
}

function sync(req) {
  const sh = tab(), today = req.today;
  const recs = readRows(sh);
  const byKey = Object.fromEntries(recs.map(r => [r.row[COL.Key], r]));
  const open = new Set();
  let added = 0, reopened = 0, closed = 0;

  for (const j of req.jobs) {
    open.add(j.key);
    let rec = byKey[j.key];
    if (!rec) {
      rec = byKey[j.key] = {row: HEADERS.map(() => "")};
      rec.row[COL["First seen"]] = j.first_seen;
      recs.push(rec);
      added++;
    } else if (rec.row[COL.Status] === "Closed") {
      reopened++;
    }
    const r = rec.row;
    r[COL.Status] = "Open";
    r[COL.Company] = j.company;
    r[COL.Region] = j.regions.join(", ");
    r[COL.Locations] = j.locations.join("; ");
    r[COL.Sponsorship] = j.sponsorship;
    r[COL.Posted] = j.posted;
    r[COL["Last seen"]] = today;
    r[COL["Closed on"]] = "";
    r[COL.Key] = j.key;
    r[COL.Sources] = j.tasks.join(", ");
    rec.title = link(j.title, j.url);
    rec.via = links(j.links);
  }

  // Close jobs that are gone, unless a board they came from couldn't be read this run.
  const failed = new Set(req.failed);
  for (const {row: r} of recs) {
    if (open.has(r[COL.Key]) || r[COL.Status] !== "Open") continue;
    const tasks = String(r[COL.Sources]).split(", ").filter(Boolean);
    if (tasks.some(t => failed.has(t)) || tasks.every(t => UNCHECKABLE.includes(t))) continue;
    r[COL.Status] = "Closed";
    r[COL["Closed on"]] = today;
    closed++;
  }

  // Open jobs first, newest first.
  const time = v => (v ? new Date(v).getTime() || 0 : 0);
  const newest = r => time(r[COL.Posted]) || time(r[COL["First seen"]]);
  recs.sort((a, b) => (a.row[COL.Status] === "Closed") - (b.row[COL.Status] === "Closed")
    || newest(b.row) - newest(a.row));

  if (recs.length) {
    sh.getRange(2, 1, recs.length, HEADERS.length).setValues(recs.map(r => r.row));
    sh.getRange(2, COL.Title + 1, recs.length, 1).setRichTextValues(recs.map(r => [r.title]));
    sh.getRange(2, COL.Via + 1, recs.length, 1).setRichTextValues(recs.map(r => [r.via]));
  }
  return {added, reopened, closed, rows: recs.length};
}

function describe(r) {
  const day = v => (v instanceof Date ? Utilities.formatDate(v, "UTC", "yyyy-MM-dd") : v);
  return {key: r[COL.Key], company: r[COL.Company], title: r[COL.Title],
          status: r[COL.Status], applied_on: day(r[COL["Applied on"]]),
          region: r[COL.Region], posted: day(r[COL.Posted])};
}

function find(query) {
  const words = String(query).toLowerCase().split(/\s+/).filter(Boolean);
  return {matches: readRows(tab()).map(r => r.row).filter(r => {
    const text = (r[COL.Company] + " " + r[COL.Title]).toLowerCase();
    return words.every(w => text.includes(w));
  }).map(describe)};
}

function markApplied(key, date) {
  const sh = tab();
  const recs = readRows(sh);
  const i = recs.findIndex(r => r.row[COL.Key] === key);
  if (i < 0) return {error: "no row with key " + key};
  sh.getRange(i + 2, COL["Applied on"] + 1).setValue(date);
  recs[i].row[COL["Applied on"]] = date;
  return {updated: describe(recs[i].row)};
}
