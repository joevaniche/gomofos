import pytest_asyncio  # noqa: F401

def pytest_collection_modifyitems(config, items):
    # Auto-mark async tests
    import pytest
    for item in items:
        if "asyncio" in item.keywords:
            continue
        if hasattr(item, "function") and __import__("inspect").iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
