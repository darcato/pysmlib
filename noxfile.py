import nox

# HOW TO RUN TEST SUITE:
# - run `pytest` inside the tests directory to test in the current python env
# - OR run `nox` from the top directory to use multiple python envs
# - OR `gitlab-runner exec docker nox` to test the gitlab CI/CD

@nox.session(python=["3.6", "3.7", "3.8"], venv_backend="conda")
def auto_tests(session):
    session.conda_install("--channel", "conda-forge", "pcaspy", "pytest", "pytest-cov", "pyepics")
    session.install("-e", ".", "--no-deps")
    session.cd("tests")
    session.run("pytest", "--cov=smlib")