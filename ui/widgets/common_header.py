# src/ui/widgets/common_header.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QMenu
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPalette, QColor, QAction


class CommonHeaderWidget(QWidget):
    """
    全画面共通ヘッダ。

    仕様:
      - 背景は黒
      - 左端にハンバーガーメニューボタン（☰）
      - その右に「構内セキュリティ」の白文字
      - 文字の背景色は付けない（ヘッダーの黒がそのまま見える）
      - ハンバーガーボタンをクリックするとメニュー(QMenu)が開く
    """

    menu_clicked = Signal()
    person_select_requested = Signal()
    person_list_requested = Signal()
    video_person_select_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(56)
        self._menu: QMenu | None = None
        self._setup_background()
        self._setup_ui()
        self._create_menu()

    def _setup_background(self) -> None:
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))  # 黒
        self.setPalette(palette)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # ハンバーガーボタン（左端）
        self.menu_button = QPushButton("☰", self)
        self.menu_button.setToolTip("メニュー")
        self.menu_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.menu_button.setFlat(True)
        self.menu_button.setStyleSheet(
            "color: white; background: transparent; font-size: 20px; padding: 0 8px;"
        )
        self.menu_button.clicked.connect(self._on_menu_button_clicked)
        layout.addWidget(self.menu_button, 0, alignment=Qt.AlignVCenter)

        # タイトルラベル「車速検知システム」
        self.title_label = QLabel("車速検知システム", self)
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title_label.setStyleSheet(
            "color: white; background: transparent; font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(self.title_label, 0, alignment=Qt.AlignVCenter)

        layout.addStretch(1)

    def _create_menu(self) -> None:
        """
        ハンバーガーボタンから表示するメニュー(QMenu)を作成する。
        """
        menu = QMenu(self)
        menu.setTitle("メニュー")

        menu.setStyleSheet(
            """
            QMenu {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 4px 0;
                margin: 0px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 0px;
            }
            QMenu::item:selected {
                background-color: #00aaff;
                color: #ffffff;
            }
            /* 見出し用（disabled の項目）は薄いグレー、ホバーしても色が変わらない */
            QMenu::item:disabled {
                color: #aaaaaa;
                background: transparent;
            }
            QMenu::item:disabled:selected {
                color: #aaaaaa;
                background: transparent;
            }
            QMenu::separator {
                height: 1px;
                background: #555555;
                margin: 4px 8px;
            }
            """
        )

        # ==============================
        # 見出し
        # ==============================
        section_header = QAction("設定", self)
        section_header.setEnabled(False)

        # ==============================
        # カメラ選択画面
        # ==============================
        self.person_select_action = QAction("カメラ選択", self)
        self.person_select_action.triggered.connect(
            self.person_select_requested.emit
        )
        # ==============================
        # 人物一覧
        # ==============================
        self.person_list_action = QAction("人物一覧", self)
        self.person_list_action.triggered.connect(
            self.person_list_requested.emit
        )

        menu.addAction(section_header)
        menu.addSeparator()
        # ==============================
        # 違反車両一覧
        # ==============================
        self.video_person_select_action = QAction("違反車両一覧", self)
        self.video_person_select_action.triggered.connect(
            self.video_person_select_requested.emit
        )
        menu.addAction(self.video_person_select_action)
        menu.addAction(self.person_select_action)
   #     menu.addAction(self.person_list_action)

        self._menu = menu

    def _on_menu_button_clicked(self) -> None:
        self.menu_clicked.emit()

        if self._menu is None:
            return

        pos = self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())
        self._menu.exec(pos)

    def sizeHint(self) -> QSize:
        return QSize(100, 56)
