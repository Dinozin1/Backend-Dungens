"""
config.py - Todos os valores de equilíbrio do jogo num só sítio.

O relatório diz que os valores são "a afinar nos testes". Em vez de espalhar
números pelo código, ficam aqui como constantes: para mudar a dificuldade
basta editar este ficheiro.
"""

# --- Jogador (secção 4.1 do relatório) ---
PLAYER_MAX_HP = 60          # vida máxima
INITIAL_ENERGY = 3          # energia com que se começa cada combate
ENERGY_PER_TURN = 3         # ganho de energia por turno (o relatório diz 2 ou 3; afinado com o bot)
MAX_ENERGY = 8              # a energia acumula entre turnos, até este teto
INITIAL_HAND = 5            # cartas da mão inicial
HAND_LIMIT = 8              # acima disto, descarta-se uma carta à escolha
HEAL_AFTER_FIGHT = 0.10     # recupera 10% da vida máxima no fim de cada combate

# --- Anti-impasse ---
ENRAGE_TURN = 12            # depois deste turno o inimigo ganha +1 de dano por turno

POISON_DAMAGE = 3           # veneno: dano por turno (ignora o bloqueio)

# --- Estados (secção 4.2) ---
VULNERABLE_MULT = 1.5       # vulnerável: +50% de dano recebido
WEAK_MULT = 0.75            # fraqueza: -25% de dano causado

# --- Run (secção 3.1 e 6) ---
# (o número de salas depende do modo de jogo: ver modes.py)
REWARD_CHOICES = 3          # no fim do combate: 1 carta entre 3
PLAYER_NAME_MAX = 12        # tamanho máximo do nome no ficheiro de recordes
