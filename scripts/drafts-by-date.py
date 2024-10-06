#!/usr/bin/env python3
#
# Copyright (c) 2024 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import sys

from pathlib  import Path
from datetime import date, timedelta

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} history-for-drafts.json <output_file>")
    sys.exit(1)

with open(sys.argv[1], "r") as inf:
    drafts = json.load(inf)

results = {}

oldest = None
newest = None

for draft in drafts:
    prev_start = None
    for h in draft["history"]:
        name  = h['draft'] + "-" + h['revision']
        start = date.fromisoformat(h['date'])
        if prev_start is not None:
            until = prev_start
        else:
            until = start + timedelta(weeks = 24)
        results[name] = {"draft": name, "start": start, "until": until}
        prev_start = start
        if oldest is None or start < oldest:
            oldest = start
        if newest is None or until > newest:
            newest = until

output = {}

curr = date.fromisoformat("1969-01-01")
prev_year = curr.isoformat()[0:4]
year_total = 0
year_count = 0
while curr < date.today():
    year = curr.isoformat()[0:4]
    if year not in output:
        output[year] = {"year": year, "min": 99999, "max": 0, "avg": -1}

    if year != prev_year:
        output[prev_year]["avg"] = int(year_total / year_count)
        year_total = 0
        year_count = 0
    prev_year = year

    count = 0
    for index in results:
        if curr >= results[index]["start"] and curr <= results[index]["until"]:
            count += 1

    year_total += count
    year_count += 1

    if count < output[year]["min"]:
        output[year]["min"] = count
    if count > output[year]["max"]:
        output[year]["max"] = count

    curr += timedelta(days = 1)

output[prev_year]["avg"] = int(year_total / year_count)


with open(sys.argv[2], "w") as outf:
    for index in output.keys():
        year_date = output[index]["year"]
        year_min  = output[index]["min"]
        year_avg  = output[index]["avg"]
        year_max  = output[index]["max"]
        print(f"{year_date},{year_min},{year_avg},{year_max}", file=outf)

