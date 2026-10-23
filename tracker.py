"""Keeps the "Openings" tab of the Google Sheet tracker in sync with the digest.

Signs in as a Google Cloud service account (key JSON in SHEET_SA_KEY) that the sheet
(ID in SHEET_ID, kept secret because this repo is public) is shared with. Each run adds new jobs at the top, refreshes the rest and marks jobs whose
listing disappeared as Closed. "Applied on" and "Notes" belong to the user and are never
written, so rows can be sorted or filtered freely: rows are matched by the hidden Key.
"""
import json
import os
import urllib.parse

from jobdigest import fetch_json

API = "https://sheets.googleapis.com/v4/spreadsheets"
TAB = "Openings"
HEADERS = ["Status", "Applied on", "Company", "Title", "Region", "Locations", "Sponsorship",
           "Posted", "Via", "First seen", "Last seen", "Closed on", "Notes", "Key", "Sources"]
COL = {h: i for i, h in enumerate(HEADERS)}
# Alert emails just stop mentioning a job, so they can't tell us it closed.
UNCHECKABLE = {"email alerts"}


def token():
    from google.oauth2 import service_account  # only needed when the sheet is set up
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["SHEET_SA_KEY"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    creds.refresh(Request())
    return creds.token


class Sheet:
    def __init__(self):
        self.base = f"{API}/{os.environ['SHEET_ID']}"
        self.auth = {"Authorization": f"Bearer {token()}"}

    def get(self, path, **params):
        return fetch_json(f"{self.base}{path}?{urllib.parse.urlencode(params)}",
                          headers=self.auth)

    def update(self, requests):
        if requests:
            fetch_json(f"{self.base}:batchUpdate", {"requests": requests}, headers=self.auth)


def text(value, link=None):
    cell = {"userEnteredValue": {"stringValue": value}}
    if link:
        cell["textFormatRuns"] = [{"startIndex": 0, "format": {"link": {"uri": link}}}]
    return cell


def links(by_source):
    names, runs, at = list(by_source), [], 0
    for name in names:
        runs.append({"startIndex": at, "format": {"link": {"uri": by_source[name]}}})
        runs.append({"startIndex": at + len(name), "format": {}})
        at += len(name) + 3
    value = " · ".join(names)
    return {"userEnteredValue": {"stringValue": value},
            "textFormatRuns": [r for r in runs if r["startIndex"] < len(value)]}


def write(sheet_id, row, cells):
    """updateCells for each run of consecutive bot-owned columns in `cells` ({col: cell})."""
    out, cols = [], sorted(cells)
    while cols:
        run = [cols.pop(0)]
        while cols and cols[0] == run[-1] + 1:
            run.append(cols.pop(0))
        out.append({"updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": row, "columnIndex": run[0]},
            "rows": [{"values": [cells[c] for c in run]}],
            "fields": "userEnteredValue,textFormatRuns"}})
    return out


def set_up(sheet, tabs):
    """Turn the first tab (or a new one) into the Openings tab, once."""
    first = tabs[0]["properties"]
    empty = not sheet.get(f"/values/{urllib.parse.quote(first['title'])}!A1:O2").get("values")
    if empty:
        sid = first["sheetId"]
        reqs = [{"updateSheetProperties": {"properties": {"sheetId": sid, "title": TAB},
                                           "fields": "title"}}]
    else:
        sid = max(t["properties"]["sheetId"] for t in tabs) + 1
        reqs = [{"addSheet": {"properties": {"sheetId": sid, "title": TAB, "index": 0}}}]
    every_row = {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": 0,
                 "endColumnIndex": len(HEADERS)}

    def rule(formula, fmt):
        return {"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [every_row],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
                                          "values": [{"userEnteredValue": formula}]},
                            "format": fmt}}}}

    reqs += [
        {"updateCells": {"start": {"sheetId": sid, "rowIndex": 0, "columnIndex": 0},
                         "rows": [{"values": [
                             dict(text(h), userEnteredFormat={"textFormat": {"bold": True}})
                             for h in HEADERS]}],
                         "fields": "userEnteredValue,userEnteredFormat.textFormat.bold"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid,
                                                  "gridProperties": {"frozenRowCount": 1}},
                                   "fields": "gridProperties.frozenRowCount"}},
        {"updateDimensionProperties": {  # Key and Sources are for the script
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": COL["Key"], "endIndex": len(HEADERS)},
            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}},
        # Added at index 0 in turn, so "applied" ends up first and wins over "closed".
        rule('=$A2="Closed"', {"textFormat": {"foregroundColor":
                                              {"red": .6, "green": .63, "blue": .65}}}),
        rule('=$B2<>""', {"backgroundColor": {"red": .9, "green": .96, "blue": .92}}),
        {"setBasicFilter": {"filter": {"range": {"sheetId": sid, "startRowIndex": 0,
                                                 "startColumnIndex": 0,
                                                 "endColumnIndex": len(HEADERS)}}}},
    ]
    sheet.update(reqs)
    return sid


