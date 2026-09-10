from string import ascii_letters

from qgis.PyQt.QtWidgets import QTableWidgetItem

from qaequilibrae.modules.common_tools import BaseDialog
from qaequilibrae.modules.style_loader.editor_styles import load_editor_styles

ALLOWED_NAME_CHARACTERS = ascii_letters + "_"


class AddNetworkRecordDialog(BaseDialog):
    """Shared behaviour of the dialogs that add one record to the modes or the link types table.

    Both tables are keyed by a single letter and carry a name that AequilibraE restricts to letters
    and underscores, so listing what the project already has, offering an identifier that is still
    free and checking what was typed is the same work for the two of them. Subclasses name the
    table and the two columns that identify a record in it, and write the record itself.
    """

    table = ""
    id_field = ""
    name_field = ""

    def _base_ui_setup(self):
        self.but_add.clicked.connect(self.add_record)
        self.but_close.clicked.connect(self.exit_procedure)

        self.list_existing()

    def add_record(self):
        """Reads the form and writes the new record to the project."""
        raise NotImplementedError

    def optional_inputs(self) -> dict:
        """Maps each column the form offers besides the identifier and the name to its widgets."""
        return {}

    def existing_records(self) -> dict:
        """Maps every identifier in the project's table to the name that goes with it."""
        with self.project.db_connection as conn:
            return dict(conn.execute(f"select {self.id_field}, {self.name_field} from {self.table}").fetchall())

    def list_existing(self):
        """Fills the table with what the project has, and offers the first identifier still free."""
        with self.project.db_connection as conn:
            cursor = conn.execute(f"select * from {self.table} order by {self.id_field}")
            rows = cursor.fetchall()
            headers = [column[0] for column in cursor.description]

        self.tbl_existing.setColumnCount(len(headers))
        self.tbl_existing.setHorizontalHeaderLabels(headers)
        self.tbl_existing.setRowCount(len(rows))
        for row_number, row in enumerate(rows):
            for column, value in enumerate(row):
                self.tbl_existing.setItem(row_number, column, QTableWidgetItem("" if value is None else str(value)))
        self.tbl_existing.resizeColumnsToContents()

        # A model built by an older AequilibraE can be missing columns the form offers, and writing
        # to one of those goes nowhere, so the form only shows what this project can actually store
        for field, widgets in self.optional_inputs().items():
            for widget in widgets:
                widget.setVisible(field in headers)

        taken = [row[headers.index(self.id_field)] for row in rows]
        available = [letter for letter in ascii_letters if letter not in taken]
        self.txt_id.setText(available[0] if available else "")
        self.but_add.setEnabled(bool(available))
        if not available:
            self.report(self.tr("Every single-letter identifier is already taken"), is_error=True)

    def invalid_input(self, identifier: str, name: str, records: dict):
        """Returns the reason why the form cannot be saved, or None when it can.

        The database only enforces that both fields are unique and that the identifier is a single
        character, and AequilibraE only looks at the name when the record is already being written,
        so everything the user can still fix is checked here instead.
        """
        if len(identifier) != 1 or identifier not in ascii_letters:
            return self.tr("The identifier must be a single letter")
        if identifier in records:
            return self.tr("The identifier is already in use")
        if not name:
            return self.tr("The name cannot be empty")
        if any(character not in ALLOWED_NAME_CHARACTERS for character in name):
            return self.tr('The name can only contain letters and "_"')
        if name.lower() in [str(taken).lower() for taken in records.values()]:
            return self.tr("The name is already in use")
        return None

    def reset_form(self):
        self.txt_name.clear()
        self.txt_description.clear()

        self.list_existing()

    def report(self, message: str, is_error: bool = False):
        self.lbl_feedback.setText(message)
        self.lbl_feedback.setStyleSheet("color: red;" if is_error else "")

    def refresh_link_editing_form(self):
        """The links layer offers the modes and link types read when it was added to the canvas."""
        links = self.qgis_project.layers.get("links")
        if links is not None:
            load_editor_styles(links[0], "links", self.project)

    def exit_procedure(self):
        self.close()
