"""
characters.py - A classe base Character e a classe Player.

R1 (encapsulamento): os atributos começam por "_" (_hp, _block, _energy...)
e só mudam através de métodos da própria classe. Cá fora lê-se com
propriedades (só leitura).
"""
from dataclasses import dataclass

import config


@dataclass
class HitResult:
    """Resultado de um ataque, para o jogo poder contar o que aconteceu."""
    target: str              # nome de quem foi atacado
    total: int = 0           # dano depois dos modificadores (vulnerável, etc.)
    absorbed: int = 0        # quanto o bloqueio absorveu
    lost: int = 0            # vida que realmente se perdeu
    parried: bool = False    # o ataque foi anulado por um parry?
    reflected: int = 0       # dano devolvido ao atacante pelo parry

    def __str__(self):
        if self.parried:
            return (f"{self.target} deu PARRY: dano anulado e "
                    f"{self.reflected} devolvido ao atacante!")
        texto = f"{self.target} perde {self.lost} de vida"
        if self.absorbed:
            texto += f" ({self.absorbed} absorvido pelo bloqueio)"
        return texto


class Character:
    """Base comum a Player e Enemy: vida, bloqueio e estados."""

    def __init__(self, name, max_hp):
        self._name = name
        self._max_hp = max_hp
        self._hp = max_hp
        self._block = 0
        self._vulnerable = 0   # turnos que faltam de "Vulnerável"
        self._weak = 0         # turnos que faltam de "Fraqueza"

    # ---- leitura (propriedades só de leitura) ----
    @property
    def name(self):
        return self._name

    @property
    def hp(self):
        return self._hp

    @property
    def max_hp(self):
        return self._max_hp

    @property
    def block(self):
        return self._block

    @property
    def vulnerable(self):
        return self._vulnerable

    @property
    def weak(self):
        return self._weak

    @property
    def is_alive(self):
        return self._hp > 0

    # ---- ações que alteram o estado ----
    def gain_block(self, amount):
        self._block += amount

    def reset_block(self):
        self._block = 0

    def heal(self, amount):
        """Cura sem passar da vida máxima. Devolve quanto curou de facto."""
        healed = max(0, min(amount, self._max_hp - self._hp))
        self._hp += healed
        return healed

    def apply_status(self, status, turns):
        """Aplica um estado ('vulnerable' ou 'weak'). Não acumula: fica o maior."""
        if status == "vulnerable":
            self._vulnerable = max(self._vulnerable, turns)
        elif status == "weak":
            self._weak = max(self._weak, turns)
        else:
            raise ValueError(f"Estado desconhecido: {status}")

    def clear_statuses(self):
        self._vulnerable = 0
        self._weak = 0

    def outgoing_damage(self, base):
        """Dano que EU causo: a fraqueza reduz 25%."""
        if self._weak > 0:
            return int(base * config.WEAK_MULT)
        return base

    def take_damage(self, amount):
        """
        Recebe dano: vulnerável aumenta 50%, o bloqueio absorve primeiro,
        o resto tira vida (secção 4.2 do relatório).
        """
        if self._vulnerable > 0:
            amount = int(amount * config.VULNERABLE_MULT)
        absorbed = min(self._block, amount)
        self._block -= absorbed
        lost = amount - absorbed
        self._hp = max(0, self._hp - lost)
        return HitResult(self._name, amount, absorbed, lost)

    def receive_attack(self, amount, attacker):
        """
        Chamado quando alguém me ataca. Por omissão é só levar o dano;
        o Player redefine isto para poder dar parry (polimorfismo).
        """
        return self.take_damage(amount)

    def end_turn(self):
        """No fim do turno de cada um, os estados duram menos 1 turno."""
        self._vulnerable = max(0, self._vulnerable - 1)
        self._weak = max(0, self._weak - 1)

    def status_text(self):
        """Texto curto com os estados ativos, para mostrar no ecrã."""
        partes = []
        if self._vulnerable:
            partes.append(f"Vulnerável({self._vulnerable})")
        if self._weak:
            partes.append(f"Fraco({self._weak})")
        return ", ".join(partes) if partes else "-"


