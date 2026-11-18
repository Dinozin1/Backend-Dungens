"""
cards.py - Cartas do jogo.

R2 (herança e polimorfismo): Card é uma classe ABSTRATA com o método play().
Cada subclasse redefine play() à sua maneira, e algumas herdam de outras
subclasses (PiercingAttackCard e RecoilAttackCard herdam de AttackCard).
O combate chama sempre card.play(...) sem saber de que tipo é a carta.

Cada carta tem uma versão melhorada ("Segfault+") que se obtém no REFACTOR.
"""
from abc import ABC, abstractmethod

import config

# Texto devolvido pelo menu de recompensas quando o jogador escolhe melhorar uma carta.
REFACTOR_OPTION = "refactor"


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

    def __init__(self, name, cost, damage, hits=1, extra_desc=""):
        desc = f"Causa {damage} de dano" + (f", {hits} vezes" if hits > 1 else "") + extra_desc
        super().__init__(name, cost, desc)
        self._damage = damage
        self._hits = hits

    @property
    def total_damage(self):
        """Dano total da carta (todos os golpes), útil para os bots."""
        return self._damage * self._hits

    def _strike(self, player, enemy, damage):
        """Como cada golpe chega ao inimigo. As subclasses podem mudar isto."""
        return enemy.receive_attack(damage, player)

    def play(self, player, enemy):
        bonus = player.consume_attack_bonus()   # Debug Mode só vale 1 ataque
        linhas = []
        for i in range(self._hits):
            if not enemy.is_alive:
                break
            base = self._damage + (bonus if i == 0 else 0)
            dano = player.outgoing_damage(base)  # fraqueza e relíquias contam
            linhas.append(str(self._strike(player, enemy, dano)))
        extra = f" (+{bonus} do Debug Mode)" if bonus else ""
        return " | ".join(linhas) + extra


class PiercingAttackCard(AttackCard):
    """Ataque que ignora o bloqueio do inimigo (o dano vai direto à vida)."""

    def __init__(self, name, cost, damage):
        super().__init__(name, cost, damage, extra_desc=" (ignora o bloqueio)")

    def _strike(self, player, enemy, damage):
        return enemy.take_damage(damage, ignore_block=True)


class RecoilAttackCard(AttackCard):
    """Ataque forte e barato, mas com RISCO: também te custa vida."""

    def __init__(self, name, cost, damage, recoil):
        super().__init__(name, cost, damage, extra_desc=f", mas perdes {recoil} de vida")
        self._recoil = recoil

    def play(self, player, enemy):
        texto = super().play(player, enemy)
        perdido = player.lose_hp(self._recoil)
        return f"{texto} | Perdes {perdido} de vida (recuo)."


class DefenseCard(Card):
    """Dá bloqueio ao jogador."""

    def __init__(self, name, cost, block):
        super().__init__(name, cost, f"Ganha {block} de bloqueio")
        self._block = block

    @property
    def block_amount(self):
        return self._block

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
    """Aplica um estado negativo (vulnerável / fraqueza / veneno) ao inimigo."""

    NOMES = {"vulnerable": "Vulnerável", "weak": "Fraco", "poison": "Envenenado"}

    def __init__(self, name, cost, status, turns):
        extra = (f" ({config.POISON_DAMAGE} de dano por turno, ignora o bloqueio)"
                 if status == "poison" else "")
        super().__init__(name, cost,
                         f"O inimigo fica {self.NOMES[status]} durante {turns} turnos{extra}")
        self._status = status
        self._turns = turns

    @property
    def status(self):
        return self._status

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


class EnergyCard(Card):
    """Energia barata, mas com RISCO: ficas com um estado negativo."""

    def __init__(self, name, cost, energy, self_status, turns):
        super().__init__(name, cost,
                         f"Ganhas {energy} de energia, mas ficas "
                         f"{DebuffCard.NOMES[self_status]} durante {turns} turnos")
        self._energy = energy
        self._status = self_status
        self._turns = turns

    def play(self, player, enemy):
        player.gain_energy(self._energy)
        player.apply_status(self._status, self._turns)
        return (f"Ganhas {self._energy} de energia, mas ficas "
                f"{DebuffCard.NOMES[self._status]} durante {self._turns} turnos!")


