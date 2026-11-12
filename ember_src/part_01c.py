STYLESHEET = """
* { font-family: "Alegreya Sans", "Segoe UI", "Arial"; color: #1B2430; }
QLineEdit, QComboBox {
    background: rgba(255, 255, 255, 0.92);
    color: #1B2430;
    border: 1px solid rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    padding: 8px 14px;
    min-height: 20px;
    selection-background-color: #5B4BFF;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #5B4BFF; }
QComboBox::drop-down { border: none; width: 26px; background: transparent; }
QComboBox QAbstractItemView {
    background: #F7F4EF;
    color: #1B2430;
    border: 1px solid #E4DDD4;
    border-radius: 12px;
    selection-background-color: #5B4BFF;
    selection-color: #FFFFFF;
    outline: none;
    padding: 4px;
}
QLabel#title {
    font-family: "Alegreya Sans", "Segoe UI";
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #1B2430;
}
QLabel#subtitle { color: #6A5AE0; font-size: 12px; font-weight: 700; }
QLabel#credit { color: #5B4BFF; font-size: 11px; font-weight: 700; }
QLabel#section {
    color: #7B8794;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.4px;
}
QLabel#muted { color: #5C6B7A; font-size: 13px; }
QLabel#ramValue { color: #5B4BFF; font-size: 13px; font-weight: 700; }
QLabel#serverTitle {
    font-family: "Alegreya Sans", "Segoe UI";
    font-size: 18px;
    font-weight: 700;
    color: #1B2430;
}
QLabel#serverSeason { color: #5B4BFF; font-size: 13px; font-weight: 700; }
QFrame#card {
    background-color: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 22px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: rgba(255, 255, 255, 0.7);
    border: none;
    border-radius: 4px;
}
QSlider::sub-page:horizontal { background: #5B4BFF; border-radius: 4px; }
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: #FFFFFF;
    border: 2px solid #5B4BFF;
    border-radius: 9px;
}
QProgressBar {
    background: rgba(255, 255, 255, 0.72);
    border: none;
    border-radius: 7px;
    min-height: 10px;
    max-height: 10px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk { background: #5B4BFF; border-radius: 7px; }
QDialog#downloadDialog { background: transparent; }
QListWidget {
    background: rgba(255, 255, 255, 0.9);
    color: #1B2430;
    border: 1px solid rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    padding: 6px;
    outline: none;
}
QListWidget::item { padding: 8px 10px; border-radius: 12px; }
QLabel#hello {
    font-family: "Alegreya Sans", "Segoe UI";
    font-size: 40px;
    font-weight: 700;
    color: #1B2430;
}
QLabel#kicker {
    font-family: "Alegreya Sans", "Segoe UI";
    color: #7B8794;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
}
QFrame#sideBar, QFrame#centerCard, QFrame#sidePanel, QFrame#footerBar, QFrame#hubCard, QFrame#card {
    background: transparent;
    border: none;
}
QStackedWidget, QStackedWidget > QWidget, QScrollArea, QScrollArea QWidget#qt_scrollarea_viewport {
    background: transparent;
    border: none;
}
QLabel#packTarget { color: #1B2430; font-size: 13px; font-weight: 700; }
QLabel#newsBody { color: #1B2430; font-size: 14px; }
QLabel#hubBody { color: #3C4654; font-size: 13px; }
QFrame#centerCard QCheckBox, QCheckBox { color: #1B2430; spacing: 8px; }
QWidget#scrollBody, QScrollArea, QStackedWidget, QAbstractScrollArea, QAbstractScrollArea::viewport {
    background: transparent;
    border: none;
}
QListWidget::item:selected { background: #5B4BFF; color: #FFFFFF; }
QListWidget::indicator, QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid #C9C2D8;
    background: #FFFFFF;
}
QListWidget::indicator:checked, QCheckBox::indicator:checked {
    background: #5B4BFF;
    border: 1px solid #5B4BFF;
}
QLabel#chip {
    background: rgba(255, 255, 255, 0.88);
    border: none;
    border-radius: 14px;
    padding: 8px 12px;
    color: #1B2430;
    font-weight: 700;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(91, 75, 255, 0.45);
    min-height: 28px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