def sync(jobs, failed, seen, today):
    """Bring the Openings tab up to date. `jobs` are the merged open jobs from this run;
    `failed` names the boards that couldn't be read (their jobs are left as they are)."""
    from jobdigest import primary_link
    sheet = Sheet()
    tabs = sheet.get("", fields="sheets.properties")["sheets"]
    sid = next((t["properties"]["sheetId"] for t in tabs if t["properties"]["title"] == TAB),
               None)
    if sid is None:
        sid = set_up(sheet, tabs)
    rows = sheet.get(f"/values/{TAB}!A2:O").get("values", [])
    rows = [r + [""] * (len(HEADERS) - len(r)) for r in rows]
    where = {r[COL["Key"]]: i + 1 for i, r in enumerate(rows) if r[COL["Key"]]}

    new = [j for j in jobs if j["key"] not in where]
    newest = lambda j: j["posted"] or seen.get(j["key"], today)
    new.sort(key=newest, reverse=True)
    shift = len(new)  # new rows go in at the top, pushing the rest down
    reqs = []
    if new:
        reqs.append({"insertDimension": {"range": {"sheetId": sid, "dimension": "ROWS",
                                                   "startIndex": 1, "endIndex": 1 + shift}}})

    def cells(j, first_seen):
        return {COL["Status"]: text("Open"), COL["Company"]: text(j["company"]),
                COL["Title"]: text(j["title"], primary_link(j)),
                COL["Region"]: text(", ".join(j["regions"])),
                COL["Locations"]: text("; ".join(j["locations"])),
                COL["Sponsorship"]: text(j["sponsorship"]),
                COL["Posted"]: text(j["posted"] or ""), COL["Via"]: links(j["links"]),
                COL["First seen"]: text(first_seen), COL["Last seen"]: text(today),
                COL["Closed on"]: text(""), COL["Key"]: text(j["key"]),
                COL["Sources"]: text(", ".join(sorted(j["tasks"])))}

    for i, j in enumerate(new):
        reqs += write(sid, 1 + i, cells(j, seen.get(j["key"], today)))
    reopened = closed = 0
    open_keys = {j["key"] for j in jobs}
    for j in jobs:
        if j["key"] in where:
            row = rows[where[j["key"]] - 1]
            reopened += row[COL["Status"]] == "Closed"
            reqs += write(sid, where[j["key"]] + shift, cells(j, row[COL["First seen"]]))
    failed = set(failed)
    for key, i in where.items():
        row = rows[i - 1]
        if key in open_keys or row[COL["Status"]] != "Open":
            continue
        tasks = set(filter(None, row[COL["Sources"]].split(", ")))
        if tasks & failed or tasks <= UNCHECKABLE:
            continue
        reqs += write(sid, i + shift, {COL["Status"]: text("Closed"),
                                       COL["Closed on"]: text(today)})
        closed += 1
    sheet.update(reqs)
    return {"added": len(new), "reopened": reopened, "closed": closed}
