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

import sys

from pathlib              import Path
from time                 import strptime
from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <rfc-index.xml> <output_file>")
    sys.exit(1)

ri = RFCIndex(rfc_index = sys.argv[1])

# Find the publication streams:
streams = []
for rfc in ri.rfcs():
    if rfc.stream not in streams:
        streams.append(rfc.stream)

# Find the IETF areas:
areas = []
for rfc in ri.rfcs():
    if rfc.area not in areas:
        areas.append(rfc.area)

# Find the RFCs per year and stream:
count_year   = {}
count_area   = {}
count_stream = {}

for rfc in ri.rfcs():
    doc_id = rfc.doc_id
    year   = rfc.year
    month  = strptime(rfc.month, "%B").tm_mon
    stream = rfc.stream
    area   = rfc.area

    if year in count_year:
        count_year[year] += 1
        count_area[year][area] += 1
        count_stream[year][stream] += 1
    else:
        count_year[year]   = 0
        count_area[year]   = {}
        count_stream[year] = {}
        for area in areas:
            count_area[year][area] = 0
        for stream in streams:
            count_stream[year][stream] = 0

# Print the results:
with open(sys.argv[2], "w") as outf:
    print("Year", end=",", file=outf)
    for stream in streams:
        print(stream.upper(), end=",", file=outf)
    for area in areas:
        if area is None:
            print("NoArea", end=",", file=outf)
        else:
            print(area.upper(), end=",", file=outf)
    print("Total", file=outf)


    for year in sorted(count_year.keys()):
        print(year, end=",", file=outf)
        for stream in streams:
            print(count_stream[year][stream], end=",", file=outf)
        for area in areas:
            print(count_area[year][area], end=",", file=outf)
        print(count_year[year], file=outf)

