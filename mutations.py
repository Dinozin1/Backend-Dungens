"""
mutations.py - Mutações de cartas: uma carta do baralho muda de comportamento.

Uma Mutation não é uma carta: é um objeto que se PENDURA numa carta (uma por carta) e
a faz comportar-se de outra maneira, sempre com um preço. A carta continua a ser
um AttackCard, um DefenseCard... (por isso os bots e as relíquias que olham para o
tipo da carta não se enganam).

R2: Mutation é a classe base com "ganchos" que as subclasses redefinem:
  modify_cost(custo) - muda o custo (nunca fica abaixo de 1);
  after_play(...)    - efeito extra depois de a carta ser jogada;
  EXHAUSTS           - a carta é exilada até ao fim do combate depois de jogada;
  EXTRA_PLAYS        - quantas vezes extra o efeito da carta se repete.

Para criar uma mutação nova basta escrever a classe: o catálogo constrói-se sozinho.
Este módulo não importa cartas (só usa os métodos do jogador e do inimigo).
"""


class Mutation:
    NAME = "Mutação"
    DESCRIPTION = ""
    EXHAUSTS = False
    EXTRA_PLAYS = 0

    @property
    def name(self):
        return self.NAME

    @property
    def description(self):
        return self.DESCRIPTION

    def modify_cost(self, cost):
        return cost

    def after_play(self, card, player, enemy):
        """Efeito extra depois de jogar a carta. Devolve um texto (ou '')."""
        return ""

    def __str__(self):
        return f"{self.NAME}: {self.DESCRIPTION}"


class Unstable(Mutation):
    NAME = "Instável"
    DESCRIPTION = "custo -1, mas perdes 2 de vida ao jogá-la"

    def modify_cost(self, cost):
        return cost - 1

    def after_play(self, card, player, enemy):
        return f"Instável: perdes {player.lose_hp(2)} de vida."


class Recursive(Mutation):
    NAME = "Recursivo"
    DESCRIPTION = "custo +1, mas o efeito acontece duas vezes"
    EXTRA_PLAYS = 1

    def modify_cost(self, cost):
        return cost + 1


class Vampiric(Mutation):
    NAME = "Vampírico"
    DESCRIPTION = "recuperas 2 de vida ao jogá-la"

    def after_play(self, card, player, enemy):
        return f"Vampírico: recuperas {player.heal(2)} de vida."


class Armored(Mutation):
    NAME = "Blindado"
    DESCRIPTION = "ganhas 3 de bloqueio ao jogá-la"

    def after_play(self, card, player, enemy):
        player.gain_block(3)
        return "Blindado: ganhas 3 de bloqueio."


class Infected(Mutation):
    NAME = "Infectado"
    DESCRIPTION = "o inimigo fica Envenenado 2 turnos"

    def after_play(self, card, player, enemy):
        enemy.apply_status("poison", 2)
        return f"Infectado: {enemy.name} fica envenenado."


class Ephemeral(Mutation):
    NAME = "Efémero"
    DESCRIPTION = "custo -1, mas é exilada até ao fim do combate depois de jogada"
    EXHAUSTS = True

    def modify_cost(self, cost):
        return cost - 1


class Precompiled(Mutation):
    NAME = "Compilado"
    DESCRIPTION = "custo +1, mas compras 1 carta do baralho ao jogá-la"

    def modify_cost(self, cost):
        return cost + 1

    def after_play(self, card, player, enemy):
        compradas = player.deck.draw(1)
        return "Compilado: compraste " + (compradas[0].name if compradas else "nada") + "."


# Catálogo automático: nome -> classe.
MUTATION_FACTORIES = {cls.NAME: cls for cls in Mutation.__subclasses__()}


def make_mutation(name):
    if name not in MUTATION_FACTORIES:
        raise KeyError(f"Mutação inexistente: {name}")
    return MUTATION_FACTORIES[name]()
