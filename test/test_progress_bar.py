from qaequilibrae.modules.common_tools.progress_bars import ProgressBar


def test_progress_bars(ae_with_project, qtbot):
    dialog = ProgressBar(ae_with_project)

    print(qtbot.screenshot(dialog))
