def overlay(source, destination, left, top):
	from PyQt6.QtGui import QPainter
	painter = QPainter(destination)
	painter.drawImage(left, top, source)
	painter.end()
