PYTHON ?= python3
JOBS ?= 4
SIM_CONFIG ?= config/sim_config.json
RUN_CONFIG ?= config/run_config.json
CLUSTER_CONFIG ?= config/cluster_config.json

all: check-config
	cmake --build build --parallel $(JOBS)
check-config:
	@test -f build/configure.ok && (test -f build/Makefile || test -f build/build.ninja) || { echo 'Configuration is incomplete. Run make configure; see build/configure_*.log and build/dependency-check.log.'; exit 1; }
check-run: check-config
	@test -x build/bin/efficiency_simulator && test -x build/bin/efficiency_merge || { echo 'Executables missing. Run make all successfully before make run-local.'; exit 1; }
configure:
	bash configure.sh $(CMAKE_ARGS)
simulation: check-config
	cmake --build build --target efficiency_simulator --parallel $(JOBS)
merger: check-config
	cmake --build build --target efficiency_merge --parallel $(JOBS)
prepare:
	$(PYTHON) cluster/prepare_jobs.py --sim "$(SIM_CONFIG)" --run "$(RUN_CONFIG)" --cluster "$(CLUSTER_CONFIG)"
# run-local 只运行，不隐式编译。它在小服务器逐个启动作业，每个作业内仍为多线程。
run-local: check-run
	$(MAKE) prepare
	$(PYTHON) cluster/workflow.py local --run-config "$(RUN_CONFIG)"
smoke: all
	$(MAKE) run-local
merge:
	$(PYTHON) cluster/workflow.py merge --run-config "$(RUN_CONFIG)"
check:
	$(PYTHON) cluster/workflow.py check --run-config "$(RUN_CONFIG)"
# 仅 submit 明确提交计算任务；all/configure/prepare 都不会提交或模拟。
submit: prepare
	$(PYTHON) cluster/workflow.py submit --run-config "$(RUN_CONFIG)"
submit-merge:
	$(PYTHON) cluster/workflow.py submit-merge --run-config "$(RUN_CONFIG)"
test: check-config
	bash cluster/setup_env.sh ctest --test-dir build --output-on-failure
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"
help:
	@echo 'configure -> all -> prepare -> submit (cluster), or smoke (small server)'
	@echo 'After all jobs finish: submit-merge; final ROOT is in the configured run directory.'
	@echo 'run-local/check/merge save terminal output to logs/*.log; no plotting targets.'
.PHONY: all check-config check-run configure simulation merger prepare run-local smoke merge check submit submit-merge test help
