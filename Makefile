# Copyright (C) 2024 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

PAPER_PDF := paper.pdf
PAPER_TEX := $(PAPER_PDF:.pdf=.tex)

MAKEFILES := Makefile.ietf-ma

-include $(MAKEFILES)

DOWNLOADS_IETF_DT  := downloads/ietf-dt/api_v1_doc_document.json \
                      downloads/ietf-dt/api_v1_doc_state.json \
                      downloads/ietf-dt/api_v1_doc_statetype.json \
                      downloads/ietf-dt/api_v1_group_group.json \
                      downloads/ietf-dt/api_v1_name_doctagname.json \
                      downloads/ietf-dt/api_v1_name_doctypename.json \
                      downloads/ietf-dt/api_v1_name_draftsubmissionstatename.json \
                      downloads/ietf-dt/api_v1_name_groupstatename.json \
                      downloads/ietf-dt/api_v1_name_grouptypename.json \
                      downloads/ietf-dt/api_v1_name_intendedstdlevelname.json \
                      downloads/ietf-dt/api_v1_name_stdlevelname.json \
                      downloads/ietf-dt/api_v1_name_streamname.json \
                      downloads/ietf-dt/api_v1_person_email.json \
                      downloads/ietf-dt/api_v1_person_person.json \
                      downloads/ietf-dt/api_v1_submit_submission.json \
                      downloads/ietf-dt/api_v1_submit_submissioncheck.json

# The $(DOWNLOADS_IETF_MA_LISTS) variable is defined in Makefile.ietf-ma
DOWNLOADS_IETF_MA  := downloads/ietf-ma/lists.json \
											$(DOWNLOADS_IETF_MA_LISTS)

DOWNLOADS_IETF_RFC := downloads/rfc-index.xml

DOWNLOADS := $(DOWNLOADS_IETF_DT) \
             $(DOWNLOADS_IETF_MA) \
             $(DOWNLOADS_IETF_RFC)

DATA      := data/ietf-dt.sqlite \
             data/ietf-ma.sqlite \
             data/ietf/drafts.json \
             data/ietf/history-for-drafts.json

RESULTS   := results/drafts-by-date.csv \
             results/rfcs-by-year-stream.csv

FIGURES   := figures/drafts-by-date.pdf \
             figures/rfcs-by-year-stream.pdf

all: $(PAPER_PDF)

# -------------------------------------------------------------------------------------------------
# Rules to build makefiles:

Makefile.ietf-ma: scripts/build-makefile-ietf-ma.py downloads/ietf-ma/lists.json
	python3 $^ $@


# -------------------------------------------------------------------------------------------------
# Rules to download data:

download: $(DOWNLOADS)

downloads:
	mkdir $@

# Downloads from the IETF datatracker:

downloads/ietf-dt: | downloads
	mkdir $@

downloads/ietf-dt/api_v1_doc_document.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/doc/document/ id $@

downloads/ietf-dt/api_v1_doc_state.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/doc/state/ id $@

downloads/ietf-dt/api_v1_doc_statetype.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/doc/statetype/ $@

downloads/ietf-dt/api_v1_group_group.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/group/group/ id $@

downloads/ietf-dt/api_v1_name_doctagname.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/doctagname/ $@

downloads/ietf-dt/api_v1_name_doctypename.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/doctypename/ $@

downloads/ietf-dt/api_v1_name_draftsubmissionstatename.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/draftsubmissionstatename/ $@

downloads/ietf-dt/api_v1_name_groupstatename.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/groupstatename/ $@

downloads/ietf-dt/api_v1_name_grouptypename.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/grouptypename/ $@

downloads/ietf-dt/api_v1_name_intendedstdlevelname.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/intendedstdlevelname/ $@

downloads/ietf-dt/api_v1_name_stdlevelname.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/stdlevelname/ $@

downloads/ietf-dt/api_v1_name_streamname.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/name/streamname/ $@

downloads/ietf-dt/api_v1_person_email.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/person/email/ address $@

downloads/ietf-dt/api_v1_person_person.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/person/person/ id $@

downloads/ietf-dt/api_v1_submit_submission.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/submit/submission/ id $@

downloads/ietf-dt/api_v1_submit_submissioncheck.json: scripts/fetch-ietf-dt.py | downloads/ietf-dt
	python3 $^ /api/v1/submit/submissioncheck/ id $@


