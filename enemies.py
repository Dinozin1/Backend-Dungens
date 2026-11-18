"""
enemies.py - Inimigos e as suas "intenções".

R2: Enemy é uma classe abstrata com choose_action(turn). Cada subclasse
(Bug, Virus, RaceCondition, MemoryLeak, Trojan, Boss) redefine-o com o seu
próprio padrão. O Boss redefine ainda describe_intent(), act() e _start_hp().
Intent também é uma classe abstrata: AttackIntent, DefendIntent, WeakenIntent,
ExposeIntent e HealIntent redefinem describe() e execute().
"""
import random
from abc import ABC, abstractmethod

import config
from characters import Character
from modes import DEFAULT_MODE, get_mode


class Intent(ABC):
    """
    O que o inimigo vai fazer no seu turno (R2: cada tipo de intenção sabe
    descrever-se e executar-se; o Enemy só chama describe() e execute()).
    """
    kind = ""        # "attack", "defend", "weaken", "expose" ou "heal"
    SHORT = ""       # nome curto, usado no histórico do boss

    def __init__(self, value, hits=1):
        self._value = value      # dano, bloqueio, turnos ou cura (conforme o tipo)
        self._hits = hits        # nº de golpes (só para ataques)

    @property
    def value(self):
        return self._value

    @property
    def hits(self):
        return self._hits

    @abstractmethod
    def describe(self):
        """Texto mostrado ao jogador (ex.: 'vai ATACAR (6 de dano)')."""

    @abstractmethod
    def execute(self, enemy, player):
        """Executa a intenção e devolve a lista de mensagens do que aconteceu."""

    def short(self):
        """Versão curta, usada no histórico do boss."""
        extra = f"x{self._hits}" if self._hits > 1 else ""
        return f"{self.SHORT} {self._value}{extra}"


class AttackIntent(Intent):
    kind, SHORT = "attack", "Ataque"

    def describe(self):
        dano = f"{self._value} de dano" + (f" x{self._hits}" if self._hits > 1 else "")
        return f"vai ATACAR ({dano})"

    def execute(self, enemy, player):
        mensagens = []
        for _ in range(self._hits):
            resultado = player.receive_attack(self._value, enemy)
            mensagens.append(f"{enemy.name} ataca! {resultado}")
            # parou o ataque quem morreu: o jogador, ou o inimigo (ex.: parry)
            if not player.is_alive or not enemy.is_alive:
                break
        return mensagens


class DefendIntent(Intent):
    kind, SHORT = "defend", "Defesa"

    def describe(self):
        return f"vai DEFENDER (+{self._value} de bloqueio)"

    def execute(self, enemy, player):
        enemy.gain_block(self._value)
        return [f"{enemy.name} ganha {self._value} de bloqueio."]


class WeakenIntent(Intent):
    kind, SHORT = "weaken", "Enfraquecer"

    def describe(self):
        return f"vai ENFRAQUECER-te ({self._value} turnos)"

    def execute(self, enemy, player):
        player.apply_status("weak", self._value)
        return [f"{enemy.name} enfraquece-te: causas -25% de dano "
                f"durante {self._value} turnos."]


class ExposeIntent(Intent):
    kind, SHORT = "expose", "Expor"

    def describe(self):
        return f"vai EXPOR-te: ficas Vulnerável {self._value} turnos"

    def execute(self, enemy, player):
        player.apply_status("vulnerable", self._value)
        return [f"{enemy.name} expõe-te: recebes +50% de dano "
                f"durante {self._value} turnos."]


class HealIntent(Intent):
    kind, SHORT = "heal", "Cura"

    def describe(self):
        return f"vai CURAR-SE ({self._value} de vida)"

    def execute(self, enemy, player):
        curado = enemy.heal(self._value)
        return [f"{enemy.name} cura-se {curado} de vida."]


class Enemy(Character, ABC):
    """Base dos inimigos. A dificuldade cresce com o PROGRESSO na run."""

    BASE_HP = 20
    HP_PER_ROOM = 4
    BASE_DAMAGE = 4
    DAMAGE_PER_ROOM = 0.5
    NAME = "Inimigo"
    MIN_LEVEL = 0      # dificuldade (sala equivalente) a partir da qual pode aparecer
    SPAWNS = True      # False: nunca é sorteado como inimigo normal (ex.: Boss)

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
        return AttackIntent(self.outgoing_damage(int(self.damage * multiplier)), hits)

    def plan(self, turn):
        """No início do turno do jogador, o inimigo decide o que vai fazer."""
        self._turn = turn
        self._intent = self.choose_action(turn)

    def describe_intent(self):
        """O que se mostra ao jogador. (O Boss redefine isto.)"""
        return f"{self.name} {self._intent.describe()}"

    def act(self, player):
        """Executa a intenção (polimorfismo: cada Intent sabe o que fazer)."""
        return self._intent.execute(self, player)


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
        return WeakenIntent(2)


class RaceCondition(Enemy):
    """Dois golpes seguidos (o parry só anula um!); de 3 em 3 turnos defende."""
    NAME = "Race Condition"
    BASE_HP = 18
    MIN_LEVEL = 2.5

    def choose_action(self, turn):
        if turn % 3 == 0:
            return DefendIntent(self.damage + 2)
        return self._attack(0.8, hits=2)


class MemoryLeak(Enemy):
    """Ciclo de 3 turnos: defende, ataca com força, cura-se."""
    NAME = "Memory Leak"
    BASE_HP = 24
    MIN_LEVEL = 4

    def choose_action(self, turn):
        fase = turn % 3
        if fase == 1:
            return DefendIntent(self.damage + 3)
        if fase == 2:
            return self._attack(1.6)
        return HealIntent(3 + int(self._level) // 2)


class Trojan(Enemy):
    """Primeiro expõe-te (Vulnerável) e depois bate forte, aproveitando isso."""
    NAME = "Trojan"
    BASE_HP = 22
    MIN_LEVEL = 4

    def choose_action(self, turn):
        if turn % 2 == 1:
            return ExposeIntent(2)
        return self._attack(1.4)


class Boss(Enemy):
    """
    O boss final. As ações estão ESCONDIDAS, mas seguem um padrão que se
    aprende: ataque, enfraquecer, ataque FORTE, e repete (de 3 em 3 turnos).
    Para ajudar, mostramos o histórico do que já fez.
    """
    NAME = "O Rootkit"
    BASE_DAMAGE = 7
    SPAWNS = False

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
            return WeakenIntent(2)
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
    """
    Escolhe o inimigo da sala: o Boss na última, e antes disso um inimigo normal
    sorteado entre as subclasses de Enemy cujo MIN_LEVEL já foi atingido.
    (Para criar um inimigo novo basta escrever a classe.)
    """
    mode = mode or get_mode(DEFAULT_MODE)
    if room >= mode.rooms:
        return Boss(room, mode)
    nivel = mode.difficulty_room(room)
    tipos = [t for t in Enemy.__subclasses__() if t.SPAWNS and nivel >= t.MIN_LEVEL]
    return random.choice(tipos)(room, mode)
