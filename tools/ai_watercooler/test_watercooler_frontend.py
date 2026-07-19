from pathlib import Path


def test_internal_console_persists_only_the_theme_preference():
    html = (Path(__file__).with_name("watercooler.html")).read_text(encoding="utf-8")

    assert 'id="theme-toggle"' in html
    assert 'aria-label="Use dark theme"' in html
    assert "ai-watercooler-theme" in html
    assert "prefers-color-scheme: dark" in html
    assert ':root[data-theme="dark"]' in html
    assert "window.localStorage.setItem(THEME_STORAGE_KEY, next)" in html
    assert html.count("localStorage.setItem(") == 1
    assert "localStorage.setItem('token'" not in html