# ---------------------------------------------------------------------------
# Catálogo: nome -> (carta normal, carta melhorada). A melhorada chama-se
# "<nome>+" e obtém-se no REFACTOR (só se melhora uma vez).
# ---------------------------------------------------------------------------
_CARDS = {
    # --- ataques ---
    'Print("Hit")': (lambda: AttackCard('Print("Hit")', 1, 5),
                     lambda: AttackCard('Print("Hit")+', 1, 8)),
    "Segfault": (lambda: AttackCard("Segfault", 3, 12),
                 lambda: AttackCard("Segfault+", 3, 16)),
    "Fork Bomb": (lambda: AttackCard("Fork Bomb", 4, 6, hits=2),
                  lambda: AttackCard("Fork Bomb+", 4, 8, hits=2)),
    "Kernel Panic": (lambda: AttackCard("Kernel Panic", 6, 28),
                     lambda: AttackCard("Kernel Panic+", 6, 36)),
    "Buffer Overflow": (lambda: PiercingAttackCard("Buffer Overflow", 3, 10),
                        lambda: PiercingAttackCard("Buffer Overflow+", 3, 14)),
    "Infinite Loop": (lambda: RecoilAttackCard("Infinite Loop", 2, 12, 4),
                      lambda: RecoilAttackCard("Infinite Loop+", 2, 16, 3)),
    # --- defesa, cura e parry ---
    "If/Else": (lambda: DefenseCard("If/Else", 1, 5),
                lambda: DefenseCard("If/Else+", 1, 8)),
    "Try/Catch": (lambda: DefenseCard("Try/Catch", 2, 10),
                  lambda: DefenseCard("Try/Catch+", 2, 14)),
    "Firewall": (lambda: DefenseCard("Firewall", 4, 18),
                 lambda: DefenseCard("Firewall+", 4, 24)),
    "Ctrl+Z": (lambda: HealCard("Ctrl+Z", 2, 8),
               lambda: HealCard("Ctrl+Z+", 2, 12)),
    "Catch & Return": (lambda: ParryCard("Catch & Return", 3, 8),
                       lambda: ParryCard("Catch & Return+", 3, 14)),
    # --- buffs, debuffs e utilidade ---
    "Debug Mode": (lambda: BuffCard("Debug Mode", 2, 5),
                   lambda: BuffCard("Debug Mode+", 2, 8)),
    "Stack Overflow": (lambda: DebuffCard("Stack Overflow", 2, "vulnerable", 2),
                       lambda: DebuffCard("Stack Overflow+", 2, "vulnerable", 3)),
    "Rate Limiter": (lambda: DebuffCard("Rate Limiter", 2, "weak", 2),
                     lambda: DebuffCard("Rate Limiter+", 2, "weak", 3)),
    "Zombie Process": (lambda: DebuffCard("Zombie Process", 2, "poison", 4),
                       lambda: DebuffCard("Zombie Process+", 2, "poison", 6)),
    "Garbage Collector": (lambda: DrawCard("Garbage Collector", 1, 2),
                          lambda: DrawCard("Garbage Collector+", 1, 3)),
    # --- risco / recompensa ---
    "Sudo": (lambda: EnergyCard("Sudo", 1, 3, "vulnerable", 2),
             lambda: EnergyCard("Sudo+", 1, 4, "vulnerable", 1)),
}

CARD_FACTORIES = {}   # nome -> função que cria a carta (inclui as melhoradas)
UPGRADES = {}         # nome -> nome da versão melhorada
for _nome, (_normal, _melhorada) in _CARDS.items():
    CARD_FACTORIES[_nome] = _normal
    _plus = _melhorada().name
    assert _plus == _nome + "+", _nome
    CARD_FACTORIES[_plus] = _melhorada
    UPGRADES[_nome] = _plus

BASIC_ATTACK = 'Print("Hit")'
BASIC_DEFENSE = "If/Else"
# Cartas que podem aparecer como recompensa: as normais, menos as básicas.
REWARD_POOL = [n for n in _CARDS if n not in (BASIC_ATTACK, BASIC_DEFENSE)]


def make_card(name):
    """Cria uma carta nova a partir do nome. Erro claro se o nome não existir."""
    if name not in CARD_FACTORIES:
        raise KeyError(f"Carta inexistente: {name}")
    return CARD_FACTORIES[name]()
