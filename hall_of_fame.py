"""
hall_of_fame.py - Recordes guardados em ficheiro JSON.

R3: coleção de objetos (lista de ScoreEntry) + ficheiro gravado e lido.
R4: o ficheiro pode faltar, estar corrompido ou ter entradas inválidas;
nada disso rebenta o jogo.
"""
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "scores.json"


class ScoreEntry:
    """Uma linha da tabela de recordes."""

    def __init__(self, name, score, rooms, won):
        self._name = name
        self._score = score
        self._rooms = rooms
        self._won = won

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

    def to_dict(self):
        return {"name": self._name, "score": self._score,
                "rooms": self._rooms, "won": self._won}

    @classmethod
    def from_dict(cls, data):
        """Cria uma entrada a partir de um dicionário, validando os tipos."""
        if not isinstance(data, dict):
            raise ValueError("entrada não é um dicionário")
        name, score = data.get("name"), data.get("score")
        rooms, won = data.get("rooms"), data.get("won")
        if (not isinstance(name, str) or not isinstance(score, int)
                or not isinstance(rooms, int) or not isinstance(won, bool)):
            raise ValueError("campos inválidos")
        return cls(name, score, rooms, won)


class HallOfFame:
    def __init__(self, path=DEFAULT_PATH):
        self._path = Path(path)
        self._entries = []
        self._warning = ""     # aviso para mostrar ao jogador, se algo correu mal
        self.load()

    @property
    def warning(self):
        return self._warning

    def load(self):
        """Lê o ficheiro. Se falhar, começa vazio (e guarda a razão no aviso)."""
        self._entries = []
        self._warning = ""
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
        try:
            dados = [e.to_dict() for e in self._entries]
            self._path.write_text(json.dumps(dados, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
            return True
        except OSError:
            return False

    def add(self, entry):
        self._entries.append(entry)

    def top(self, n=10):
        """As n melhores pontuações, da maior para a menor."""
        return sorted(self._entries, key=lambda e: e.score, reverse=True)[:n]
