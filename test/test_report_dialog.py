from os.path import isfile

from qaequilibrae.modules.common_tools.report_dialog import ReportDialog


def test_report_dialog(sf_project_with_assignment, mocker, qtbot):
    proj = sf_project_with_assignment

    file_path = proj.project.project_base_path / "report_output.txt"
    report = ["This is an example"]

    mocker.patch(
        "qaequilibrae.modules.common_tools.report_dialog.ReportDialog.browse_outfile",
        return_value=file_path,
    )
    dialog = ReportDialog(proj.iface, report)
    dialog.path = file_path

    dialog.save_log()

    assert isfile(dialog.path)

    with open(dialog.path, "r", encoding="utf-8") as file:
        for line in file.readlines():
            assert line == report[0]
