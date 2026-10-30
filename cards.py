"""
cards.py - Cartas do jogo.

R2 (herança e polimorfismo): Card é uma classe ABSTRATA com o método play().
Cada subclasse (AttackCard, DefenseCard, ...) redefine play() à sua maneira.
O combate chama sempre card.play(...) sem saber de que tipo é a carta.
"""
import random
from abc import ABC, abstractmethod


class Card(ABC):
    """Classe base de todas as cartas."""

    def __init__(self, name, cost, description):
        self._name = name
        self._cost = cost
        self._description = description

    @property
    def name(self):
        return self._name

    @property
    def cost(self):
        return self._cost

    @property
    def description(self):
        return self._description

    @abstractmethod
    def play(self, player, enemy):
        """Executa o efeito da carta e devolve um texto a explicar o que aconteceu."""

    def __str__(self):
        return f"{self._name} [custo {self._cost}] - {self._description}"


class AttackCard(Card):
    """Causa dano ao inimigo (pode bater várias vezes)."""

    def __init__(self, name, cost, damage, hits=1):
        desc = f"Causa {damage} de dano" + (f", {hits} vezes" if hits > 1 else "")
        super().__init__(name, cost, desc)
        self._damage = damage
        self._hits = hits

    def play(self, player, enemy):
        bonus = player.consume_attack_bonus()   # Debug Mode só vale 1 ataque
        linhas = []
        for i in range(self._hits):
            if not enemy.is_alive:
                break
            base = self._damage + (bonus if i == 0 else 0)
            dano = player.outgoing_damage(base)  # fraqueza reduz o dano
            linhas.append(str(enemy.receive_attack(dano, player)))
        extra = f" (+{bonus} do Debug Mode)" if bonus else ""
        return " | ".join(linhas) + extra


class DefenseCard(Card):
    """Dá bloqueio ao jogador."""

    def __init__(self, name, cost, block):
        super().__init__(name, cost, f"Ganha {block} de bloqueio")
        self._block = block

    def play(self, player, enemy):
        player.gain_block(self._block)
        return f"Ganhas {self._block} de bloqueio (total: {player.block})."


class HealCard(Card):
    """Recupera vida."""

    def __init__(self, name, cost, amount):
        super().__init__(name, cost, f"Recupera {amount} de vida")
        self._amount = amount

    def play(self, player, enemy):
        curado = player.heal(self._amount)
        return f"Recuperas {curado} de vida."


class BuffCard(Card):
    """O próximo ataque causa dano extra."""

    def __init__(self, name, cost, bonus):
        super().__init__(name, cost, f"O próximo ataque causa +{bonus} de dano")
        self._bonus = bonus

    def play(self, player, enemy):
        player.add_attack_bonus(self._bonus)
        return f"O teu próximo ataque causa +{self._bonus} de dano."


class DebuffCard(Card):
    """Aplica um estado negativo (vulnerável / fraqueza) ao inimigo."""

    NOMES = {"vulnerable": "Vulnerável", "weak": "Fraco"}

    def __init__(self, name, cost, status, turns):
        nome = self.NOMES[status]
        super().__init__(name, cost, f"O inimigo fica {nome} durante {turns} turnos")
        self._status = status
        self._turns = turns

    def play(self, player, enemy):
        enemy.apply_status(self._status, self._turns)
        return f"{enemy.name} fica {self.NOMES[self._status]} durante {self._turns} turnos."


class ParryCard(Card):
    """Se o inimigo atacar neste turno, anula o dano e devolve uma parte."""

    def __init__(self, name, cost, reflect):
        super().__init__(name, cost,
                         f"Se o inimigo atacar neste turno, anula o dano e devolve {reflect}")
        self._reflect = reflect

    def play(self, player, enemy):
        player.set_parry(self._reflect)
        return "Preparas o parry... se o inimigo atacar, devolves o golpe!"


class DrawCard(Card):
    """Compra cartas extra do baralho (a 'compra extra' do relatório)."""

    def __init__(self, name, cost, amount):
        super().__init__(name, cost, f"Compras {amount} cartas do teu baralho")
        self._amount = amount

    def play(self, player, enemy):
        compradas = player.deck.draw(self._amount)
        if not compradas:
            return "O baralho está vazio, não compraste nada."
        return "Compraste: " + ", ".join(c.name for c in compradas) + "."


# ---------------------------------------------------------------------------
# "Fábrica" de cartas: um dicionário nome -> função que cria a carta.
# Assim criamos sempre objetos NOVOS e o resto do jogo só precisa do nome.
# As 10 primeiras são as do relatório (secção 5); as duas últimas são extras.
# ---------------------------------------------------------------------------
CARD_FACTORIES = {
    'Print("Hit")':      lambda: AttackCard('Print("Hit")', 1, 5),
    "Segfault":          lambda: AttackCard("Segfault", 3, 12),
    "Fork Bomb":         lambda: AttackCard("Fork Bomb", 4, 6, hits=2),
    "If/Else":           lambda: DefenseCard("If/Else", 1, 5),
    "Try/Catch":         lambda: DefenseCard("Try/Catch", 2, 10),
    "Firewall":          lambda: DefenseCard("Firewall", 4, 18),
    "Ctrl+Z":            lambda: HealCard("Ctrl+Z", 2, 8),
    "Debug Mode":        lambda: BuffCard("Debug Mode", 2, 5),
    "Stack Overflow":    lambda: DebuffCard("Stack Overflow", 2, "vulnerable", 2),
    "Catch & Return":    lambda: ParryCard("Catch & Return", 3, 8),
    # extras nossos (finalizadora de custo 6 e a "compra extra"):
    "Kernel Panic":      lambda: AttackCard("Kernel Panic", 6, 28),
    "Garbage Collector": lambda: DrawCard("Garbage Collector", 1, 2),
}

BASIC_ATTACK = 'Print("Hit")'
BASIC_DEFENSE = "If/Else"
# Cartas especiais que podem sair na compra aleatória (secção 4.3):
SPECIALS = ["Ctrl+Z", "Debug Mode", "Stack Overflow", "Catch & Return",
            "Garbage Collector"]
# Cartas que podem aparecer como recompensa (tudo menos as básicas):
REWARD_POOL = [n for n in CARD_FACTORIES if n not in (BASIC_ATTACK, BASIC_DEFENSE)]


def make_card(name):
    """Cria uma carta nova a partir do nome. Erro claro se o nome não existir."""
    if name not in CARD_FACTORIES:
        raise KeyError(f"Carta inexistente: {name}")
    return CARD_FACTORIES[name]()


def random_special():
    """Carta especial aleatória (a 'aposta' da compra à Inscryption)."""
    return make_card(random.choice(SPECIALS))
