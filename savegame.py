"""
savegame.py - Gravação da run (o "ficheiro gravado" opcional do R3).

Grava-se no INÍCIO de cada sala (o estado do jogador nesse momento, mais a
semente da sala) e, a cada resposta do jogador, o registo das respostas dessa
sala (ver replay.py). Se o jogador fechar o jogo, mesmo a meio de um combate,
retoma exatamente no mesmo ponto. Só existe UMA run guardada de cada vez.
Um ficheiro em falta, corrompido ou adulterado é simplesmente ignorado (R4).
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from cards import valid_card_spec
from fileutil import write_text_atomic
from modes import MODES
from relics import RELIC_FACTORIES

DEFAULT_SAVE = Path(__file__).parent / "save.json"
MAX_LOG = 5000     # respostas por sala (uma sala nunca chega perto)


def _valid_answer(valor):
    """Uma resposta gravada é None, um número ou um texto curto (nada mais)."""
    if valor is None:
        return True
    if isinstance(valor, bool):
        return False
    return isinstance(valor, int) or (isinstance(valor, str) and len(valor) <= 20)


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
    seed: int = 0                                # semente da sala em curso
    log: list = field(default_factory=list)      # respostas já dadas nessa sala


class SaveGame:
    def __init__(self, path=DEFAULT_SAVE):
        # path=None => gravação desligada (testes e simulações)
        self._path = Path(path) if path is not None else None
        self._last = None      # o que se gravou por último (para atualizar só o registo)

    def save(self, player, mode, next_room, total_turns, seed=0, log=()):
        """Grava o estado no início da sala 'next_room'. Devolve False se não conseguiu."""
        self._last = {
            "name": player.name, "hp": player.hp,
            "cards": [c.spec for c in player.deck.cards],
            "relics": [r.name for r in player.relics],
            "mode": mode.key, "next_room": next_room, "total_turns": total_turns,
            "seed": seed, "log": list(log),
        }
        return self._write()

    def update_log(self, log):
        """A cada resposta do jogador: volta a gravar o mesmo estado com o registo novo."""
        if self._last is None:
            return True
        self._last["log"] = list(log)
        return self._write()

    def _write(self):
        if self._path is None:
            return True
        try:
            write_text_atomic(self._path,
                              json.dumps(self._last, indent=2, ensure_ascii=False))
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
        if (any(not valid_card_spec(c) for c in cartas)
                or any(r not in RELIC_FACTORIES for r in reliquias)):
            raise ValueError("cartas ou relíquias desconhecidas")
        if hp < 1 or turnos < 0 or not 1 <= sala <= MODES[modo].rooms:
            raise ValueError("valores fora do intervalo")
        # ficheiros antigos não têm semente nem registo
        semente, registo = d.get("seed", 0), d.get("log", [])
        if not isinstance(semente, int) or isinstance(semente, bool) or semente < 0:
            raise ValueError("semente inválida")
        if (not isinstance(registo, list) or len(registo) > MAX_LOG
                or any(not _valid_answer(r) for r in registo)):
            raise ValueError("registo inválido")
        return RunState(nome, hp, cartas, reliquias, modo, sala, turnos, semente, registo)

    def delete(self):
        """Apaga a gravação (quando a run termina)."""
        if self._path is None:
            return
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass
