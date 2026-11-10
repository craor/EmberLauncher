STYLESHEET = """
* { font-family: "Segoe UI", "Inter", "Arial"; }
QLineEdit, QComboBox {
    background: rgba(255, 255, 255, 0.06);
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 18px;
    selection-background-color: #ff8a2a;
    selection-color: #1a1008;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #ff8a2a; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #1b211c;
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.08);
    selection-background-color: #ff8a2a;
    selection-color: #1a1008;
    outline: none;
}
QLabel#title {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 4px;
    color: #f7f3ec;
}
QLabel#subtitle { color: #c8b7a2; font-size: 12px; }
QLabel#credit { color: #ffb15e; font-size: 11px; font-weight: 700; }
QLabel#section {
    color: #aeb8aa;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#muted { color: #b4bcae; font-size: 11px; }
QLabel#ramValue { color: #ffc27a; font-size: 13px; font-weight: 700; }
QLabel#serverTitle {
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #ffe7c4;
}
QLabel#serverSeason { color: #ffb15e; font-size: 13px; font-weight: 700; }
QFrame#card {
    background-color: rgba(12, 16, 14, 176);
    border: 1px solid rgba(255, 214, 170, 0.16);
    border-radius: 22px;
}
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
}
QSlider::sub-page:horizontal { background: #ff8a2a; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: #ffd7a8;
    border: 2px solid #ff8a2a;
    border-radius: 8px;
}
QProgressBar {
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-radius: 5px;
    min-height: 8px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7a18, stop:1 #ffd7a1);
    border-radius: 5px;
}
QDialog#downloadDialog { background: #121614; }
QListWidget {
    background: rgba(255, 255, 255, 0.04);
    color: #f4f1ea;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 6px;
    outline: none;
}
QListWidget::item { padding: 7px 8px; border-radius: 8px; }
QLabel#hello {
    font-size: 26px;
    font-weight: 800;
    color: #ffc27a;
}
QLabel#kicker {
    color: #ffb15e;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
}
QLabel#chip {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 176, 90, 0.35);
    border-radius: 12px;
    padding: 8px 12px;
    color: #ffe7c4;
    font-weight: 700;
}
QLabel#hubTitle { color: #fff4e4; font-size: 16px; font-weight: 800; }
QLabel#hubBody { color: #f4e2cc; font-size: 12px; }
QFrame#sideBar, QFrame#sidePanel, QFrame#centerCard {
    background-color: rgba(10, 14, 12, 196);
    border: 1px solid rgba(255, 176, 90, 0.24);
    border-radius: 22px;
}
QFrame#footerBar {
    background-color: rgba(16, 12, 10, 220);
    border: 1px solid rgba(255, 176, 90, 0.32);
    border-radius: 18px;
}
QFrame#hubCard {
    background-color: rgba(18, 12, 10, 168);
    border: 1px solid rgba(255, 214, 170, 0.28);
    border-radius: 16px;
}
QWidget#scrollBody, QScrollArea { background: transparent; border: none; }
QListWidget::item:selected { background: #6a3414; color: #fff1df; }
QListWidget::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.05);
}
QListWidget::indicator:checked {
    background: #ff8a2a;
    border: 1px solid #ffb15e;
}
QCheckBox { color: #f4f1ea; spacing: 8px; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.05);
}
QCheckBox::indicator:checked { background: #ff8a2a; border: 1px solid #ff8a2a; }
"""


