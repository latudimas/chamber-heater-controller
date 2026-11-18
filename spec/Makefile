# Model-check the safety state machine. Needs `tlc` (nix develop).
TLC ?= tlc

.PHONY: check mutants parse clean
check:
	$(TLC) -workers auto -cleanup -metadir /tmp/tlc-heater -config HeaterSafety.cfg HeaterSafety.tla

mutants:
	./check_mutations.sh

parse:
	tlasany HeaterSafety.tla

clean:
	rm -rf states /tmp/tlc-heater *_TTrace_*.tla *_TTrace_*.bin
