"""Application logo and launch-screen artwork."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

DEVELOPER_CREDIT = "Developed by Farhan Sami"
DEVELOPER_ROLE = "IT Network and System Engineer"


def create_logo(size: int = 128) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = size / 128

    background = QLinearGradient(0, 0, size, size)
    background.setColorAt(0, QColor("#10213b"))
    background.setColorAt(1, QColor("#087e83"))
    painter.setBrush(background)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(2 * scale, 2 * scale, 124 * scale, 124 * scale), 28 * scale, 28 * scale)

    painter.setPen(QPen(QColor("#e3bd68"), 2.5 * scale))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(17 * scale, 17 * scale, 94 * scale, 94 * scale))

    paper = QPainterPath()
    paper.moveTo(43 * scale, 34 * scale)
    paper.lineTo(72 * scale, 34 * scale)
    paper.lineTo(87 * scale, 49 * scale)
    paper.lineTo(87 * scale, 91 * scale)
    paper.quadTo(87 * scale, 96 * scale, 82 * scale, 96 * scale)
    paper.lineTo(43 * scale, 96 * scale)
    paper.quadTo(38 * scale, 96 * scale, 38 * scale, 91 * scale)
    paper.lineTo(38 * scale, 39 * scale)
    paper.quadTo(38 * scale, 34 * scale, 43 * scale, 34 * scale)
    paper.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#f7f5ee"))
    painter.drawPath(paper)
    painter.setBrush(QColor("#d8e2dd"))
    folded_corner = QPainterPath()
    folded_corner.moveTo(72 * scale, 35 * scale)
    folded_corner.lineTo(72 * scale, 49 * scale)
    folded_corner.lineTo(86 * scale, 49 * scale)
    folded_corner.closeSubpath()
    painter.drawPath(folded_corner)

    painter.setPen(QPen(QColor("#73908d"), 2.4 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(47 * scale, 58 * scale), QPointF(77 * scale, 58 * scale))
    painter.drawLine(QPointF(47 * scale, 67 * scale), QPointF(77 * scale, 67 * scale))
    painter.drawLine(QPointF(47 * scale, 76 * scale), QPointF(66 * scale, 76 * scale))

    painter.setBrush(QColor("#e3bd68"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(65 * scale, 73 * scale, 34 * scale, 34 * scale))
    painter.setPen(QPen(QColor("#10213b"), 3 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(QPointF(73 * scale, 90 * scale), QPointF(80 * scale, 97 * scale))
    painter.drawLine(QPointF(80 * scale, 97 * scale), QPointF(92 * scale, 83 * scale))
    painter.end()
    return pixmap


def create_splash_pixmap() -> QPixmap:
    width, height = 640, 380
    pixmap = QPixmap(width, height)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    background = QLinearGradient(0, 0, width, height)
    background.setColorAt(0, QColor("#0c1930"))
    background.setColorAt(1, QColor("#075d69"))
    painter.fillRect(pixmap.rect(), background)

    painter.setPen(QPen(QColor(255, 255, 255, 22), 1))
    for x in range(0, width, 32):
        painter.drawLine(x, 0, x, height)
    for y in range(0, height, 32):
        painter.drawLine(0, y, width, y)

    logo = create_logo(112)
    painter.drawPixmap((width - logo.width()) // 2, 48, logo)

    painter.setPen(QColor("#f7f5ee"))
    title_font = QFont("Segoe UI", 24, QFont.Weight.DemiBold)
    painter.setFont(title_font)
    painter.drawText(QRectF(30, 184, width - 60, 42), Qt.AlignmentFlag.AlignCenter, "Meezan Cheque Printer")

    painter.setPen(QColor("#c9d9dc"))
    subtitle_font = QFont("Segoe UI", 10)
    painter.setFont(subtitle_font)
    painter.drawText(QRectF(30, 230, width - 60, 26), Qt.AlignmentFlag.AlignCenter, "Local cheque preparation and print calibration")

    painter.setPen(QColor("#e3bd68"))
    credit_font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
    painter.setFont(credit_font)
    painter.drawText(QRectF(30, 302, width - 60, 22), Qt.AlignmentFlag.AlignCenter, DEVELOPER_CREDIT)

    painter.setPen(QColor("#c9d9dc"))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(QRectF(30, 326, width - 60, 20), Qt.AlignmentFlag.AlignCenter, DEVELOPER_ROLE)
    painter.end()
    return pixmap
