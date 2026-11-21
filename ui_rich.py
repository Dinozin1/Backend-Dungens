"""
ui_rich.py - Interface a cores com a biblioteca "rich" (opcional).

Herda de TextUI e redefine só a parte VISUAL (os métodos _show_*, o estado do
combate, os menus e os recordes). A validação das entradas (R4) e as regras são
as da TextUI. Se o rich não estiver instalado, o main.py usa a TextUI normal.

Nota: os textos passam sempre por Text(...) para o rich não interpretar
os "[custo 1]" das cartas como etiquetas de formatação.
"""
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import config
from cards import (BASIC_ATTACK, BASIC_DEFENSE, AttackCard, BuffCard, DebuffCard,
                   DefenseCard, DrawCard, EnergyCard, HealCard, ParryCard,
                   RecoilAttackCard, make_card)
from ui import QuitGame, TextUI

# Tipo de carta -> (nome mostrado, cor). A ordem conta: a primeira que servir ganha.
CARD_KINDS = (
    (AttackCard, "Ataque", "red"),
    (DefenseCard, "Defesa", "cyan"),
    (HealCard, "Cura", "green"),
    (ParryCard, "Parry", "yellow"),
    (BuffCard, "Buff", "bright_magenta"),
    (DebuffCard, "Debuff", "magenta"),
    (DrawCard, "Compra", "blue"),
    (EnergyCard, "Energia", "bright_yellow"),
)
RISKY = (RecoilAttackCard, EnergyCard)

# O que o inimigo vai fazer -> cor da intenção.
INTENT_STYLES = {"attack": "bold red", "defend": "cyan", "weaken": "magenta",
                 "expose": "magenta", "heal": "green", "poison": "bold green",
                 "drain": "bright_yellow", "spam": "bright_black"}

# Mensagens do jogo -> estilo (a primeira regra que coincidir ganha).
MESSAGE_STYLES = (
    ("VITÓRIA", "bold green"), ("FIM DA RUN", "bold red"),
    ("vida chegou a 0", "bold red"), ("foi derrotado", "bold green"),
    (">>>", "bold cyan"), ("PARRY", "bold yellow"), ("REFACTOR", "bold magenta"),
    ("MUTAÇÃO", "bold bright_magenta"), ("Combate retomado", "dim"),
    ("exilada", "dim"), ("rouba-te", "bright_yellow"), ("envenena-te", "bold green"),
    ("Relíquia obtida", "bright_blue"), ("inválid", "yellow"), ("não é permitido", "yellow"),
    ("ataca!", "red"), ("->", "yellow"), ("Recuperas", "green"), ("cura-se", "green"),
    ("veneno", "green"),
)


def card_kind(card):
    """(nome, cor) do tipo da carta; as de risco ficam marcadas."""
    for classe, nome, cor in CARD_KINDS:
        if isinstance(card, classe):
            return (nome + " (risco)" if isinstance(card, RISKY) else nome), cor
    return "Carta", "white"


