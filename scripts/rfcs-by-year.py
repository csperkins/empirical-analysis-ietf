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

import pandas as pd
import sys

from pathlib              import Path
from time                 import strptime
from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <rfc-index.xml> <output_file>")
    sys.exit(1)

ri = RFCIndex(rfc_index = sys.argv[1])

rfcnum = []
year   = []
stream = []
area   = []

for rfc in ri.rfcs():
    rfcnum.append(rfc.doc_id)
    year.append(rfc.year)
    stream.append(rfc.stream)
    area.append(rfc.area)

df = pd.DataFrame({
        "rfc_num": rfcnum,
        "stream" : stream,
        "year": year,
        "area": area
    })

streams = df.pivot_table(values="rfc_num", aggfunc="count", index="year", columns="stream", fill_value=0)
areas   = df.pivot_table(values="rfc_num", aggfunc="count", index="year", columns="area",   fill_value=0)
totals  = df.groupby("year").agg("count")["rfc_num"]

tmp = pd.merge(totals, streams, on="year").rename(columns={"rfc_num":"Total"})
res = pd.merge(tmp, areas, on="year")

res.to_csv(sys.argv[2], index_label="Year")

