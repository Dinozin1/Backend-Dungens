"""
enemies.py - Inimigos e as suas "intenções".

R2: Enemy é uma classe abstrata com choose_action(turn). Cada subclasse
(Bug, Virus, RaceCondition, MemoryLeak, Trojan, Boss) redefine-o com o seu
próprio padrão. O Boss redefine ainda describe_intent(), act() e _start_hp().
"""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

import config
from characters import Character
from modes import DEFAULT_MODE, get_mode


@dataclass
class Intent:
    """O que o inimigo vai fazer no seu turno."""
    kind: str        # "attack", "defend", "weaken", "expose" ou "heal"
    value: int       # dano, bloqueio, turnos ou cura (conforme o tipo)
    hits: int = 1    # nº de golpes (só para ataques)

    def describe(self):
        if self.kind == "attack":
            dano = f"{self.value} de dano" + (f" x{self.hits}" if self.hits > 1 else "")
            return f"vai ATACAR ({dano})"
        if self.kind == "defend":
            return f"vai DEFENDER (+{self.value} de bloqueio)"
        if self.kind == "weaken":
            return f"vai ENFRAQUECER-te ({self.value} turnos)"
        if self.kind == "expose":
            return f"vai EXPOR-te: ficas Vulnerável {self.value} turnos"
        return f"vai CURAR-SE ({self.value} de vida)"

    def short(self):
        """Versão curta, usada no histórico do boss."""
        nomes = {"attack": "Ataque", "defend": "Defesa", "weaken": "Enfraquecer",
                 "expose": "Expor", "heal": "Cura"}
        extra = f"x{self.hits}" if self.hits > 1 else ""
        return f"{nomes[self.kind]} {self.value}{extra}"


class Enemy(Character, ABC):
    """Base dos inimigos. A dificuldade cresce com o PROGRESSO na run."""

    BASE_HP = 20
    HP_PER_ROOM = 4
    BASE_DAMAGE = 4
    DAMAGE_PER_ROOM = 0.5
    NAME = "Inimigo"

    def __init__(self, room, mode=None):
        self._mode = mode or get_mode(DEFAULT_MODE)
        self._room = room
        self._level = self._mode.difficulty_room(room)   # sala "equivalente"
        super().__init__(self.NAME, self._start_hp())
        self._intent = None
        self._turn = 0           # turno atual do combate (para o 'enfurecer')

    def _start_hp(self):
        return int(self.BASE_HP + self.HP_PER_ROOM * (self._level - 1))

    @property
    def room(self):
        return self._room

    @property
    def total_rooms(self):
        return self._mode.rooms

    @property
    def intent(self):
        return self._intent

    @property
    def damage(self):
        """
        Dano base desta sala (cresce ao longo da run). Passado o turno
        ENRAGE_TURN o inimigo enfurece-se: +1 de dano por turno, para que
        nenhum combate se arraste para sempre (anti-impasse).
        """
        enrage = max(0, self._turn - config.ENRAGE_TURN)
        return int(self.BASE_DAMAGE + self.DAMAGE_PER_ROOM * self._level) + enrage

    @abstractmethod
    def choose_action(self, turn):
        """Cada tipo de inimigo decide a sua ação à sua maneira."""

    def _attack(self, multiplier=1.0, hits=1):
        """Cria uma intenção de ataque (já com a fraqueza aplicada)."""
        return Intent("attack",
                      self.outgoing_damage(int(self.damage * multiplier)), hits)

    def plan(self, turn):
        """No início do turno do jogador, o inimigo decide o que vai fazer."""
        self._turn = turn
        self._intent = self.choose_action(turn)

    def describe_intent(self):
        """O que se mostra ao jogador. (O Boss redefine isto.)"""
        return f"{self.name} {self._intent.describe()}"

    def act(self, player):
        """Executa a intenção e devolve as mensagens do que aconteceu."""
        intent = self._intent
        if intent.kind == "attack":
            mensagens = []
            for _ in range(intent.hits):
                resultado = player.receive_attack(intent.value, self)
                mensagens.append(f"{self.name} ataca! {resultado}")
                if not player.is_alive:
                    break
            return mensagens
        if intent.kind == "defend":
            self.gain_block(intent.value)
            return [f"{self.name} ganha {intent.value} de bloqueio."]
        if intent.kind == "weaken":
            player.apply_status("weak", intent.value)
            return [f"{self.name} enfraquece-te: causas -25% de dano "
                    f"durante {intent.value} turnos."]
        if intent.kind == "expose":
            player.apply_status("vulnerable", intent.value)
            return [f"{self.name} expõe-te: recebes +50% de dano "
                    f"durante {intent.value} turnos."]
        curado = self.heal(intent.value)
        return [f"{self.name} cura-se {curado} de vida."]