class Player(Character):
    """O programador. Tem energia, um baralho, relíquias e pode dar parry."""

    def __init__(self, name, deck):
        super().__init__(name, config.PLAYER_MAX_HP)
        self._deck = deck
        self._energy = 0
        self._attack_bonus = 0   # bónus do "Debug Mode" para o próximo ataque
        self._parry = 0          # dano a devolver se o inimigo atacar neste turno
        self._relics = []        # relíquias apanhadas durante a run

    @property
    def deck(self):
        return self._deck

    @property
    def energy(self):
        return self._energy

    @property
    def parry(self):
        return self._parry

    @property
    def attack_bonus(self):
        return self._attack_bonus

    @property
    def relics(self):
        return tuple(self._relics)

    # ---- relíquias ----
    def add_relic(self, relic):
        self._relics.append(relic)

    def notify_card_played(self, card):
        """Avisa as relíquias de que foi jogada uma carta (ex.: Macro)."""
        for relic in self._relics:
            relic.on_card_played(self, card)

    # ---- gravação ----
    def restore_hp(self, hp):
        """Usado ao carregar uma run gravada (entre 1 e a vida máxima)."""
        self._hp = max(1, min(hp, self._max_hp))

    # ---- energia ----
    def can_afford(self, cost):
        return self._energy >= cost

    def spend_energy(self, cost):
        if not self.can_afford(cost):
            raise ValueError("Energia insuficiente")
        self._energy -= cost

    def gain_energy(self, amount):
        self._energy = min(config.MAX_ENERGY, self._energy + amount)

    # ---- buff e parry ----
    def add_attack_bonus(self, amount):
        self._attack_bonus += amount

    def consume_attack_bonus(self):
        """Devolve o bónus acumulado e gasta-o (só vale para UM ataque)."""
        bonus, self._attack_bonus = self._attack_bonus, 0
        return bonus

    def set_parry(self, reflect_damage):
        self._parry = reflect_damage

    # ---- ciclo do combate ----
    def start_combat(self):
        """Prepara o jogador para um novo combate e compra a mão inicial."""
        self._energy = config.INITIAL_ENERGY
        self._block = 0
        self._parry = 0
        self._attack_bonus = 0
        self.clear_statuses()
        self._deck.start_combat()
        self._deck.draw(config.INITIAL_HAND)
        for relic in self._relics:
            relic.on_combat_start(self)

    def start_turn(self, first_turn):
        """O bloqueio e o parry do turno anterior desaparecem; ganha energia."""
        self.reset_block()
        self._parry = 0
        if not first_turn:
            self.gain_energy(config.ENERGY_PER_TURN)
        for relic in self._relics:
            relic.on_turn_start(self)

    def heal_after_combat(self):
        """Recupera 10% da vida máxima (mais o que as relíquias derem)."""
        extra = sum(r.heal_after_combat() for r in self._relics)
        return self.heal(int(self._max_hp * config.HEAL_AFTER_FIGHT) + extra)

    # ---- redefinições (polimorfismo) ----
    def outgoing_damage(self, base):
        """As relíquias (ex.: Stack Trace) somam dano a cada golpe."""
        bonus = sum(r.attack_bonus() for r in self._relics) if base > 0 else 0
        return super().outgoing_damage(base + bonus)

    def receive_attack(self, amount, attacker):
        """Se há parry ativo, anula o ataque e devolve dano ao atacante."""
        if self._parry > 0:
            reflected = self._parry
            self._parry = 0
            attacker.take_damage(reflected)
            return HitResult(self._name, parried=True, reflected=reflected)
        return self.take_damage(amount)

    def status_text(self):
        partes = [super().status_text()]
        if self._parry:
            partes.append(f"Parry({self._parry})")
        if self._attack_bonus:
            partes.append(f"Próx. ataque +{self._attack_bonus}")
        partes = [p for p in partes if p != "-"]
        return ", ".join(partes) if partes else "-"