# Downloads from the IETF mail archive:

downloads/ietf-ma: | downloads
	mkdir $@

downloads/ietf-ma/lists: | downloads/ietf-ma
	mkdir $@

downloads/ietf-ma/lists/%.json: scripts/fetch-ietf-ma-list.py | downloads/ietf-ma/lists
	python3 $^ $@

downloads/ietf-ma/lists.json: scripts/fetch-ietf-ma-lists.py | downloads/ietf-ma
	python3 $^ $@


# Downloads from the RFC Editor:

downloads/rfc-index.xml: | downloads
	curl --remove-on-error -fsL -o $@ https://www.rfc-editor.org/rfc-index.xml 


# -------------------------------------------------------------------------------------------------
# Rules to process the downloads into usable data:

data:
	mkdir $@

data/ietf-dt.sqlite: scripts/build-db-from-ietf-dt.py $(DOWNLOADS_IETF_DT) | data
	python3 $^ $@

data/ietf-ma.sqlite: scripts/build-db-from-ietf-ma.py $(DOWNLOADS_IETF_MA) | data
	python3 $< downloads/ietf-ma/lists.json $@

# The following will likely go away

data/ietf: | data
	mkdir $@

data/ietf/drafts.json: scripts/fetch-ietf-drafts.py | data/ietf
	python3 $^ $@

data/ietf/history-for-drafts.json: scripts/fetch-ietf-history-for-drafts.py | data/ietf
	python3 $^ $@


# -------------------------------------------------------------------------------------------------
# Rules to generate results:

results:
	mkdir $@

results/rfcs-by-year-stream.csv: scripts/rfcs-by-year-stream.py data/rfc-index.xml | results
	python3 $^ $@

results/drafts-by-date.csv: scripts/drafts-by-date.py data/ietf/history-for-drafts.json | results
	python3 $^ $@


# -------------------------------------------------------------------------------------------------
# Rules to build figures:

figures:
	mkdir $@

figures/%.pdf: scripts/plot-%.py results/%.csv | figures
	python3 $^ $@


# -------------------------------------------------------------------------------------------------
# Rules to build the final PDF:

$(PAPER_PDF): $(FIGURES)

%.pdf: %.tex scripts/latex-build.sh
	@sh scripts/latex-build.sh $<
	@perl scripts/check-for-duplicate-words.perl $<
	@sh scripts/check-for-todo.sh $<
	@sh scripts/check-for-ack.sh  $<

# Include dependency information for PDFs. The scripts/latex-build.sh
# script will generate this as needed. This ensures that the Makefile
# knows to try to build any PDF or TeX files included by the main TeX
# files.
-include $(PAPER_TEX:%.tex=%.dep)

# =================================================================================================
# Project specific clean rules:

define xargs
$(if $(2),$(1) $(firstword $(2)))
$(if $(word 2,$(2)),$(call xargs,$(1),$(wordlist 2,$(words $(2)),$(2))))
endef

define remove
$(call xargs,rm -f,$(1))
endef

define remove-latex
$(call xargs,scripts/latex-build.sh --clean,$(1))
endef

clean-downloads: clean
	$(call remove,$(DOWNLOADS))
	if [ -d downloads/ietf-dt ]; then rmdir downloads/ietf-dt; fi
	if [ -d downloads         ]; then rmdir downloads;         fi

clean:
	$(call remove,$(MAKEFILES))
	$(call remove,$(DATA))
	$(call remove,$(FIGURES))
	$(call remove,$(RESULTS))
	if [ -d figures ]; then rmdir figures; fi
	if [ -d results ]; then rmdir results; fi
	$(call remove-latex,$(PAPER_TEX))

# =================================================================================================
# Configuration for make:

# Warn if the Makefile references undefined variables and remove built-in rules:
MAKEFLAGS += --output-sync --warn-undefined-variables --no-builtin-rules --no-builtin-variables

# Remove output of failed commands, to avoid confusing later runs of make:
.DELETE_ON_ERROR:

# Don't remove intermediate files generated as part of the build:
.NOTINTERMEDIATE:

# List of targets that don't represent files:
.PHONY: all clean clean-downloads download

# List of target that should not be built in parallel:
.NOTPARALLEL: download data/ietf-dt.sqlite data/ietf-ma.sqlite

# =================================================================================================
# vim: set ts=2 sw=2 tw=0 ai:
