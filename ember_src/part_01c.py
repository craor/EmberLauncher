STYLESHEET = """
* { font-family: "Alegreya Sans", "Segoe UI", "Arial"; color: #D9C7A0; }
QLineEdit, QComboBox {
    background: #E7D7B1;
    color: #2B1F17;
    border: 2px solid #4A3426;
    border-radius: 0px;
    padding: 6px 10px;
    min-height: 18px;
    selection-background-color: #E8873A;
    selection-color: #2B1F17;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid #E8873A; }
QComboBox::drop-down { border: none; width: 22px; background: #C4A574; }
QComboBox QAbstractItemView {
    background: #E7D7B1;
    color: #2B1F17;
    border: 2px solid #2B1F17;
    selection-background-color: #E8873A;
    selection-color: #2B1F17;
    outline: none;
}
QLabel#title {
    font-family: "Pixelify Sans", "Alegreya Sans";
    font-size: 18px;
    letter-spacing: 1px;
    color: #E8873A;
}
QLabel#subtitle { color: #C4A574; font-size: 12px; }
QLabel#credit { color: #E8873A; font-size: 11px; font-weight: 700; }
QLabel#section {
    color: #C4A574;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#muted { color: #C4A574; font-size: 12px; }
QLabel#ramValue { color: #E8873A; font-size: 13px; font-weight: 700; }
QLabel#serverTitle {
    font-family: "Pixelify Sans", "Alegreya Sans";
    font-size: 16px;
    color: #E7D7B1;
}
QLabel#serverSeason { color: #E8873A; font-size: 13px; font-weight: 700; }
QFrame#card {
    background-color: #3A291C;
    border: 2px solid #1A120C;
    border-radius: 2px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #1A120C;
    border: 1px solid #2B1F17;
    border-radius: 0px;
}
QSlider::sub-page:horizontal { background: #B3322A; border-radius: 0px; }
QSlider::handle:horizontal {
    width: 14px;
    height: 18px;
    margin: -6px 0;
    background: #E8873A;
    border: 2px solid #2B1F17;
    border-radius: 0px;
}
QProgressBar {
    background: #1A120C;
    border: 2px solid #2B1F17;
    border-radius: 0px;
    min-height: 12px;
    max-height: 12px;
    text-align: center;
    color: #E7D7B1;
}
QProgressBar::chunk { background: #6B8F47; border-radius: 0px; }
QDialog#downloadDialog { background: transparent; }
QListWidget {
    background: #E7D7B1;
    color: #2B1F17;
    border: 2px solid #4A3426;
    border-radius: 0px;
    padding: 4px;
    outline: none;
}
QListWidget::item { padding: 7px 8px; border-radius: 0px; }
QLabel#hello {
    font-family: "Pixelify Sans", "Alegreya Sans";
    font-size: 22px;
    color: #E8873A;
}
QLabel#kicker {
    font-family: "Pixelify Sans", "Alegreya Sans";
    color: #E8873A;
    font-size: 12px;
    letter-spacing: 1px;
}
QFrame#sideBar, QFrame#centerCard, QFrame#sidePanel, QFrame#footerBar, QFrame#hubCard, QFrame#card {
    background: transparent;
    border: none;
}
QStackedWidget, QStackedWidget > QWidget, QScrollArea, QScrollArea QWidget#qt_scrollarea_viewport {
    background: transparent;
    border: none;
}
QFrame#centerCard QLabel#muted, QFrame#centerCard QLabel#newsBody, QFrame#centerCard QLabel#hubBody {
    color: #3A291C;
}
QFrame#centerCard QLabel#hello, QFrame#centerCard QLabel#kicker, QFrame#centerCard QLabel#section, QFrame#centerCard QLabel#ramValue {
    color: #8A3E12;
}
QLabel#chip {
    background: transparent;
    border: 2px solid #1A120C;
    border-radius: 0px;
    padding: 8px 12px;
    color: #2B1F17;
    font-weight: 700;
}
QLabel#packTarget { color: #E7D7B1; font-size: 13px; font-weight: 700; }
QLabel#newsBody { color: #E7D7B1; font-size: 13px; }
QLabel#hubBody { color: #E7D7B1; font-size: 12px; }
QFrame#centerCard QCheckBox { color: #3A291C; }
QWidget#scrollBody, QScrollArea, QStackedWidget, QAbstractScrollArea, QAbstractScrollArea::viewport {
    background: transparent;
    border: none;
}
QListWidget::item:selected { background: #E8873A; color: #2B1F17; }
QListWidget::indicator {
    width: 14px; height: 14px; border-radius: 0px;
    border: 2px solid #2B1F17;
    background: #E7D7B1;
}
QListWidget::indicator:checked { background: #6B8F47; border: 2px solid #2B1F17; }
QCheckBox { color: #E7D7B1; spacing: 8px; }
QCheckBox::indicator {
    width: 14px; height: 14px; border-radius: 0px;
    border: 2px solid #1A120C;
    background: #E7D7B1;
}
QCheckBox::indicator:checked { background: #6B8F47; border: 2px solid #1A120C; }
QScrollBar:vertical {
    background: #2B1F17;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical { background: #6B8F47; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
