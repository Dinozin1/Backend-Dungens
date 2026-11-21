"""
cards.py - Cartas do jogo.

R2 (herança e polimorfismo): Card é uma classe ABSTRATA com o método play().
Cada subclasse redefine play() à sua maneira, e algumas herdam de outras
subclasses (PiercingAttackCard e RecoilAttackCard herdam de AttackCard).
O combate chama sempre card.play(...) sem saber de que tipo é a carta.

Cada carta tem uma versão melhorada ("Segfault+") que se obtém no REFACTOR e pode
receber UMA mutação (mutations.py). O Card.play() é um "template method": paga o efeito
da subclasse (_effect) e aplica os ganchos da mutação, se a carta tiver uma.
"""
from abc import ABC, abstractmethod
from functools import partial

import config
from characters import STATUS_NAMES
from mutations import MUTATION_FACTORIES, make_mutation

# Textos devolvidos pelo menu de recompensas quando o jogador escolhe melhorar ou mutar uma carta.
REFACTOR_OPTION = "refactor"
MUTATE_OPTION = "mutate"


class Card(ABC):
    """Classe base de todas as cartas."""

    def __init__(self, name, cost, description):
        self._name = name
        self._cost = cost
        self._description = description
        self._mutation = None

    @property
    def name(self):
        """Nome base da carta (é o que identifica a carta no catálogo e nas melhorias)."""
        return self._name

    @property
    def mutation(self):
        return self._mutation

    @property
    def spec(self):
        """Identificador completo (nome + mutação), usado na gravação: 'Segfault|Vampírico'."""
        return self._name + (f"|{self._mutation.name}" if self._mutation else "")

    @property
    def display_name(self):
        """Nome mostrado ao jogador: 'Segfault (Vampírico)'."""
        return self._name + (f" ({self._mutation.name})" if self._mutation else "")

    @property
    def cost(self):
        """Custo atual: o da carta, alterado pela mutação (nunca abaixo de 1)."""
        if self._mutation:
            return max(1, self._mutation.modify_cost(self._cost))
        return self._cost

    @property
    def description(self):
        if self._mutation:
            return f"{self._description} {{{self._mutation}}}"
        return self._description

    @property
    def exhausts(self):
        """True se, depois de jogada, a carta é exilada até ao fim do combate."""
        return bool(self._mutation and self._mutation.EXHAUSTS)

    def mutate(self, mutation):
        """Pendura uma mutação na carta (só uma por carta)."""
        if self._mutation is not None:
            raise ValueError(f"{self._name} já tem uma mutação")
        self._mutation = mutation

    @abstractmethod
    def _effect(self, player, enemy):
        """O efeito próprio de cada tipo de carta. Devolve o texto do que aconteceu."""

    def play(self, player, enemy):
        """Joga a carta: o efeito do tipo + os ganchos da mutação (se tiver)."""
        texto = self._effect(player, enemy)
        if self._mutation is None:
            return texto
        for _ in range(self._mutation.EXTRA_PLAYS):
            if enemy.is_alive:
                texto += " | (de novo) " + self._effect(player, enemy)
        extra = self._mutation.after_play(self, player, enemy)
        return f"{texto} | {extra}" if extra else texto

    def __str__(self):
        return f"{self.display_name} [custo {self.cost}] - {self.description}"


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

    def _effect(self, player, enemy):
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

    def _effect(self, player, enemy):
        texto = super()._effect(player, enemy)
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

    def _effect(self, player, enemy):
        player.gain_block(self._block)
        return f"Ganhas {self._block} de bloqueio (total: {player.block})."


class HealCard(Card):
    """Recupera vida."""

    def __init__(self, name, cost, amount):
        super().__init__(name, cost, f"Recupera {amount} de vida")
        self._amount = amount

    def _effect(self, player, enemy):
        curado = player.heal(self._amount)
        return f"Recuperas {curado} de vida."


class BuffCard(Card):
    """O próximo ataque causa dano extra."""

    def __init__(self, name, cost, bonus):
        super().__init__(name, cost, f"O próximo ataque causa +{bonus} de dano")
        self._bonus = bonus

    def _effect(self, player, enemy):
        player.add_attack_bonus(self._bonus)
        return f"O teu próximo ataque causa +{self._bonus} de dano."


class DebuffCard(Card):
    """Aplica um estado negativo (vulnerável / fraqueza / veneno) ao inimigo."""

    def __init__(self, name, cost, status, turns):
        extra = (f" ({config.POISON_DAMAGE} de dano por turno, ignora o bloqueio)"
                 if status == "poison" else "")
        super().__init__(name, cost,
                         f"O inimigo fica {STATUS_NAMES[status]} durante {turns} turnos{extra}")
        self._status = status
        self._turns = turns

    @property
    def status(self):
        return self._status

    def _effect(self, player, enemy):
        enemy.apply_status(self._status, self._turns)
        return f"{enemy.name} fica {STATUS_NAMES[self._status]} durante {self._turns} turnos."


class ParryCard(Card):
    """Se o inimigo atacar neste turno, anula o dano e devolve uma parte."""

    def __init__(self, name, cost, reflect):
        super().__init__(name, cost,
                         f"Se o inimigo atacar neste turno, anula o dano e devolve {reflect}")
        self._reflect = reflect

    def _effect(self, player, enemy):
        player.set_parry(self._reflect)
        return "Preparas o parry... se o inimigo atacar, devolves o golpe!"


