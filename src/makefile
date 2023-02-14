#! /usr/bin/env make
# pico_energenie/makefile

.PHONY: what
what:
	@echo makefile: for pico_energenie testing
	@echo   make clean         - cleanup all generated files
	@echo   make tests         - make and run all auto tests

#----- PROGRAMS ----------------------------------------------------------------
DIFF      = diff
PYTHON    = python3
LOAD_PICO = ./load_pico

#----- DIRS --------------------------------------------------------------------

#----- FILES -------------------------------------------------------------------

#----- TARGETS -----------------------------------------------------------------
.PHONY: test_energenie
test_energenie:
	$(PYTHON) test_energenie.py > test_energenie.out
	$(DIFF) -q test_energenie.out.cap test_energenie.out

.PHONY: tests
tests: test_energenie

.PHONY:load
load:
	$(LOAD_PICO)

#----- UTILITIES ---------------------------------------------------------------
.PHONY: clean
clean:
	$(RM) *.out

#END: pico_energenie/makefile
