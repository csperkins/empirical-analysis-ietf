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

from datetime             import timedelta
from ietfdata.datatracker import *

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


def path_for_draft(draft):
    elem = draft.split("-")
    if len(elem) < 3:
        path = f"data/ietf/drafts/unknown"
    else:
        if draft.startswith("draft-ietf-"):
            path = f"data/ietf/drafts/ietf/{elem[2]}"
        elif draft.startswith("draft-irtf-"):
            path = f"data/ietf/drafts/irtf/{elem[2]}"
        elif draft.startswith("draft-iab-"):
            path = f"data/ietf/drafts/iab"
        else:
            path = f"data/ietf/drafts/individual/{elem[1]}"
    return path


if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <output_file>")
    sys.exit(1)

dt = DataTracker(cache_dir = "data", cache_timeout = timedelta(weeks = 1))

drafts = []
for draft in dt.documents(doctype = dt.document_type_from_slug("draft")):
    name   = draft.name
    title  = draft.title
    pages  = draft.pages
    rfc    = draft.rfc_number
    rev    = draft.rev
    group  = group_acronym(dt, draft.group)
    stream = stream_acronym(dt, draft.stream)
    path   = path_for_draft(draft.name)
    drafts.append({
        "name"   : name,
        "title"  : title,
        "pages"  : pages,
        "rev"    : rev,
        "group"  : group,
        "stream" : stream,
        "path"   : path
    })

with open(sys.argv[1], "w") as outf:
    json.dump(drafts, outf, indent=3)

