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
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from datetime import datetime
 
if len(sys.argv) != 3:
    print(f"Usage: python3 {sys.argv[0]} <datafile.csv> <output_file.pdf>")
    sys.exit(1)

csv_path = sys.argv[1]
pdf_path = sys.argv[2]

tics = []
data = {}
with open(csv_path, "r") as csv_file:
    for line in csv_file.readlines():
        date,min_count,avg_count,max_count = line.strip().split(",")
        data[int(date)] = (int(min_count), int(avg_count), int(max_count))
        if date.endswith("0"):
            tics.append(int(date))

dates = sorted(data.keys())

mins = [data[date][0] for date in dates]
avgs = [data[date][1] for date in dates]
maxs = [data[date][2] for date in dates]

plt.rc('font',**{'family':'serif','serif':['Times'], 'size': 8})
plt.rc('text', usetex=True)
plt.rc('axes', axisbelow=True)
plt.rcParams['pdf.fonttype'] = 42

plt.figure(figsize=(6,3))
plt.plot(dates, avgs, color="#2678b2", label="Mean")

plt.fill_between(dates, mins, maxs, color="#2678b2", alpha=0.3, lw=0, label="Range")
plt.gca().set_ylim(bottom=0)

plt.xticks(tics, rotation='vertical')
plt.xlabel("Year")
plt.ylabel("Number of Active Internet-Drafts")

plt.legend(loc='upper left')

# Annotate with date IETF created
plt.plot([1986, 1986], [0, 1000], ':', color='black')
plt.text(1982, 1100, 'IETF Created', color='black')

plt.plot()
plt.savefig(pdf_path, format="pdf", bbox_inches="tight")

