"""
relics.py - Relíquias: objetos que ALTERAM AS REGRAS durante a run (ideia do Balatro).

R2: Relic é a classe base com "ganchos" (hooks) vazios. Cada subclasse redefine
só os ganchos de que precisa. O Player chama os ganchos de todas as relíquias
sem saber quais são (polimorfismo).
"""
import random


class Relic:
    """Base: todos os ganchos não fazem nada por omissão."""

    def __init__(self, name, description):
        self._name = name
        self._description = description

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    # --- ganchos que as subclasses podem redefinir ---
    def on_combat_start(self, player):
        """Chamado no início de cada combate (depois de comprar a mão)."""

    def on_turn_start(self, player):
        """Chamado no início de cada turno do jogador."""

    def on_card_played(self, player, card):
        """Chamado depois de o jogador jogar uma carta."""

    def attack_bonus(self):
        """Dano extra em cada golpe do jogador."""
        return 0

    def heal_after_combat(self):
        """Vida extra recuperada no fim de cada combate."""
        return 0

    def __str__(self):
        return f"{self._name} - {self._description}"


class Overclock(Relic):
    def __init__(self):
        super().__init__("Overclock", "+1 energia no início de cada turno")

    def on_turn_start(self, player):
        player.gain_energy(1)


class Antivirus(Relic):
    def __init__(self):
        super().__init__("Antivirus", "+3 de bloqueio no início de cada turno")

    def on_turn_start(self, player):
        player.gain_block(3)


class CacheL1(Relic):
    def __init__(self):
        super().__init__("Cache L1", "Começas cada combate com +1 carta na mão")

    def on_combat_start(self, player):
        player.deck.draw(1)


class StackTrace(Relic):
    def __init__(self):
        super().__init__("Stack Trace", "Todos os teus golpes causam +1 de dano")

    def attack_bonus(self):
        return 1


class Backup(Relic):
    def __init__(self):
        super().__init__("Backup", "Recuperas +4 de vida no fim de cada combate")

    def heal_after_combat(self):
        return 4


class Macro(Relic):
    """Tem estado próprio: conta as cartas jogadas no combate."""

    def __init__(self):
        super().__init__("Macro", "A cada 5 cartas jogadas no combate, ganhas +1 energia")
        self._played = 0

    def on_combat_start(self, player):
        self._played = 0

    def on_card_played(self, player, card):
        self._played += 1
        if self._played % 5 == 0:
            player.gain_energy(1)


RELIC_FACTORIES = {
    "Overclock": Overclock, "Antivirus": Antivirus, "Cache L1": CacheL1,
    "Stack Trace": StackTrace, "Backup": Backup, "Macro": Macro,
}


def make_relic(name):
    if name not in RELIC_FACTORIES:
        raise KeyError(f"Relíquia inexistente: {name}")
    return RELIC_FACTORIES[name]()


def random_relics(owned_names, amount=2):
    """Relíquias que ainda não tens, para escolheres uma."""
    livres = [n for n in RELIC_FACTORIES if n not in owned_names]
    return [make_relic(n) for n in random.sample(livres, min(amount, len(livres)))]
