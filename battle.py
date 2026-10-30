"""
battle.py - Um combate (o "ciclo pequeno" da secção 3.2 do relatório).

A Battle NÃO usa print() nem input(): fala com um objeto "ui" (a interface).
Assim a lógica fica separada da interface e podemos trocar texto por 2D
sem reescrever o combate (e testar com um bot, ver test_bot.py).
"""
import config
from cards import BASIC_ATTACK, BASIC_DEFENSE, make_card, random_special


class Battle:
    def __init__(self, player, enemy, ui):
        self._player = player
        self._enemy = enemy
        self._ui = ui
        self._turns = 0

    @property
    def turns(self):
        return self._turns

    def run(self):
        """Corre o combate todo. Devolve True se o jogador ganhou."""
        self._player.start_combat()
        self._ui.message(f"\n>>> Sala {self._enemy.room}/{config.TOTAL_ROOMS}: "
                         f"aparece {self._enemy.name}!")
        while True:
            self._turns += 1
            self._player.start_turn(first_turn=(self._turns == 1))   # 1. início
            self._enemy.plan(self._turns)                            # 2. intenção
            self._ui.show_state(self._player, self._enemy, self._turns)
            self._buy_card()                                         # 3. compra
            self._play_cards()                                       # 4. jogar
            if not self._enemy.is_alive:
                self._ui.message(f"\n{self._enemy.name} foi derrotado!")
                return True
            self._player.end_turn()                                  # 5. fim do turno
            self._enemy_turn()
            if not self._player.is_alive:
                self._ui.message("\nA tua vida chegou a 0. Sistema comprometido...")
                return False

    # ---- passos do turno ----
    def _buy_card(self):
        """Compra de 1 carta: básica à escolha ou especial aleatória (4.3)."""
        escolha = self._ui.choose_purchase()
        if escolha == "attack":
            carta = make_card(BASIC_ATTACK)
        elif escolha == "defense":
            carta = make_card(BASIC_DEFENSE)
        else:
            carta = random_special()
        self._player.deck.add_to_hand(carta)
        self._ui.message(f"Compraste: {carta}")
        self._enforce_hand_limit()

    def _play_cards(self):
        """Joga cartas até o jogador terminar o turno ou o inimigo morrer."""
        while self._enemy.is_alive:
            hand = self._player.deck.hand
            index = self._ui.choose_card(self._player, hand)
            if index is None:                       # o jogador acabou o turno
                return
            if not 0 <= index < len(hand):          # validação de segurança
                self._ui.message("Essa carta não existe.")
                continue
            carta = hand[index]
            if not self._player.can_afford(carta.cost):
                self._ui.message(f"Energia insuficiente para {carta.name} "
                                 f"(custa {carta.cost}, tens {self._player.energy}).")
                continue
            self._player.spend_energy(carta.cost)
            self._player.deck.play_from_hand(index)
            # Polimorfismo: não sabemos que tipo de carta é, só chamamos play().
            self._ui.message(f"-> {carta.name}: {carta.play(self._player, self._enemy)}")
            self._enforce_hand_limit()

    def _enemy_turn(self):
        self._enemy.reset_block()
        for linha in self._enemy.act(self._player):
            self._ui.message(linha)
        self._enemy.end_turn()

    def _enforce_hand_limit(self):
        """Mão acima do limite: o jogador descarta uma carta à escolha."""
        while len(self._player.deck.hand) > config.HAND_LIMIT:
            hand = self._player.deck.hand
            index = self._ui.choose_discard(hand)
            if not 0 <= index < len(hand):
                continue
            carta = self._player.deck.discard_from_hand(index)
            self._ui.message(f"Descartaste {carta.name}.")
