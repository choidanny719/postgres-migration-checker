def pytest_addoption(parser):
    parser.addoption("--database-engine", choices=("native", "docker"), default="native")
