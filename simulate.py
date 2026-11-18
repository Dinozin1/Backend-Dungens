"""
simulate.py - Simula centenas de runs com bots para validar o equilíbrio.

Os bots usam a MESMA classe Game que o jogador humano: só trocam a interface
(TextUI) por uma BotUI. Só é possível porque a lógica está separada da interface.

  python simulate.py          # 300 runs por bot e por modo
  python simulate.py 1000     # mais runs = números mais estáveis

- NaiveBot: joga sempre a carta mais cara que consegue pagar (limite inferior).
- SmartBot: defende quando vai levar dano, usa parry e debuffs, escolhe boas
  recompensas e relíquias. Aproxima um jogador razoável (não poupa energia).
"""
import random
import sys
from collections import Counter

from cards import (REFACTOR_OPTION, AttackCard, BuffCard, DebuffCard, DefenseCard,
                   DrawCard, EnergyCard, HealCard, ParryCard)
from game import Game
from hall_of_fame import HallOfFame
from modes import MODES
from savegame import SaveGame
from ui import RunUI


class NaiveBot(RunUI):
    """Interface automática simples: implementa a RunUI (sem menus)."""

    def ask_name(self): return "Bot"
    def confirm(self, question): return True
    def message(self, text): pass
    def show_state(self, player, enemy, turn): pass

    def choose_purchase(self, can_draw_deck):
        opcoes = ["attack", "defense"] + (["deck"] if can_draw_deck else [])
        return random.choice(opcoes)

    def choose_card(self, player, hand):
        pagaveis = [i for i, c in enumerate(hand) if player.can_afford(c.cost)]
        return max(pagaveis, key=lambda i: hand[i].cost) if pagaveis else None

    def choose_discard(self, hand): return 0
    def choose_reward(self, options, can_upgrade=False):
        return random.choice(options)
    def choose_upgrade(self, pairs): return random.randrange(len(pairs))
    def choose_relic(self, options): return random.choice(options)


