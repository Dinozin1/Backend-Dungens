"""
deck.py - O baralho: guarda as cartas e as três pilhas do combate.

R3 (coleção de objetos): o baralho, a pilha de compra, a mão e o descarte
são listas de objetos Card.
"""
import random

from cards import UPGRADES, make_card


class Deck:
    def __init__(self, cards):
        self._cards = list(cards)   # todas as cartas que o jogador possui
        self._draw_pile = []        # pilha de compra (baralhada)
        self._hand = []             # mão
        self._discard = []          # descarte

    # ---- leitura ----
    @property
    def cards(self):
        return tuple(self._cards)

    @property
    def hand(self):
        return tuple(self._hand)

    @property
    def draw_pile_size(self):
        return len(self._draw_pile)

    @property
    def discard_size(self):
        return len(self._discard)

    @property
    def available_to_draw(self):
        """Cartas que ainda se podem comprar (pilha + descarte reciclável)."""
        return len(self._draw_pile) + len(self._discard)

    def __len__(self):
        return len(self._cards)

    # ---- construção do baralho (recompensas) ----
    def add_card(self, card):
        self._cards.append(card)

    def upgradable_names(self):
        """Nomes (sem repetir) das cartas do baralho que ainda se podem melhorar."""
        nomes = []
        for carta in self._cards:
            if carta.name in UPGRADES and carta.name not in nomes:
                nomes.append(carta.name)
        return nomes

    def upgrade_card(self, name):
        """REFACTOR: troca UMA carta com este nome pela versão melhorada."""
        if name not in UPGRADES:
            raise ValueError(f"{name} não se pode melhorar")
        for i, carta in enumerate(self._cards):
            if carta.name == name:
                self._cards[i] = make_card(UPGRADES[name])
                return self._cards[i]
        raise ValueError(f"{name} não está no baralho")

    # ---- combate ----
    def start_combat(self):
        """Todas as cartas voltam à pilha de compra, baralhadas; mão vazia."""
        self._draw_pile = list(self._cards)
        random.shuffle(self._draw_pile)
        self._hand = []
        self._discard = []

    def draw(self, amount):
        """
        Compra até 'amount' cartas para a mão. Se a pilha acabar, baralha o
        descarte e continua. Devolve as cartas compradas.
        """
        compradas = []
        for _ in range(amount):
            if not self._draw_pile:
                self._draw_pile, self._discard = self._discard, []
                random.shuffle(self._draw_pile)
            if not self._draw_pile:
                break                      # já não há mais cartas nenhumas
            carta = self._draw_pile.pop()
            self._hand.append(carta)
            compradas.append(carta)
        return compradas

    def add_to_hand(self, card):
        """Põe na mão uma carta comprada fora do baralho (a compra do turno)."""
        self._hand.append(card)

    def play_from_hand(self, index):
        """Tira a carta da mão para o descarte e devolve-a."""
        carta = self._hand.pop(index)
        self._discard.append(carta)
        return carta

    def discard_from_hand(self, index):
        """Descarta uma carta da mão (usado quando a mão passa do limite)."""
        carta = self._hand.pop(index)
        self._discard.append(carta)
        return carta
