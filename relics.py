"""
relics.py - Relíquias: objetos que ALTERAM AS REGRAS durante a run (ideia do Balatro).

R2: Relic é a classe base com "ganchos" (hooks) vazios. Cada subclasse define
NAME e DESCRIPTION e redefine só os ganchos de que precisa. O Player chama os
ganchos de todas as relíquias sem saber quais são (polimorfismo).

Para criar uma relíquia nova basta escrever a classe: o catálogo
(RELIC_FACTORIES) é construído sozinho a partir das subclasses de Relic.
"""
from cards import DefenseCard
from rng import rng


class Relic:
    """Base: todos os ganchos não fazem nada por omissão."""

    NAME = "Relíquia"
    DESCRIPTION = ""
    PREVENTS_HEALING = False    # True: o jogador deixa de recuperar vida após os combates

    @property
    def name(self):
        return self.NAME

    @property
    def description(self):
        return self.DESCRIPTION

    # --- ganchos que as subclasses podem redefinir ---
    def on_combat_start(self, player):
        """Chamado no início de cada combate (depois de comprar a mão)."""

    def on_turn_start(self, player):
        """Chamado no início de cada turno do jogador."""

    def on_card_played(self, player, card):
        """Chamado depois de o jogador jogar uma carta."""

    def on_damage_taken(self, player, attacker, result):
        """Chamado depois de o jogador levar um ataque (que não foi anulado por parry)."""

    def attack_bonus(self):
        """Dano extra em cada golpe do jogador."""
        return 0

    def heal_after_combat(self):
        """Vida extra recuperada no fim de cada combate."""
        return 0

    def __str__(self):
        return f"{self.NAME} - {self.DESCRIPTION}"


class Overclock(Relic):
    NAME = "Overclock"
    DESCRIPTION = "+1 energia no início de cada turno"

    def on_turn_start(self, player):
        player.gain_energy(1)


class Antivirus(Relic):
    NAME = "Antivirus"
    DESCRIPTION = "+3 de bloqueio no início de cada turno"

    def on_turn_start(self, player):
        player.gain_block(3)


class CacheL1(Relic):
    NAME = "Cache L1"
    DESCRIPTION = "Começas cada combate com +1 carta na mão"

    def on_combat_start(self, player):
        player.deck.draw(1)


class StackTrace(Relic):
    NAME = "Stack Trace"
    DESCRIPTION = "Todos os teus golpes causam +1 de dano"

    def attack_bonus(self):
        return 1


class Backup(Relic):
    NAME = "Backup"
    DESCRIPTION = "Recuperas +4 de vida no fim de cada combate"

    def heal_after_combat(self):
        return 4


class Macro(Relic):
    """Tem estado próprio: conta as cartas jogadas no combate."""
    NAME = "Macro"
    DESCRIPTION = "A cada 5 cartas jogadas no combate, ganhas +3 energia"

    def __init__(self):
        self._played = 0

    def on_combat_start(self, player):
        self._played = 0

    def on_card_played(self, player, card):
        self._played += 1
        if self._played % 5 == 0:
            player.gain_energy(3)


class Linter(Relic):
    """Reage ao TIPO da carta jogada (só as de defesa contam)."""
    NAME = "Linter"
    DESCRIPTION = "Cada carta de defesa jogada dá +2 de bloqueio extra"

    def on_card_played(self, player, card):
        if isinstance(card, DefenseCard):
            player.gain_block(2)


class AutoSave(Relic):
    NAME = "Auto-Save"
    DESCRIPTION = "Recuperas 2 de vida no início de cada turno"

    def on_turn_start(self, player):
        player.heal(2)


class Defrag(Relic):
    NAME = "Defrag"
    DESCRIPTION = "No início do turno, se tens 2 cartas ou menos na mão, compras 2"

    def on_turn_start(self, player):
        if len(player.deck.hand) <= 2:
            player.deck.draw(2)


class Watchdog(Relic):
    NAME = "Watchdog"
    DESCRIPTION = "No início do turno, se tens menos de metade da vida, recuperas 3"

    def on_turn_start(self, player):
        if player.hp * 2 < player.max_hp:
            player.heal(3)


class Honeypot(Relic):
    NAME = "Honeypot"
    DESCRIPTION = "Cada ataque que levas custa 2 de vida (direta) a quem te atacou"

    def on_damage_taken(self, player, attacker, result):
        attacker.take_damage(2, ignore_block=True)


class StackCanary(Relic):
    """Tem estado próprio: só salva uma vez por combate."""
    NAME = "Stack Canary"
    DESCRIPTION = "Uma vez por combate, se fosses morrer ficas com 1 de vida"

    def __init__(self):
        self._used = False

    def on_combat_start(self, player):
        self._used = False

    def on_damage_taken(self, player, attacker, result):
        if not player.is_alive and not self._used:
            self._used = True
            player.restore_hp(1)


# --- Relíquias de RISCO (poder grande, com preço) ---
class Overvolt(Relic):
    NAME = "Overvolt"
    DESCRIPTION = "RISCO: +2 energia por turno, mas começas cada combate com -5 de vida"

    def on_combat_start(self, player):
        player.lose_hp(5)

    def on_turn_start(self, player):
        player.gain_energy(2)


class SafeMode(Relic):
    NAME = "Modo Seguro"
    DESCRIPTION = "RISCO: +6 de bloqueio no início de cada turno, mas -1 energia por turno"

    def on_turn_start(self, player):
        player.gain_block(6)
        player.spend_energy(min(1, player.energy))


class LegacyCode(Relic):
    NAME = "Código Legado"
    DESCRIPTION = ("RISCO: +3 de dano em todos os golpes, "
                   "mas deixas de recuperar vida após os combates")
    PREVENTS_HEALING = True

    def attack_bonus(self):
        return 3


# Catálogo automático: nome -> classe (pela ordem em que as classes foram definidas).
RELIC_FACTORIES = {cls.NAME: cls for cls in Relic.__subclasses__()}


def make_relic(name):
    if name not in RELIC_FACTORIES:
        raise KeyError(f"Relíquia inexistente: {name}")
    return RELIC_FACTORIES[name]()


def random_relics(owned_names, amount=2):
    """Relíquias que ainda não tens, para escolheres uma."""
    livres = [n for n in RELIC_FACTORIES if n not in owned_names]
    return [make_relic(n) for n in rng.sample(livres, min(amount, len(livres)))]