class RichUI(TextUI):
    def __init__(self):
        self._console = Console()

    # ---------- base ----------
    def _read(self, prompt):
        try:
            return self._console.input(Text(prompt, style="bold cyan"))
        except EOFError:
            raise QuitGame

    def message(self, text):
        estilo = next((s for chave, s in MESSAGE_STYLES if chave in text), None)
        self._console.print(Text(text, style=estilo or ""))

    @staticmethod
    def _bar(valor, maximo, cor, tamanho=20):
        cheio = round(tamanho * valor / maximo) if maximo else 0
        barra = Text()
        barra.append("█" * cheio, style=cor)
        barra.append("░" * (tamanho - cheio), style="grey37")
        return barra

    @staticmethod
    def _hp_color(hp, max_hp):
        ratio = hp / max_hp if max_hp else 0
        return "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"

    def _cards_table(self, title, cards, player=None, first_col="#"):
        """Tabela de cartas (mão, recompensas, descarte). Sem energia fica a cinzento."""
        tabela = Table(title=title, header_style="bold", box=box.ROUNDED)
        tabela.add_column(first_col, justify="right")
        tabela.add_column("Carta")
        tabela.add_column("Tipo")
        tabela.add_column("Custo", justify="center")
        tabela.add_column("Efeito")
        for i, carta in enumerate(cards, 1):
            tipo, cor = card_kind(carta)
            pagavel = player is None or player.can_afford(carta.cost)
            estilo = None if pagavel else "dim"
            mutada = carta.mutation is not None
            tabela.add_row(Text(str(i)),
                           Text(carta.display_name, style=f"bold {cor}" + (" italic" if mutada else "")),
                           Text(tipo, style=cor), Text(str(carta.cost), style="yellow"),
                           Text(carta.description), style=estilo)
        self._console.print(tabela)

    def _option(self, number, text, style="white"):
        linha = Text()
        linha.append(f" {number}) ", style="bold cyan")
        linha.append(text, style=style)
        self._console.print(linha)

    # ---------- menus ----------
    def _show_menu(self, opcoes):
        titulo = Text(justify="center")
        titulo.append("BACKEND DUNGEONS\n", style="bold bright_green")
        titulo.append("Limpa o sistema infetado, sala a sala!", style="italic")
        self._console.print(Panel(titulo, border_style="bright_green", box=box.DOUBLE))
        for i, (chave, texto) in enumerate(opcoes, 1):
            self._option(i, texto, "bold yellow" if chave == "continue" else "white")

    def show_help(self):
        self._console.print(Panel(Text(self.help_text()), title="Como jogar",
                                  border_style="cyan"))

    def show_hall(self, tables, warning=""):
        if warning:
            self._console.print(Text(f"(aviso: {warning})", style="yellow"))
        medalhas = {1: "bold yellow", 2: "bold white", 3: "bold #cd7f32"}
        for titulo, entradas in tables:
            tabela = Table(title=f"Recordes - {titulo}", box=box.ROUNDED)
            for coluna in ("#", "Nome", "Pontos", "Resultado"):
                tabela.add_column(coluna)
            for i, e in enumerate(entradas, 1):
                tabela.add_row(Text(str(i)), Text(e.name), Text(str(e.score)),
                               Text("VITÓRIA" if e.won else f"sala {e.rooms}",
                                    style="green" if e.won else "red"),
                               style=medalhas.get(i))
            if not entradas:
                tabela.add_row(Text("-"), Text("Ainda não há recordes."), Text(""), Text(""))
            self._console.print(tabela)

    # ---------- combate ----------
    def show_state(self, player, enemy, turn):
        quadro = Table.grid(padding=(0, 2))
        for personagem in (enemy, player):
            quadro.add_row(
                Text(personagem.name, style="bold"),
                self._bar(personagem.hp, personagem.max_hp,
                          self._hp_color(personagem.hp, personagem.max_hp)),
                Text(f"{personagem.hp}/{personagem.max_hp}"),
                Text(f"bloqueio {personagem.block}", style="cyan"),
                Text(personagem.status_text(), style="yellow"))
        texto_intencao = enemy.describe_intent()
        estilo = ("bold magenta" if "???" in texto_intencao
                  else INTENT_STYLES.get(enemy.intent.kind, ""))
        corpo = Text()
        corpo.append(f"Intenção: {texto_intencao}\n", style=estilo)
        corpo.append(f"Energia {player.energy}/{config.MAX_ENERGY}", style="bold yellow")
        corpo.append(f"   Baralho {player.deck.draw_pile_size}"
                     f"   Descarte {player.deck.discard_size}")
        if player.relics:
            corpo.append("\nRelíquias: " + ", ".join(r.name for r in player.relics),
                         style="bright_blue")
        grelha = Table.grid()
        grelha.add_row(quadro)
        grelha.add_row(corpo)
        self._console.print(Panel(grelha, title=f"Turno {turn}", border_style="cyan"))

    def _show_purchase(self, can_draw_deck):
        self._console.print(Text("\nCompra do turno (escolhe 1):", style="bold"))
        for numero, nome, rotulo in ((1, BASIC_ATTACK, "ATAQUE"), (2, BASIC_DEFENSE, "DEFESA")):
            carta = make_card(nome)
            _, cor = card_kind(carta)
            self._option(numero, f"Carta básica de {rotulo} - {carta.name} "
                                 f"[custo {carta.cost}] {carta.description}", cor)
        if can_draw_deck:
            self._option(3, "Carta do teu BARALHO (o que construíste na run)", "bold yellow")

    def _show_hand(self, player, hand):
        self._cards_table(f"Mão (energia {player.energy})", hand, player)
        self._option(0, "Terminar turno", "dim")

    def _show_discard(self, hand):
        self.message(f"\nA mão passou de {config.HAND_LIMIT} cartas! Descarta uma:")
        self._cards_table("Descartar", hand)

    def _show_reward(self, options, can_upgrade, mutation=None):
        self._console.print(Text("\nRecompensa! Escolhe uma carta para o baralho:",
                                 style="bold green"))
        self._cards_table("Recompensa", options)
        refactor, mutar = self._reward_numbers(options, can_upgrade, mutation)
        if refactor:
            self._option(refactor, "REFACTOR: melhora uma carta do teu baralho",
                         "bold magenta")
        if mutar:
            self._option(mutar, f"MUTAÇÃO ({mutation}) numa carta do teu baralho",
                         "bold bright_magenta")
        self._option(0, "Nenhuma (mantém o baralho pequeno)", "dim")

    def _show_mutation_target(self, mutation, pairs):
        tabela = Table(title=f"MUTAÇÃO - {mutation}", box=box.ROUNDED)
        for coluna in ("#", "Agora", "Depois"):
            tabela.add_column(coluna)
        for i, (antes, depois) in enumerate(pairs, 1):
            _, cor = card_kind(antes)
            tabela.add_row(Text(str(i)),
                           Text(f"{antes.name} [custo {antes.cost}] - {antes.description}",
                                style=cor),
                           Text(f"{depois.display_name} [custo {depois.cost}] - "
                                f"{depois.description}", style=f"bold {cor}"))
        self._console.print(tabela)
        self._option(0, "Voltar atrás", "dim")

    def _show_upgrades(self, pairs):
        tabela = Table(title="REFACTOR - que carta queres melhorar?", box=box.ROUNDED)
        for coluna in ("#", "Agora", "Depois"):
            tabela.add_column(coluna)
        for i, (antes, depois) in enumerate(pairs, 1):
            _, cor = card_kind(antes)
            tabela.add_row(Text(str(i)),
                           Text(f"{antes.display_name} - {antes.description}", style=cor),
                           Text(f"{depois.display_name} - {depois.description}",
                                style=f"bold {cor}"))
        self._console.print(tabela)
        self._option(0, "Voltar atrás", "dim")

    def _show_relics(self, options):
        tabela = Table(title="Encontraste uma relíquia! (dura até ao fim da run)",
                       box=box.ROUNDED)
        for coluna in ("#", "Relíquia", "Efeito"):
            tabela.add_column(coluna)
        for i, relic in enumerate(options, 1):
            risco = relic.description.startswith("RISCO")
            tabela.add_row(Text(str(i)), Text(relic.name, style="bold bright_blue"),
                           Text(relic.description, style="red" if risco else ""))
        self._console.print(tabela)