class SmartBot(NaiveBot):
    REWARD_ORDER = ["Firewall", "Kernel Panic", "Segfault", "Zombie Process",
                    "Stack Overflow", "Catch & Return", "Buffer Overflow", "Try/Catch",
                    "Fork Bomb", "Rate Limiter", "Infinite Loop", "Garbage Collector",
                    "Ctrl+Z", "Debug Mode", "Sudo"]
    UPGRADE_ORDER = ["Segfault", "Firewall", "Try/Catch", 'Print("Hit")', "If/Else",
                     "Kernel Panic", "Zombie Process", "Catch & Return"]
    RELIC_ORDER = ["Overclock", "Antivirus", "Linter", "Macro", "Stack Trace",
                   "Auto-Save", "Cache L1", "Backup", "Overvolt", "Código Legado"]

    def __init__(self):
        self.player = self.enemy = None

    def show_state(self, player, enemy, turn):
        self.player, self.enemy = player, enemy

    def _incoming(self):
        """Dano que o inimigo vai causar (o bot 'já aprendeu' o padrão do boss)."""
        it = self.enemy.intent
        return it.value * it.hits if it.kind == "attack" else 0

    def choose_purchase(self, can_draw_deck):
        p, hand = self.player, self.player.deck.hand
        em_perigo = self._incoming() - p.block >= p.hp * 0.3
        if em_perigo and not any(isinstance(c, DefenseCard) for c in hand):
            return "defense"
        if can_draw_deck and len(hand) < 5:
            return "deck"
        return random.choices(["attack", "defense"], [0.6, 0.4])[0]

    def _pick(self, hand, player, kind):
        return [(i, c) for i, c in enumerate(hand)
                if isinstance(c, kind) and player.can_afford(c.cost)]

    def choose_card(self, player, hand):
        e = self.enemy
        if not any(player.can_afford(c.cost) for c in hand):
            return None
        incoming = self._incoming()
        em_falta = incoming - player.block
        # 1. parry quando o inimigo vai atacar
        parries = self._pick(hand, player, ParryCard)
        if incoming > 0 and player.parry == 0 and parries:
            return parries[0][0]
        # 2. defender se o ataque deixar a vida baixa
        defs = self._pick(hand, player, DefenseCard)
        if em_falta > 0 and player.hp - em_falta < 30 and defs:
            return max(defs, key=lambda ic: ic[1].block_amount / ic[1].cost)[0]
        # 3. curar, debuff, compra extra, buff
        heals = self._pick(hand, player, HealCard)
        if player.hp <= player.max_hp - 8 and heals:
            return heals[0][0]
        # debuff só se o inimigo ainda não tem esse estado (e se vale a pena)
        for i, c in self._pick(hand, player, DebuffCard):
            if getattr(e, c.status) == 0 and e.hp > 20:
                return i
        # Sudo: energia barata, quando há cartas que não consigo pagar e a vida aguenta
        energia = self._pick(hand, player, EnergyCard)
        if (energia and player.hp > 30
                and any(c.cost > player.energy for c in hand)):
            return energia[0][0]
        draws = self._pick(hand, player, DrawCard)
        if draws and len(hand) <= 5:
            return draws[0][0]
        buffs = self._pick(hand, player, BuffCard)
        atks = self._pick(hand, player, AttackCard)
        if buffs and player.attack_bonus == 0 and atks and player.energy >= buffs[0][1].cost + 1:
            return buffs[0][0]
        # 4. atacar: se der para matar, mata; senão o mais eficiente
        mult = 1.5 if e.vulnerable else 1
        if atks:
            matam = [ic for ic in atks if ic[1].total_damage * mult >= e.hp + e.block]
            if matam:
                return matam[0][0]
            return max(atks, key=lambda ic: (ic[1].total_damage / ic[1].cost,
                                             ic[1].total_damage))[0]
        if em_falta > 0 and defs:
            return defs[0][0]
        return None

    def choose_reward(self, options, can_upgrade=False):
        """Fica com uma carta boa; se não houver nenhuma, faz REFACTOR."""
        nomes = {c.name: c for c in options}
        for nome in self.REWARD_ORDER[:7]:
            if nome in nomes:
                return nomes[nome]
        if can_upgrade:
            return REFACTOR_OPTION
        for nome in self.REWARD_ORDER:
            if nome in nomes:
                return nomes[nome]
        return options[0]

    def choose_upgrade(self, pairs):
        nomes = [antes.name for antes, _ in pairs]
        for nome in self.UPGRADE_ORDER:
            if nome in nomes:
                return nomes.index(nome)
        return 0

    def choose_relic(self, options):
        nomes = {r.name: r for r in options}
        for nome in self.RELIC_ORDER:
            if nome in nomes:
                return nomes[nome]
        return options[0]


def simulate(mode_key, bot_class, n=300):
    """Corre n runs reais (classe Game) e devolve (vitórias, salas médias, mortes por sala)."""
    mortes, salas, vitorias = Counter(), [], 0
    for _ in range(n):
        hall = HallOfFame(None)
        Game(ui=bot_class(), hall=hall, save=SaveGame(None)).play_new(MODES[mode_key])
        entrada = hall.entries[0]
        salas.append(entrada.rooms)
        if entrada.won:
            vitorias += 1
        else:
            mortes[entrada.rooms + 1] += 1
    return vitorias / n, sum(salas) / n, mortes


def report(n=300):
    for bot in (NaiveBot, SmartBot):
        for mode in MODES.values():
            v, media, mortes = simulate(mode.key, bot, n)
            dist = ", ".join(f"sala {s}: {c / n:.0%}" for s, c in sorted(mortes.items()))
            print(f"{bot.__name__:<9} {mode.label:<18} vitórias {v:>4.0%} | "
                  f"salas limpas {media:.1f} | mortes -> {dist or '-'}")


if __name__ == "__main__":
    random.seed(2026)
    report(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
