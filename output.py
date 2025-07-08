#!/usr/bin/env python3

import csv, json
from pathlib import Path
from typing import Sequence


def write_results(csv_path, headers_to_keep, all_results):


    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as csvf:

        w = csv.writer(csvf) 
        w.writerow(["GameIndex", *headers_to_keep, "Scores"])

        for idx, headers, scores in all_results:
            w.writerow(
                [idx]
                + [headers.get(h, "") for h in headers_to_keep]
                + [json.dumps(scores)]
            )
  
  