class Bug(Enemy):
    """Padrão simples: ataca sempre."""
    NAME = "Bug"

    def choose_action(self, turn):
        return self._attack()


class Virus(Enemy):
    """Alterna entre atacar (com mais força) e enfraquecer o jogador."""
    NAME = "Vírus"

    def choose_action(self, turn):
        if turn % 2 == 1:
            return self._attack(1.3)
        return Intent("weaken", 2)


class RaceCondition(Enemy):
    """Dois golpes seguidos (o parry só anula um!); de 3 em 3 turnos defende."""
    NAME = "Race Condition"
    BASE_HP = 18

    def choose_action(self, turn):
        if turn % 3 == 0:
            return Intent("defend", self.damage + 2)
        return self._attack(0.8, hits=2)


class MemoryLeak(Enemy):
    """Ciclo de 3 turnos: defende, ataca com força, cura-se."""
    NAME = "Memory Leak"
    BASE_HP = 24

    def choose_action(self, turn):
        fase = turn % 3
        if fase == 1:
            return Intent("defend", self.damage + 3)
        if fase == 2:
            return self._attack(1.6)
        return Intent("heal", 3 + int(self._level) // 2)


class Trojan(Enemy):
    """Primeiro expõe-te (Vulnerável) e depois bate forte, aproveitando isso."""
    NAME = "Trojan"
    BASE_HP = 22

    def choose_action(self, turn):
        if turn % 2 == 1:
            return Intent("expose", 2)
        return self._attack(1.4)


class Boss(Enemy):
    """
    O boss final. As ações estão ESCONDIDAS, mas seguem um padrão que se
    aprende: ataque, enfraquecer, ataque FORTE, e repete (de 3 em 3 turnos).
    Para ajudar, mostramos o histórico do que já fez.
    """
    NAME = "O Rootkit"
    BASE_DAMAGE = 7

    def __init__(self, room, mode=None):
        super().__init__(room, mode)
        self._history = []

    def _start_hp(self):
        """Redefinido: a vida do boss é fixa e depende só do modo."""
        return self._mode.boss_hp

    @property
    def history(self):
        return tuple(self._history)

    def choose_action(self, turn):
        fase = turn % 3
        if fase == 1:
            return self._attack()
        if fase == 2:
            return Intent("weaken", 2)
        return self._attack(2.0)

    def describe_intent(self):
        """Redefinido: o jogador NÃO vê o que o boss vai fazer."""
        texto = f"{self.name} esconde as suas ações... (???)"
        if self._history:
            texto += "\n  Já fez: " + " -> ".join(self._history)
        return texto

    def act(self, player):
        """Redefinido: depois de agir, regista a ação no histórico."""
        mensagens = super().act(player)
        self._history.append(self._intent.short())
        return mensagens


def spawn_enemy(room, mode=None):
    """Escolhe o inimigo da sala: normais antes da última, boss na última."""
    mode = mode or get_mode(DEFAULT_MODE)
    if room >= mode.rooms:
        return Boss(room, mode)
    nivel = mode.difficulty_room(room)
    tipos = [Bug, Virus]
    if nivel >= 2.5:
        tipos.append(RaceCondition)
    if nivel >= 4:
        tipos += [MemoryLeak, Trojan]
    return random.choice(tipos)(room, mode)
