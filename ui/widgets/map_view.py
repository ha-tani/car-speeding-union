# ui/widgets/map_view.py
"""
MapGraphicsView — プレースホルダー版（config 依存なし）
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QGraphicsRectItem,
)
from PySide6.QtGui import QPixmap, QBrush, QColor, QPen
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem


class ClickableCameraIcon(QGraphicsPixmapItem):
    """クリックで通常/選択状態の画像が切り替わるカメラアイコン。"""

    def __init__(
        self,
        pixmap_normal: QPixmap,
        pixmap_selected: QPixmap,
        camera_name: str = "",
        on_clicked=None,
        parent=None,
    ) -> None:
        super().__init__(pixmap_normal, parent)
        self._pixmap_normal = pixmap_normal
        self._pixmap_selected = pixmap_selected
        self._camera_name = camera_name
        self._on_clicked = on_clicked
        self._selected_state: bool = False
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(1)

    def set_selected(self, state: bool) -> None:
        self._selected_state = state
        self.setPixmap(self._pixmap_selected if state else self._pixmap_normal)

    def mousePressEvent(self, event) -> None:
        if self._on_clicked is not None:
            self._on_clicked(self._camera_name)
        event.accept()


class MapGraphicsView(QGraphicsView):
    """
    サイドバー内のマップ表示用ビュー（プレースホルダー版）。
    """

    zoom_changed = Signal(int)
    camera_icon_clicked = Signal(str)
    selection_limit_reached = Signal(str)
    clear_message = Signal()

    def __init__(self, parent=None, initial_map_id: str = "") -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self._zoom_percent: int = 100
        self._min_zoom: int = 100
        self._max_zoom: int = 250
        self._zoom_step: int = 10

        self._map_id: str | None = None
        self._map_pixmap_item: QGraphicsPixmapItem | None = None
        self._placeholder_item: QGraphicsTextItem | None = None
        self._camera_icons: list[ClickableCameraIcon] = []

        self.load_map(initial_map_id)

    def zoom_in(self) -> None:
        new_val = min(self._zoom_percent + self._zoom_step, self._max_zoom)
        if new_val != self._zoom_percent:
            self._apply_zoom(new_val)

    def zoom_out(self) -> None:
        new_val = max(self._zoom_percent - self._zoom_step, self._min_zoom)
        if new_val != self._zoom_percent:
            self._apply_zoom(new_val)

    def reset_view(self) -> None:
        self._apply_zoom(100)

    def _apply_zoom(self, percent: int) -> None:
        self._zoom_percent = max(self._min_zoom, min(self._max_zoom, percent))
        t = self.transform()
        t.reset()
        self.setTransform(t)
        scale_factor = self._zoom_percent / 100.0
        self.scale(scale_factor, scale_factor)
        self.zoom_changed.emit(self._zoom_percent)

    def get_selected_camera_names(self) -> list[str]:
        return [icon for icon in self._camera_icons if icon._selected_state]

    def _on_icon_clicked(self, camera_name: str) -> None:
        self._select_icons(camera_name)
        self.camera_icon_clicked.emit(camera_name)

    def select_camera(self, camera_name: str) -> None:
        self._select_icons(camera_name)

    def _select_icons(self, camera_name: str) -> None:
        select_all = (camera_name == "すべてのカメラ")
        for icon in self._camera_icons:
            icon.set_selected(select_all or icon._camera_name == camera_name)

    def load_map(self, map_id: str) -> None:
        self._scene.clear()
        self._map_pixmap_item = None
        self._placeholder_item = None
        self._camera_icons = []

        assets_dir = Path(__file__).parent.parent.parent / "assets"
        png_path: Path | None = None

        if map_id:
            candidate = assets_dir / f"{map_id}.png"
            if candidate.exists():
                png_path = candidate

        if png_path is None:
            # カメラアイコン以外のpngをマップ画像候補とする
            icon_names = {"orange_0.png", "red_0.png"}
            pngs = sorted(p for p in assets_dir.glob("*.png") if p.name not in icon_names)
            if pngs:
                png_path = pngs[0]

        if png_path is not None:
            pixmap = QPixmap(str(png_path))
            if not pixmap.isNull():
                self._map_pixmap_item = QGraphicsPixmapItem(pixmap)
                self._scene.addItem(self._map_pixmap_item)
                self._scene.setSceneRect(QRectF(pixmap.rect()))
                self._map_id = map_id or png_path.stem

                # カメラアイコンをマップ上に配置
                icon_defs = [
                    # (通常時画像ファイル名, 選択時画像ファイル名, x座標, y座標, カメラ名)
                    ("orange_6.png", "red_6.png", 246, 145, "カメラA"),
                    # ↓ MAP上にアイコンを追加する場合はここに記載
                    ("orange_6.png", "red_6.png", 265, 145, "カメラB"),
                    # ↓ MAP上にアイコンを追加する場合はここに記載
                    ("orange_6.png", "red_6.png", 285, 145, "カメラC"),
                ]
                
                self._camera_icons = []
                for normal_name, selected_name, x, y, camera_name in icon_defs:
                    pix_n = QPixmap(str(assets_dir / normal_name)).scaled(20, 20)
                    pix_s = QPixmap(str(assets_dir / selected_name)).scaled(20, 20)
                    if not pix_n.isNull() and not pix_s.isNull():
                        icon = ClickableCameraIcon(
                            pix_n, pix_s,
                            camera_name=camera_name,
                            on_clicked=self._on_icon_clicked,
                        )
                        icon.setPos(x, y)
                        self._scene.addItem(icon)
                        self._camera_icons.append(icon)
                return

        # 画像が読み込めなかった場合のみプレースホルダーを表示
        self._scene.setSceneRect(0, 0, 400, 300)
        self._placeholder_item = self._scene.addText("マップ（プレースホルダー）")
        self._placeholder_item.setDefaultTextColor(QColor("#888888"))
        self._placeholder_item.setPos(100, 130)
        self._map_id = None

    def get_current_map_id(self) -> str | None:
        return self._map_id
