"""
Snakes Game Module
Classic Snake game using PyQt5.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QKeyEvent

class SnakesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snakes Game")
        self.setGeometry(200, 200, 400, 400)
        self.setFocusPolicy(Qt.StrongFocus)

        self.snake = [(200, 200), (190, 200), (180, 200)]
        self.direction = (10, 0)
        self.food = (100, 100)
        self.score = 0
        self.game_over = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        # Draw snake
        painter.setBrush(QColor(0, 255, 0))
        for x, y in self.snake:
            painter.drawRect(x, y, 10, 10)

        # Draw food
        painter.setBrush(QColor(255, 0, 0))
        painter.drawRect(self.food[0], self.food[1], 10, 10)

        # Draw score
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 20, f"Score: {self.score}")

        if self.game_over:
            painter.drawText(150, 200, "Game Over! Press R to restart")

    def keyPressEvent(self, event: QKeyEvent):
        if self.game_over and event.key() == Qt.Key_R:
            self.restart_game()
            return

        if event.key() == Qt.Key_Left and self.direction != (10, 0):
            self.direction = (-10, 0)
        elif event.key() == Qt.Key_Right and self.direction != (-10, 0):
            self.direction = (10, 0)
        elif event.key() == Qt.Key_Up and self.direction != (0, 10):
            self.direction = (0, -10)
        elif event.key() == Qt.Key_Down and self.direction != (0, -10):
            self.direction = (0, 10)

    def update_game(self):
        if self.game_over:
            return

        head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])

        # Check wall collision
        if head[0] < 0 or head[0] >= 400 or head[1] < 0 or head[1] >= 400:
            self.game_over = True
            self.update()
            return

        # Check self collision
        if head in self.snake:
            self.game_over = True
            self.update()
            return

        self.snake.insert(0, head)

        # Check food
        if head == self.food:
            self.score += 1
            self.food = ( (head[0] + 50) % 400, (head[1] + 50) % 400 )
        else:
            self.snake.pop()

        self.update()

    def restart_game(self):
        self.snake = [(200, 200), (190, 200), (180, 200)]
        self.direction = (10, 0)
        self.food = (100, 100)
        self.score = 0
        self.game_over = False
        self.update()