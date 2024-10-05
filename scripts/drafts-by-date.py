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

curr = oldest
prev_month = curr.isoformat()[0:7]
month_total = 0
month_count = 0
while curr < date.today():
    month = curr.isoformat()[0:7]
    if month not in output:
        output[month] = {"month": month, "min": 99999, "max": 0, "avg": -1}

    if month != prev_month:
        output[prev_month]["avg"] = int(month_total / month_count)
        month_total = 0
        month_count = 0
    prev_month = month

    count = 0
    for index in results:
        if curr >= results[index]["start"] and curr <= results[index]["until"]:
            count += 1

    month_total += count
    month_count += 1

    if count < output[month]["min"]:
        output[month]["min"] = count
    if count > output[month]["max"]:
        output[month]["max"] = count

    curr += timedelta(days = 1)

output[prev_month]["avg"] = int(month_total / month_count)


with open(sys.argv[2], "w") as outf:
    for index in output.keys():
        month_date = output[index]["month"]
        month_min  = output[index]["min"]
        month_avg  = output[index]["avg"]
        month_max  = output[index]["max"]
        print(f"{month_date},{month_min},{month_avg},{month_max}", file=outf)

