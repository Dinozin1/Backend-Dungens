"""
test_bot.py - Simula runs com um bot (sem consola) para testar e afinar o equilíbrio.
Só é possível porque a lógica está separada da interface: o BotUI tem os
mesmos métodos do TextUI. Corre com:  python test_bot.py
"""
import random
import tempfile
from pathlib import Path

from battle import Battle
from cards import make_card
from characters import Player
from deck import Deck
from enemies import spawn_enemy
from game import STARTER_DECK, Game
from hall_of_fame import HallOfFame, ScoreEntry
import config


class BotUI:
    """Interface automática: joga sempre a carta mais cara que consegue pagar."""
    def __init__(self, purchase_weights=(0.4, 0.4, 0.2)):
        self.w = purchase_weights

    def message(self, t): pass
    def show_state(self, *a): pass
    def choose_purchase(self):
        return random.choices(["attack", "defense", "special"], self.w)[0]
    def choose_card(self, player, hand):
        ok = [i for i, c in enumerate(hand) if player.can_afford(c.cost)]
        if not ok:
            return None
        return max(ok, key=lambda i: hand[i].cost)
    def choose_discard(self, hand): return 0
    def choose_reward(self, options): return random.choice(options)


def simulate(n=300):
    ui, rooms, wins = BotUI(), [], 0
    for _ in range(n):
        player = Player("Bot", Deck([make_card(c) for c in STARTER_DECK]))
        cleared = 0
        for room in range(1, config.TOTAL_ROOMS + 1):
            b = Battle(player, spawn_enemy(room), ui)
            if not b.run():
                break
            cleared += 1
            if room < config.TOTAL_ROOMS:
                player.heal_after_combat()
                player.deck.add_card(ui.choose_reward(
                    [make_card(x) for x in random.sample(__import__('cards').REWARD_POOL, 3)]))
        rooms.append(cleared)
        wins += cleared == config.TOTAL_ROOMS
    print(f"{n} runs: vitórias {wins/n:.0%}, salas limpas em média {sum(rooms)/n:.1f}")


def test_rules():
    """Testes rápidos das regras principais."""
    p = Player("T", Deck([make_card(c) for c in STARTER_DECK]))
    e = spawn_enemy(1)
    # dano vs bloqueio
    e.gain_block(3); r = e.take_damage(5)
    assert r.absorbed == 3 and r.lost == 2
    # vulnerável +50%
    e2 = spawn_enemy(1); e2.apply_status("vulnerable", 2)
    assert e2.take_damage(10).total == 15
    # fraqueza -25%
    p.apply_status("weak", 1); assert p.outgoing_damage(8) == 6
    # parry anula e devolve
    p2 = Player("P", Deck([])); p2.set_parry(8); en = spawn_enemy(1); hp = en.hp
    res = p2.receive_attack(99, en)
    assert res.parried and p2.hp == p2.max_hp and en.hp == hp - 8
    # energia nunca passa do teto e nunca fica negativa
    p2.gain_energy(100); assert p2.energy == config.MAX_ENERGY
    try:
        p2.spend_energy(99); assert False
    except ValueError:
        pass
    # carta inexistente
    try:
        make_card("Nope"); assert False
    except KeyError:
        pass
    # recordes: ficheiro em falta e ficheiro corrompido
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "s.json"
        h = HallOfFame(f); assert h.top() == []
        h.add(ScoreEntry("A", 10, 1, False)); assert h.save()
        assert HallOfFame(f).top()[0].name == "A"
        f.write_text("{lixo", encoding="utf-8")
        h2 = HallOfFame(f); assert h2.top() == [] and h2.warning
    print("Testes das regras: OK")


if __name__ == "__main__":
    test_rules()
    simulate()
