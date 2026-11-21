"""
deck.py - O baralho: guarda as cartas e as três pilhas do combate.

R3 (coleção de objetos): o baralho, a pilha de compra, a mão e o descarte
são listas de objetos Card.
"""
from cards import UPGRADES, make_card, upgraded_spec
from rng import rng


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
        """Identificadores (sem repetir) das cartas que ainda se podem melhorar."""
        nomes = []
        for carta in self._cards:
            if carta.name in UPGRADES and carta.spec not in nomes:
                nomes.append(carta.spec)
        return nomes

    def upgrade_card(self, spec):
        """REFACTOR: troca UMA carta com este identificador pela melhorada (mantém a mutação)."""
        if spec.partition("|")[0] not in UPGRADES:
            raise ValueError(f"{spec} não se pode melhorar")
        for i, carta in enumerate(self._cards):
            if carta.spec == spec:
                self._cards[i] = make_card(upgraded_spec(spec))
                return self._cards[i]
        raise ValueError(f"{spec} não está no baralho")

    def mutable_names(self):
        """Nomes (sem repetir) das cartas que ainda não têm mutação."""
        nomes = []
        for carta in self._cards:
            if carta.mutation is None and carta.name not in nomes:
                nomes.append(carta.name)
        return nomes

    def mutate_card(self, name, mutation):
        """MUTAÇÃO: pendura a mutação em UMA carta com este nome que ainda não tenha uma."""
        for carta in self._cards:
            if carta.name == name and carta.mutation is None:
                carta.mutate(mutation)
                return carta
        raise ValueError(f"{name} não está no baralho (ou já tem mutação)")

    # ---- combate ----
    def start_combat(self):
        """Todas as cartas voltam à pilha de compra, baralhadas; mão vazia."""
        self._draw_pile = list(self._cards)
        rng.shuffle(self._draw_pile)
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
                rng.shuffle(self._draw_pile)
            if not self._draw_pile:
                break                      # já não há mais cartas nenhumas
            carta = self._draw_pile.pop()
            self._hand.append(carta)
            compradas.append(carta)
        return compradas

    def add_to_hand(self, card):
        """Põe na mão uma carta comprada fora do baralho (a compra do turno)."""
        self._hand.append(card)

    def add_to_discard(self, card):
        """Põe uma carta temporária (ex.: Spam) no descarte; some no fim do combate."""
        self._discard.append(card)

    def exile_from_hand(self, index):
        """Tira a carta da mão até ao fim do combate (não vai ao descarte)."""
        return self._hand.pop(index)

    def discard_from_hand(self, index):
        """Tira a carta da mão para o descarte e devolve-a (carta jogada ou descartada)."""
        carta = self._hand.pop(index)
        self._discard.append(carta)
        return carta
