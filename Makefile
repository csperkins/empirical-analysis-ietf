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

# =================================================================================================
# Project specific build rules:

PAPER_PDF = paper.pdf
PAPER_TEX = $(PAPER_PDF:.pdf=.tex)

IETF_DATA = data/ietf/rfc-index.xml

RESULTS = results/rfcs-by-year.csv

FIGURES = figures/rfcs-by-year.pdf

all: $(PAPER_PDF)

$(PAPER_PDF): $(FIGURES)

# -------------------------------------------------------------------------------------------------
# Rules to fetch data:

data:
	mkdir $@

data/ietf: | data
	mkdir $@

data/ietf/rfc-index.xml: scripts/fetch.sh | data/ietf
	@sh scripts/fetch.sh https://www.rfc-editor.org/rfc-index.xml $@


# -------------------------------------------------------------------------------------------------
# Rules to generate results:

results:
	mkdir $@

results/rfcs-by-year.csv: scripts/rfcs-by-year.py data/ietf/rfc-index.xml | results
	python3 $^ $@


# -------------------------------------------------------------------------------------------------
# Rules to build figures:

figures:
	mkdir $@

figures/rfcs-by-year.pdf: scripts/plot-rfcs-by-year.py results/rfcs-by-year.csv | figures
	python3 $^ $@

# -------------------------------------------------------------------------------------------------
# Rules to build the final PDF:

%.pdf: %.tex scripts/latex-build.sh
	@sh scripts/latex-build.sh $<
	@perl scripts/check-for-duplicate-words.perl $<
	@sh scripts/check-for-todo.sh $<
	@sh scripts/check-for-ack.sh  $<

# Include dependency information for PDFs. The scripts/latex-build.sh
# script will generate this as needed. This ensures that the Makefile
# knows to try to build any PDF or TeX files included by the main TeX
# files.
-include $(TEX_FILES:%.tex=%.dep)

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

clean-data: clean
	rm -rf $(IETF_DATA)
	if [ -d data/ietf ]; then rmdir data/ietf; fi
	if [ -d data      ]; then rmdir data;      fi

clean:
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

# Remove obsolete old-style default suffix rules:
.SUFFIXES:

# List of targets that don't represent files:
.PHONY: all clean

# =================================================================================================
# vim: set ts=2 sw=2 tw=0 ai:
