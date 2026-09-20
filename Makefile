.PHONY: verify test demo demo-auto api dashboards clean

verify:
	python3 scripts/verify_environment.py

test:
	python3 -m unittest discover -s tests -v

demo:
	python3 -m demo.simulate_incident

demo-auto:
	python3 -m demo.simulate_incident --auto

api:
	python3 -m api.server

dashboards:
	python3 -m demo.generate_dashboard

clean:
	rm -rf data/*.db docs/evidence/_live tests/_tmp_* __pycache__ */__pycache__ .pytest_cache
