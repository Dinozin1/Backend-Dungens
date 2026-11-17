"""
modes.py - Modos de jogo (normal de 10 salas e rápido de 5 salas).

A dificuldade NÃO depende do número da sala, mas do PROGRESSO na run:
a última sala de qualquer modo tem sempre a dificuldade "de sala 10".
Assim o boss do modo rápido não fica ridiculamente fácil.
"""
from dataclasses import dataclass

REFERENCE_ROOMS = 10     # a escala de dificuldade foi pensada para 10 salas
DEFAULT_MODE = "normal"


@dataclass(frozen=True)
class GameMode:
    key: str            # identificador (usado nos recordes e na gravação)
    label: str          # nome mostrado ao jogador
    rooms: int          # número de salas (a última é o boss)
    boss_hp: int        # vida do boss neste modo
    relic_rooms: tuple  # depois destas salas oferece-se uma relíquia

    def difficulty_room(self, room):
        """Converte a sala atual numa 'sala equivalente' da escala de 10 salas."""
        if self.rooms <= 1:
            return float(REFERENCE_ROOMS)
        return 1 + (room - 1) * (REFERENCE_ROOMS - 1) / (self.rooms - 1)


MODES = {
    "normal": GameMode("normal", "Normal (10 salas)", 10, 75, (3, 6, 9)),
    "curto": GameMode("curto", "Rápido (5 salas)", 5, 55, (2, 4)),
}


def get_mode(key):
    """Devolve o modo pela chave (se for desconhecida, usa o normal)."""
    return MODES.get(key, MODES[DEFAULT_MODE])
