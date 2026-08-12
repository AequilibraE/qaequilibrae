from qaequilibrae.modules.common_tools.parameters_dialog import ParameterDialog


def test_load_parameters_dialog(ae_with_project, qtbot):
    dialog = ParameterDialog(ae_with_project)

    assert dialog.but_close.text() == "Cancel and close"

    dialog.current_data = {"assignment": {"equilibrium": {"rgap": True}}}
    dialog.validate_data()

    messagebar = ae_with_project.iface.messageBar()
    assert messagebar.messages[2][0] == "Error:Parameter structure was compromised. Please reset to default.", (
        "Level 2 error message is missing"
    )

    dialog.load_default_data()

    dialog.text_box.append(
        """assignment:
             equilibrium:
                maximum_iterations: 123
                rgap: 0.03"""
    )
    dialog.save_new_parameters()

    assert dialog.current_data["assignment"]["equilibrium"]["maximum_iterations"] == 123
    assert dialog.current_data["assignment"]["equilibrium"]["rgap"] == 0.03
    assert dialog.but_close.text() == "Close"

    dialog.exit_procedure()
