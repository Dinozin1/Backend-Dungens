"""
relics.py - Relíquias: objetos que ALTERAM AS REGRAS durante a run (ideia do Balatro).

R2: Relic é a classe base com "ganchos" (hooks) vazios. Cada subclasse redefine
só os ganchos de que precisa. O Player chama os ganchos de todas as relíquias
sem saber quais são (polimorfismo).
"""
import random

from cards import DefenseCard


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
        """Vida extra recuperada no fim de cada combate (pode ser negativa)."""
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
        super().__init__("Macro", "A cada 5 cartas jogadas no combate, ganhas +3 energia")
        self._played = 0

    def on_combat_start(self, player):
        self._played = 0

    def on_card_played(self, player, card):
        self._played += 1
        if self._played % 5 == 0:
            player.gain_energy(3)


class Linter(Relic):
    """Reage ao TIPO da carta jogada (só as de defesa contam)."""

    def __init__(self):
        super().__init__("Linter", "Cada carta de defesa jogada dá +2 de bloqueio extra")

    def on_card_played(self, player, card):
        if isinstance(card, DefenseCard):
            player.gain_block(2)


class AutoSave(Relic):
    def __init__(self):
        super().__init__("Auto-Save", "Recuperas 2 de vida no início de cada turno")

    def on_turn_start(self, player):
        player.heal(2)


# --- Relíquias de RISCO (poder grande, com preço) ---
class Overvolt(Relic):
    def __init__(self):
        super().__init__("Overvolt",
                         "RISCO: +2 energia por turno, mas começas cada combate com -5 de vida")

    def on_combat_start(self, player):
        player.lose_hp(5)

    def on_turn_start(self, player):
        player.gain_energy(2)


class LegacyCode(Relic):
    def __init__(self):
        super().__init__("Código Legado",
                         "RISCO: +3 de dano em todos os golpes, mas deixas de recuperar vida após os combates")

    def attack_bonus(self):
        return 3

    def heal_after_combat(self):
        return -999            # anula toda a cura de fim de combate


RELIC_FACTORIES = {
    "Overclock": Overclock, "Antivirus": Antivirus, "Cache L1": CacheL1,
    "Stack Trace": StackTrace, "Backup": Backup, "Macro": Macro,
    "Linter": Linter, "Auto-Save": AutoSave,
    "Overvolt": Overvolt, "Código Legado": LegacyCode,
}


def make_relic(name):
    if name not in RELIC_FACTORIES:
        raise KeyError(f"Relíquia inexistente: {name}")
    return RELIC_FACTORIES[name]()


def random_relics(owned_names, amount=2):
    """Relíquias que ainda não tens, para escolheres uma."""
    livres = [n for n in RELIC_FACTORIES if n not in owned_names]
    return [make_relic(n) for n in random.sample(livres, min(amount, len(livres)))]
