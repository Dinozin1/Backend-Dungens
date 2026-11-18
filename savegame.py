"""
savegame.py - Gravação da run entre combates (o "ficheiro gravado" opcional do R3).

Grava-se depois de cada combate ganho. Se o jogador fechar o jogo, pode
continuar a partir da última sala. Só existe UMA run guardada de cada vez.
Um ficheiro em falta, corrompido ou adulterado é simplesmente ignorado (R4).
"""
import json
from dataclasses import dataclass
from pathlib import Path

from cards import CARD_FACTORIES
from fileutil import write_text_atomic
from modes import MODES
from relics import RELIC_FACTORIES

DEFAULT_SAVE = Path(__file__).parent / "save.json"


@dataclass
class RunState:
    """Tudo o que é preciso para retomar uma run."""
    name: str
    hp: int
    cards: list
    relics: list
    mode_key: str
    next_room: int
    total_turns: int


class SaveGame:
    def __init__(self, path=DEFAULT_SAVE):
        # path=None => gravação desligada (testes e simulações)
        self._path = Path(path) if path is not None else None

    def save(self, player, mode, next_room, total_turns):
        """Grava o estado da run. Devolve False se não conseguiu."""
        if self._path is None:
            return True
        dados = {
            "name": player.name, "hp": player.hp,
            "cards": [c.name for c in player.deck.cards],
            "relics": [r.name for r in player.relics],
            "mode": mode.key, "next_room": next_room, "total_turns": total_turns,
        }
        try:
            write_text_atomic(self._path,
                              json.dumps(dados, indent=2, ensure_ascii=False))
            return True
        except OSError:
            return False

    def load(self):
        """Devolve um RunState válido, ou None se não há gravação utilizável."""
        if self._path is None:
            return None
        try:
            dados = json.loads(self._path.read_text(encoding="utf-8"))
            return self._validate(dados)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _validate(d):
        """Verifica tudo antes de confiar no ficheiro (lança ValueError se mau)."""
        if not isinstance(d, dict):
            raise ValueError("formato inválido")
        nome, hp, cartas = d.get("name"), d.get("hp"), d.get("cards")
        reliquias, modo = d.get("relics"), d.get("mode")
        sala, turnos = d.get("next_room"), d.get("total_turns")
        ints = (hp, sala, turnos)
        if (not isinstance(nome, str) or not nome.strip()
                or any(not isinstance(x, int) or isinstance(x, bool) for x in ints)
                or not isinstance(cartas, list) or not cartas
                or not isinstance(reliquias, list) or modo not in MODES):
            raise ValueError("campos inválidos")
        if (any(c not in CARD_FACTORIES for c in cartas)
                or any(r not in RELIC_FACTORIES for r in reliquias)):
            raise ValueError("cartas ou relíquias desconhecidas")
        if hp < 1 or turnos < 0 or not 1 <= sala <= MODES[modo].rooms:
            raise ValueError("valores fora do intervalo")
        return RunState(nome, hp, cartas, reliquias, modo, sala, turnos)

    def delete(self):
        """Apaga a gravação (quando a run termina)."""
        if self._path is None:
            return
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass
