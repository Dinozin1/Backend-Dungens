"""
ui_rich.py - Interface a cores com a biblioteca "rich" (opcional).

Herda de TextUI e só redefine a parte VISUAL (estado do combate, mão, recordes).
A validação das entradas e as regras continuam iguais. Se o rich não estiver
instalado, o main.py usa a TextUI normal.

Nota: os textos passam sempre por Text(...) para o rich não interpretar
os "[custo 1]" das cartas como etiquetas de formatação.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import config
from ui import TextUI


class RichUI(TextUI):
    def __init__(self):
        self._console = Console()

    def message(self, text):
        self._console.print(Text(text))

    @staticmethod
    def _bar(valor, maximo, cor, tamanho=20):
        cheio = round(tamanho * valor / maximo) if maximo else 0
        barra = Text()
        barra.append("█" * cheio, style=cor)
        barra.append("░" * (tamanho - cheio), style="grey37")
        return barra

    def show_state(self, player, enemy, turn):
        quadro = Table.grid(padding=(0, 2))
        for atacante, cor in ((enemy, "red"), (player, "green")):
            quadro.add_row(
                Text(atacante.name, style="bold"),
                self._bar(atacante.hp, atacante.max_hp, cor),
                Text(f"{atacante.hp}/{atacante.max_hp}"),
                Text(f"bloqueio {atacante.block}", style="cyan"),
                Text(atacante.status_text(), style="yellow"))
        corpo = Text()
        corpo.append(f"Intenção: {enemy.describe_intent()}\n", style="bold magenta")
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

    def choose_card(self, player, hand):
        tabela = Table(title=f"Mão (energia {player.energy})", header_style="bold")
        tabela.add_column("#", justify="right")
        tabela.add_column("Carta")
        tabela.add_column("Custo", justify="center")
        tabela.add_column("Efeito")
        for i, carta in enumerate(hand, 1):
            estilo = None if player.can_afford(carta.cost) else "dim"
            tabela.add_row(Text(str(i)), Text(carta.name), Text(str(carta.cost)),
                           Text(carta.description), style=estilo)
        self._console.print(tabela)
        print(" 0) Terminar turno")
        validas = ["0"] + [str(i) for i in range(1, len(hand) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def show_hall(self, tables, warning=""):
        if warning:
            self._console.print(Text(f"(aviso: {warning})", style="yellow"))
        for titulo, entradas in tables:
            tabela = Table(title=f"Recordes - {titulo}")
            for coluna in ("#", "Nome", "Pontos", "Resultado"):
                tabela.add_column(coluna)
            for i, e in enumerate(entradas, 1):
                tabela.add_row(Text(str(i)), Text(e.name), Text(str(e.score)),
                               Text("VITÓRIA" if e.won else f"sala {e.rooms}"))
            self._console.print(tabela)
