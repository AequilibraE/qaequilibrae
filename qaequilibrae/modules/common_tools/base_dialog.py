from typing import Optional

from qgis.PyQt import QtWidgets, uic


class BaseDialog(QtWidgets.QDialog):
    """
    Classe base genérica para todos os QDialogs do qaequilibrae.

    Esta classe encapsula a lógica comum de carregamento de UI e inicialização
    básica que é compartilhada entre todos os dialogs do projeto.
    """

    def __init__(
        self,
        ui_file: str,
        qgis_project=None,
        parent: Optional[QtWidgets.QWidget] = None,
        title: Optional[str] = None,
        **kwargs,
    ):
        """
        Inicializa o dialog base.

        Args:
            ui_file (str): Caminho para o arquivo .ui (relativo ao diretório forms/)
            qgis_project: Projeto QGIS (opcional, para compatibilidade)
            parent (QWidget): Widget pai (opcional)
            title (str): Título da janela (opcional)
            **kwargs: Argumentos adicionais para customização
        """
        try:
            super().__init__(parent)
            qgis_project.block_change_scenario()

            # Armazena referências básicas
            self.qgis_project = qgis_project
            self.iface = qgis_project.iface
            self.project = qgis_project.project

            # Carrega a UI
            self.__load_ui(ui_file)

            # Define título se fornecido
            if title:
                self.setWindowTitle(title)

            # Inicialização customizada
            self._base_ui_setup(**kwargs)

            # Conecta sinais padrão
            self.finished.connect(qgis_project.allow_change_scenario)
        except Exception as e:
            qgis_project.allow_change_scenario()
            raise e

    def __load_ui(self, ui_file: str):
        """
        Carrega o arquivo UI especificado.

        Args:
            ui_file (str): Caminho para o arquivo .ui
        """

        uic.loadUi(ui_file, self)

    def _base_ui_setup(self, **kwargs):
        """
        Configuração inicial da UI.
        Deve ser sobrescrita pelas classes filhas para customizações específicas.

        Args:
            **kwargs: Argumentos adicionais passados no construtor
        """
        pass
