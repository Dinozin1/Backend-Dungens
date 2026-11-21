"""
rng.py - O gerador de números aleatórios DO JOGO (baralhar, escolher inimigo,
sortear recompensas e relíquias).

É um gerador à parte do módulo `random` global, que fica para as interfaces e
os bots. Assim, o que o jogador (ou um bot) faz com o `random` nunca mexe nas
cartas que saem: com a mesma semente e as mesmas respostas, a sala repete-se
exatamente igual. É isto que permite retomar um combate a meio (replay.py).
"""
import random

rng = random.Random()
