import nox

@nox.session(python=["3.6", "3.7", "3.8"], venv_backend="conda")
def auto_tests(session):
    session.conda_install("--channel", "conda-forge", "pcaspy", "pytest", "pyepics")
    session.install("-e", ".", "--no-deps")
    session.run("pytest")