"""Find jobs in the tracker sheet and mark them applied.

    python3 sheet.py find figma ux          # rows whose company + title have all the words
    python3 sheet.py applied "<key>" [date]  # set "Applied on" (default today)

Reads SHEET_URL and SHEET_TOKEN from the environment or from .sheet.env (KEY=value lines).
"""
import datetime
import json
import os
import pathlib
import sys

from jobdigest import sheet_call

ENV_FILE = pathlib.Path(__file__).with_name(".sheet.env")


def main():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            name, _, value = line.partition("=")
            if value:
                os.environ.setdefault(name.strip(), value.strip())
    cmd, *rest = sys.argv[1:] or ["help"]
    if cmd == "find" and rest:
        result = sheet_call({"action": "find", "query": " ".join(rest)})
    elif cmd == "applied" and rest:
        date = rest[1] if len(rest) > 1 else datetime.date.today().isoformat()
        result = sheet_call({"action": "applied", "key": rest[0], "date": date})
    else:
        sys.exit(__doc__)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