class DrawCard(Card):
    """Compra cartas extra do baralho (a 'compra extra' do relatório)."""

    def __init__(self, name, cost, amount):
        super().__init__(name, cost, f"Compras {amount} cartas do teu baralho")
        self._amount = amount

    def _effect(self, player, enemy):
        compradas = player.deck.draw(self._amount)
        if not compradas:
            return "O baralho está vazio, não compraste nada."
        return "Compraste: " + ", ".join(c.name for c in compradas) + "."


class EnergyCard(Card):
    """Energia barata, mas com RISCO: ficas com um estado negativo."""

    def __init__(self, name, cost, energy, self_status, turns):
        super().__init__(name, cost,
                         f"Ganhas {energy} de energia, mas ficas "
                         f"{STATUS_NAMES[self_status]} durante {turns} turnos")
        self._energy = energy
        self._status = self_status
        self._turns = turns

    def _effect(self, player, enemy):
        player.gain_energy(self._energy)
        player.apply_status(self._status, self._turns)
        return (f"Ganhas {self._energy} de energia, mas ficas "
                f"{STATUS_NAMES[self._status]} durante {self._turns} turnos!")


class JunkCard(Card):
    """Lixo (ex.: o Spam do Adware): ocupa a mão e gasta energia, mas não faz nada."""

    def __init__(self, name, cost):
        super().__init__(name, cost, "Não faz nada (lixo)")

    def _effect(self, player, enemy):
        return "Era só lixo. Nada acontece."


# ---------------------------------------------------------------------------
# Catálogo orientado a dados: nome -> (classe, argumentos normais, argumentos
# melhorados). Os argumentos são os que vêm a seguir ao nome no __init__ da classe.
# A versão melhorada chama-se "<nome>+" e obtém-se no REFACTOR (só uma vez).
# Para criar uma carta nova basta acrescentar uma linha.
# ---------------------------------------------------------------------------
_CARDS = {
    # --- ataques: (custo, dano[, golpes ou recuo]) ---
    'Print("Hit")': (AttackCard, (1, 5), (1, 8)),
    "Segfault": (AttackCard, (3, 12), (3, 16)),
    "Fork Bomb": (AttackCard, (4, 6, 2), (4, 8, 2)),
    "Kernel Panic": (AttackCard, (6, 28), (6, 36)),
    "Buffer Overflow": (PiercingAttackCard, (3, 10), (3, 14)),
    "Infinite Loop": (RecoilAttackCard, (2, 12, 4), (2, 16, 3)),
    # --- defesa, cura e parry: (custo, valor) ---
    "If/Else": (DefenseCard, (1, 5), (1, 8)),
    "Try/Catch": (DefenseCard, (2, 10), (2, 14)),
    "Firewall": (DefenseCard, (4, 18), (4, 24)),
    "Ctrl+Z": (HealCard, (2, 8), (2, 12)),
    "Catch & Return": (ParryCard, (3, 8), (3, 14)),
    # --- buffs, debuffs e utilidade ---
    "Debug Mode": (BuffCard, (2, 5), (2, 8)),
    "Stack Overflow": (DebuffCard, (2, "vulnerable", 2), (2, "vulnerable", 3)),
    "Rate Limiter": (DebuffCard, (2, "weak", 2), (2, "weak", 3)),
    "Zombie Process": (DebuffCard, (2, "poison", 4), (2, "poison", 6)),
    "Garbage Collector": (DrawCard, (1, 2), (1, 3)),
    # --- risco / recompensa ---
    "Sudo": (EnergyCard, (1, 3, "vulnerable", 2), (1, 4, "vulnerable", 1)),
}

CARD_FACTORIES = {}   # nome -> função que cria a carta (inclui as melhoradas)
UPGRADES = {}         # nome -> nome da versão melhorada
for _nome, (_classe, _normal, _melhorada) in _CARDS.items():
    CARD_FACTORIES[_nome] = partial(_classe, _nome, *_normal)
    CARD_FACTORIES[_nome + "+"] = partial(_classe, _nome + "+", *_melhorada)
    UPGRADES[_nome] = _nome + "+"

BASIC_ATTACK = 'Print("Hit")'
BASIC_DEFENSE = "If/Else"
# Cartas que podem aparecer como recompensa: as normais, menos as básicas.
REWARD_POOL = [n for n in _CARDS if n not in (BASIC_ATTACK, BASIC_DEFENSE)]


SPAM = "Spam"
CARD_FACTORIES[SPAM] = partial(JunkCard, SPAM, 1)    # só existe dentro do combate (Adware)
# Cartas que podem estar num baralho/gravação (tudo menos o lixo temporário).
DECK_CARDS = [n for n in CARD_FACTORIES if n != SPAM]


def make_card(spec):
    """
    Cria uma carta nova a partir do nome ('Segfault') ou do identificador com
    mutação ('Segfault|Vampírico'). Erro claro se o nome não existir.
    """
    name, _, mutacao = spec.partition("|")
    if name not in CARD_FACTORIES:
        raise KeyError(f"Carta inexistente: {name}")
    carta = CARD_FACTORIES[name]()
    if mutacao:
        carta.mutate(make_mutation(mutacao))
    return carta


def valid_card_spec(spec):
    """True se 'spec' é uma carta de baralho válida (usado a validar gravações)."""
    if not isinstance(spec, str):
        return False
    name, _, mutacao = spec.partition("|")
    return name in DECK_CARDS and (not mutacao or mutacao in MUTATION_FACTORIES)


def upgraded_spec(spec):
    """'Segfault|Vampírico' -> 'Segfault+|Vampírico' (a mutação mantém-se no REFACTOR)."""
    name, sep, mutacao = spec.partition("|")
    return UPGRADES[name] + sep + mutacao
