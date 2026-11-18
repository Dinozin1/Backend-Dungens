"""
hall_of_fame.py - Recordes guardados em ficheiro JSON.

R3: coleção de objetos (lista de ScoreEntry) + ficheiro gravado e lido.
R4: o ficheiro pode faltar, estar corrompido ou ter entradas inválidas;
nada disso rebenta o jogo. Cada recorde guarda o MODO de jogo, para a
tabela do modo rápido não se misturar com a do modo normal.
"""
import json
import os
from pathlib import Path

import config
from fileutil import write_text_atomic
from names import is_acceptable_name

DEFAULT_PATH = Path(__file__).parent / "scores.json"


class ScoreEntry:
    """Uma linha da tabela de recordes."""

    def __init__(self, name, score, rooms, won, mode="normal"):
        self._name = name
        self._score = score
        self._rooms = rooms
        self._won = won
        self._mode = mode

    @property
    def name(self):
        return self._name

    @property
    def score(self):
        return self._score

    @property
    def rooms(self):
        return self._rooms

    @property
    def won(self):
        return self._won

    @property
    def mode(self):
        return self._mode

    def to_dict(self):
        return {"name": self._name, "score": self._score, "rooms": self._rooms,
                "won": self._won, "mode": self._mode}

    @classmethod
    def from_dict(cls, data):
        """Cria uma entrada a partir de um dicionário, validando os tipos."""
        if not isinstance(data, dict):
            raise ValueError("entrada não é um dicionário")
        name, score = data.get("name"), data.get("score")
        rooms, won = data.get("rooms"), data.get("won")
        mode = data.get("mode", "normal")   # ficheiros antigos não têm modo
        # bool é subclasse de int em Python: "True" não é uma pontuação válida
        if (not isinstance(name, str) or not isinstance(mode, str)
                or not isinstance(won, bool)
                or any(not isinstance(x, int) or isinstance(x, bool) for x in (score, rooms))):
            raise ValueError("campos inválidos")
        if not name.strip() or len(name) > config.PLAYER_NAME_MAX:
            raise ValueError("nome inválido")
        if not is_acceptable_name(name):      # ficheiro editado à mão com nomes impróprios
            raise ValueError("nome não permitido")
        return cls(name, score, rooms, won, mode)


class HallOfFame:
    def __init__(self, path=DEFAULT_PATH):
        # path=None => só em memória (usado nos testes e nas simulações)
        self._path = Path(path) if path is not None else None
        self._entries = []
        self._warning = ""     # aviso para mostrar ao jogador, se algo correu mal
        self.load()

    @property
    def warning(self):
        return self._warning

    @property
    def entries(self):
        return tuple(self._entries)

    def load(self):
        """Lê o ficheiro. Se falhar, começa vazio (e guarda a razão no aviso)."""
        self._entries = []
        self._warning = ""
        if self._path is None:
            return
        try:
            texto = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return                                   # primeira vez: normal
        except OSError as erro:
            self._warning = f"Não foi possível ler os recordes ({erro})."
            return
        try:
            dados = json.loads(texto)
            if not isinstance(dados, list):
                raise ValueError("o ficheiro não contém uma lista")
        except ValueError:                           # JSONDecodeError é ValueError
            self._warning = "O ficheiro de recordes estava corrompido; foi reiniciado."
            self._backup_corrupt_file()
            return
        for item in dados:
            try:
                self._entries.append(ScoreEntry.from_dict(item))
            except ValueError:
                pass                                 # ignora só a entrada inválida

    def _backup_corrupt_file(self):
        """Guarda o ficheiro estragado como .bak para não se perder."""
        try:
            os.replace(self._path, self._path.with_suffix(".bak"))
        except OSError:
            pass

    def save(self):
        """Grava os recordes. Devolve False se não conseguiu."""
        if self._path is None:
            return True
        try:
            dados = [e.to_dict() for e in self._entries]
            write_text_atomic(self._path,
                              json.dumps(dados, indent=2, ensure_ascii=False))
            return True
        except OSError:
            return False

    def add(self, entry):
        self._entries.append(entry)

    def top(self, n=10, mode=None):
        """As n melhores pontuações (opcionalmente só de um modo)."""
        entradas = [e for e in self._entries if mode is None or e.mode == mode]
        return sorted(entradas, key=lambda e: e.score, reverse=True)[:n]
