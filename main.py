import sys
from bisect import bisect_left
from enum import Enum, auto

from PyQt6.QtCore import QSize, QUrl, Qt, QThread, QTimeLine
from PyQt6.QtGui import QFont, QIntValidator, QAction
from PyQt6.QtMultimedia import QSoundEffect, QAudioDevice, QMediaDevices
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QFrame, \
    QLineEdit, QMenuBar, QMenu, QMainWindow, QStatusBar


class TempoValidator(QIntValidator):
    def fixup(self, s: str) -> str:
        b = self.bottom()
        if s == '':
            s = str(b)

        while not b <= (n := int(s)) <= (t := self.top()):
            s = str(b) if n < b else str(t)

        return s


class Metronome(QMainWindow):
    __tempi: list[int] = list(range(40, 61, 2)) + \
                         list(range(63, 73, 3)) + \
                         list(range(76, 121, 4)) + \
                         list(range(126, 145, 6)) + \
                         list(range(152, 209, 8))

    class __Mode(Enum):
        maelzel = auto()
        precise = auto()

        def __str__(self):
            match self.name:
                case 'maelzel': return "Maelzel's metronome"
                case 'precise': return 'Precise tempo'

    def __init__(self):
        super().__init__()

        self.__current_tempo: int = self.__tempi[0]
        self.__playing: bool = False
        self.__mode: Metronome.__Mode = self.__Mode.maelzel

        self.thread().setPriority(QThread.Priority.TimeCriticalPriority)

        self.__init_metronome()
        self.__init_window()
        self.__init_ui()
        self.__init_menu()
        self.__init_statusbar()

        self.show()

    def __init_metronome(self) -> None:
        self.__sound_player: QSoundEffect = QSoundEffect()  # QSoundEffect for low latency
        self.__sound_player.setAudioDevice(QAudioDevice(QMediaDevices.defaultAudioOutput()))
        self.__sound_player.setSource(QUrl.fromLocalFile('resources/tick.wav'))

        # Using QTimeLine since it gives better timing than QTimer
        self.__timer: QTimeLine = QTimeLine(600_000)  # 10 minutes. For most music that's enough
        self.__timer.setLoopCount(0)
        self.__timer.valueChanged.connect(self.__sound_player.play)

    def __init_window(self) -> None:
        screen: QSize = QApplication.screens()[0].size()
        sw: int = screen.width()
        sh: int = screen.height()

        w: int = 300
        h: int = 400

        self.setGeometry((sw - w) // 2, (sh - h) // 2, w, h)  # Ensures the window is at the center of the screen
        self.setFixedSize(self.size())
        self.setWindowTitle('MetronomiQ')

    def __init_menu(self) -> None:
        exit_act: QAction = QAction('Exit', self)
        switch_act: QAction = QAction('Switch mode', self)

        for act, short, tip, slot in {(exit_act, 'Ctrl+Q', 'Quit the program', self.close),
                                      (switch_act, 'Ctrl+M', 'Switch operation mode', self.__switch_mode)}:
            act.setShortcut(short)
            act.setStatusTip(tip)
            act.triggered.connect(slot)

        menu_bar: QMenuBar = self.menuBar()
        file_menu: QMenu = menu_bar.addMenu('File')
        file_menu.addActions([switch_act, exit_act])

    def __init_statusbar(self) -> None:
        self.__mode_indicator: QLabel = QLabel(f'Mode: {self.__mode}')

        status_bar = QStatusBar(self)
        status_bar.setSizeGripEnabled(False)
        status_bar.addPermanentWidget(self.__mode_indicator)

        self.setStatusBar(status_bar)

    def __init_ui(self) -> None:
        vbox: QVBoxLayout = QVBoxLayout()
        vbox.addWidget(self.__create_indication())
        vbox.addWidget(self.__create_controls())

        central: QWidget = QWidget()
        central.setLayout(vbox)

        self.setCentralWidget(central)

    def __create_indication(self) -> QFrame:
        tempo_text: QLabel = QLabel('Current tempo:')
        bpm_text: QLabel = QLabel('beats per minute')
        traditional_text: QLabel = QLabel('Traditional tempo marking:')

        self.__tempo_indicator: QLabel = QLabel(str(self.__current_tempo))
        self.__tempo_indicator.setFont(QFont('Gill Sans', 36, QFont.Weight.Bold))

        self.__traditional_marking: QLabel = QLabel(self.__get_marking())
        self.__traditional_marking.setFont(QFont('Gill Sans', 18, QFont.Weight.Bold))

        for widget in {tempo_text, self.__tempo_indicator, bpm_text, traditional_text, self.__traditional_marking}:
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Just in case someone wants to copypaste from this little program
        for widget in {self.__tempo_indicator, self.__traditional_marking}:
            widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        vbox: QVBoxLayout = QVBoxLayout()
        for widget in (tempo_text, self.__tempo_indicator, bpm_text, traditional_text, self.__traditional_marking):
            vbox.addWidget(widget)

        for pos in {0, 4, -1}:
            vbox.insertSpacing(pos, 26)

        frame: QFrame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setLayout(vbox)

        return frame

    def __create_controls(self) -> QFrame:
        # For Maelzel mode
        self.__slider_min: QLabel = QLabel(str(self.__tempi[0]))
        self.__slider_max: QLabel = QLabel(str(self.__tempi[-1]))
        self.__slider: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.__slider.setMinimum(0)
        self.__slider.setMaximum(len(self.__tempi) - 1)
        self.__slider.valueChanged.connect(self.__update_tempo)

        # For precise mode
        self.__tempo_prompt: QLabel = QLabel('Input integer BPM (20–300):')
        self.__tempo_input: QLineEdit = QLineEdit(str(self.__current_tempo))
        self.__tempo_input.setValidator(TempoValidator(20, 300))
        self.__tempo_input.editingFinished.connect(self.__update_tempo)

        # By default, we're in Maelzel mode
        for widget in {self.__tempo_prompt, self.__tempo_input}:
            widget.setVisible(False)
            widget.setEnabled(False)

        for widget in {self.__slider, self.__tempo_input}:
            widget.setStatusTip('Select tempo')

        self.__start_stop_button: QPushButton = QPushButton('Start')
        self.__start_stop_button.setShortcut('Space')
        self.__start_stop_button.setStatusTip('Start/stop count')
        self.__start_stop_button.setMaximumWidth(self.size().width() // 2)
        self.__start_stop_button.pressed.connect(self.__start_stop_metronome)

        hbox_slider: QHBoxLayout = QHBoxLayout()
        for widget in (self.__slider_min, self.__slider, self.__slider_max):
            hbox_slider.addWidget(widget)

        hbox_precise: QHBoxLayout = QHBoxLayout()
        hbox_precise.addWidget(self.__tempo_prompt)
        hbox_precise.addWidget(self.__tempo_input)

        # This is to have centered button
        hbox_button: QHBoxLayout = QHBoxLayout()
        hbox_button.addWidget(self.__start_stop_button)

        vbox: QVBoxLayout = QVBoxLayout()
        for layout in (hbox_slider, hbox_precise, hbox_button):
            vbox.addLayout(layout)
        vbox.insertStretch(2)

        frame: QFrame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setLayout(vbox)

        return frame

    def __switch_mode(self) -> None:
        match self.__mode:
            case self.__Mode.maelzel:
                self.__mode = self.__Mode.precise
                self.__tempo_input.setVisible(True)
                self.__tempo_input.setEnabled(True)
                self.__tempo_prompt.setVisible(True)
                self.__slider.setEnabled(False)
                for widget in (self.__slider_min, self.__slider, self.__slider_max):
                    widget.setVisible(False)
            case self.__Mode.precise:
                self.__mode = self.__Mode.maelzel
                self.__tempo_input.setVisible(False)
                self.__tempo_input.setEnabled(False)
                self.__tempo_prompt.setVisible(False)
                self.__slider.setEnabled(True)
                for widget in (self.__slider_min, self.__slider, self.__slider_max):
                    widget.setVisible(True)

        self.__update_tempo()
        self.__mode_indicator.setText(f'Mode: {self.__mode}')

    def __update_tempo(self) -> None:
        match self.__mode:
            case self.__Mode.maelzel:
                self.__current_tempo = self.__tempi[self.__slider.value()]
                self.__tempo_input.setText(str(self.__current_tempo))
            case self.__Mode.precise:
                if (t := self.__tempo_input.text()) == '':
                    self.__current_tempo = self.__tempi[0]
                else:
                    self.__current_tempo = int(t)
                self.__slider.setValue(bisect_left(self.__tempi, self.__current_tempo))

        self.__tempo_indicator.setText(str(self.__current_tempo))
        self.__traditional_marking.setText(self.__get_marking())

    def __get_marking(self) -> str:
        if self.__current_tempo <= 24:
            return 'Larghissimo'
        elif self.__current_tempo <= 40:
            return 'Grave'
        elif self.__current_tempo <= 60:
            return 'Largo'
        elif self.__current_tempo <= 66:
            return 'Largetto'
        elif self.__current_tempo <= 76:
            return 'Adagio'
        elif self.__current_tempo <= 108:
            return 'Andante'
        elif self.__current_tempo <= 120:
            return 'Moderato'
        elif self.__current_tempo <= 168:
            return 'Allegro'
        elif self.__current_tempo <= 200:
            return 'Presto'
        else:
            return 'Prestissimo'

    def __start_stop_metronome(self) -> None:
        if not self.__playing:
            self.__start_stop_button.setText('Stop')
            self.__slider.setEnabled(False)

            self.__timer.setUpdateInterval(60_000 // self.__current_tempo)
            self.__timer.start()
            self.__playing = True
        else:
            self.__start_stop_button.setText('Start')
            self.__slider.setEnabled(True)

            self.__timer.stop()
            self.__playing = False


if __name__ == '__main__':
    app = QApplication([])
    window = Metronome()
    sys.exit(app.exec())
