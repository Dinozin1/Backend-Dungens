"""
enemies.py - Inimigos e as suas "intenções".

R2: Enemy é uma classe abstrata com choose_action(turn). Cada subclasse
(Bug, Virus, MemoryLeak, Boss) redefine-o com o seu próprio padrão.
O Boss redefine ainda describe_intent() e act() para esconder as ações.
"""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

import config
from characters import Character


@dataclass
class Intent:
    """O que o inimigo vai fazer no seu turno."""
    kind: str    # "attack", "defend", "weaken" ou "heal"
    value: int   # dano, bloqueio, turnos ou cura (conforme o tipo)

    def describe(self):
        if self.kind == "attack":
            return f"vai ATACAR ({self.value} de dano)"
        if self.kind == "defend":
            return f"vai DEFENDER (+{self.value} de bloqueio)"
        if self.kind == "weaken":
            return f"vai ENFRAQUECER-te ({self.value} turnos)"
        return f"vai CURAR-SE ({self.value} de vida)"

    def short(self):
        """Versão curta, usada no histórico do boss."""
        nomes = {"attack": "Ataque", "defend": "Defesa",
                 "weaken": "Enfraquecer", "heal": "Cura"}
        return f"{nomes[self.kind]} {self.value}"


class Enemy(Character, ABC):
    """Base dos inimigos. A dificuldade cresce com o número da sala."""

    BASE_HP = 20
    HP_PER_ROOM = 3
    BASE_DAMAGE = 3
    DAMAGE_PER_ROOM = 0.3
    NAME = "Inimigo"

    def __init__(self, room):
        hp = self.BASE_HP + self.HP_PER_ROOM * (room - 1)
        super().__init__(self.NAME, hp)
        self._room = room
        self._intent = None

    @property
    def room(self):
        return self._room

    @property
    def damage(self):
        """Dano base desta sala (cresce de sala para sala)."""
        return int(self.BASE_DAMAGE + self.DAMAGE_PER_ROOM * self._room)

    @abstractmethod
    def choose_action(self, turn):
        """Cada tipo de inimigo decide a sua ação à sua maneira."""

    def _attack(self, multiplier=1.0):
        """Cria uma intenção de ataque (já com a fraqueza aplicada)."""
        return Intent("attack", self.outgoing_damage(int(self.damage * multiplier)))

    def plan(self, turn):
        """No início do turno do jogador, o inimigo decide o que vai fazer."""
        self._intent = self.choose_action(turn)

    def describe_intent(self):
        """O que se mostra ao jogador. (O Boss redefine isto.)"""
        return f"{self.name} {self._intent.describe()}"

    def act(self, player):
        """Executa a intenção e devolve as mensagens do que aconteceu."""
        intent = self._intent
        if intent.kind == "attack":
            resultado = player.receive_attack(intent.value, self)
            return [f"{self.name} ataca! {resultado}"]
        if intent.kind == "defend":
            self.gain_block(intent.value)
            return [f"{self.name} ganha {intent.value} de bloqueio."]
        if intent.kind == "weaken":
            player.apply_status("weak", intent.value)
            return [f"{self.name} enfraquece-te: causas -25% de dano "
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
        return Intent("heal", 3 + self._room // 2)


class Boss(Enemy):
    """
    O boss final. As ações estão ESCONDIDAS, mas seguem um padrão que se
    aprende: ataque, enfraquecer, ataque FORTE, e repete (de 3 em 3 turnos).
    Para ajudar, mostramos o histórico do que já fez.
    """
    NAME = "O Rootkit"
    BASE_HP = 60
    HP_PER_ROOM = 0       # a vida do boss é fixa
    BASE_DAMAGE = 6

    def __init__(self, room):
        super().__init__(room)
        self._history = []

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


def spawn_enemy(room):
    """Escolhe o inimigo da sala: normais nas salas 1-9, boss na última."""
    if room >= config.TOTAL_ROOMS:
        return Boss(room)
    tipos = [Bug, Virus] if room <= 3 else [Bug, Virus, MemoryLeak]
    return random.choice(tipos)(room)
