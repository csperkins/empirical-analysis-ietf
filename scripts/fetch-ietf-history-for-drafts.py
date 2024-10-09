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

from datetime import timedelta

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.rfcindex        import *

def stream_acronym(dt, stream):
    if stream is not None:
        return dt.stream(stream).slug
    else:
        return None

def group_acronym(dt, group):
    if group is not None:
        acronym = dt.group(group).acronym
        if acronym == "none":
            return None
        else:
            return acronym
    else:
        return None


if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <output_file>")
    sys.exit(1)

dt = DataTrackerExt(cache_dir = "data", cache_timeout = timedelta(weeks = 1))

count  = 0
drafts = []
for draft in dt.documents(doctype = dt.document_type_from_slug("draft")):
    count += 1
    print(f"  {count:6} {draft.name}")
    doc = {
        "name"     : draft.name,
        "revision" : draft.rev,
        "group"    : group_acronym(dt, draft.group),
        "stream"   : stream_acronym(dt, draft.stream),
        "history"  : []
    }

    for h in dt.draft_history(draft):
        history = {
            "draft"      : h.draft.name,
            "revision"   : h.rev,
            "date"       : h.date.isoformat(),
            "submission" : None,

        }
        if h.submission is not None:
            history["submission"] = {
                "name"            : h.submission.name,
                "revision"        : h.submission.rev,
                "document_date"   : None,
                "submission_date" : h.submission.submission_date.isoformat(),
                "authors"         : h.submission.authors,
                "title"           : h.submission.title,
                "pages"           : h.submission.pages,
                "group"           : group_acronym(dt, h.submission.group)
            }
            if h.submission.document_date is not None:
                history["submission"]["document_date"] = h.submission.document_date.isoformat()
        doc["history"].append(history)
    drafts.append(doc)

with open(sys.argv[1], "w") as outf:
    json.dump(drafts, outf, indent=3)

