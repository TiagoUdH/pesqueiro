import pygame
import sys
import os
import configparser
import random

# ── Diretorios ──────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.join(BASE_DIR, "..")
IMG_DIR     = os.path.join(ROOT_DIR, "imagens")
SND_DIR     = os.path.join(ROOT_DIR, "sons")
CONFIG_FILE = os.path.join(ROOT_DIR, "config.ini")
SAVE_FILE   = os.path.join(ROOT_DIR, "save.ini")

# ── Configuracoes ────────────────────────────────────────────────────────────
config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")

LARGURA  = config.getint("jogo", "largura",  fallback=800)
ALTURA   = config.getint("jogo", "altura",   fallback=600)
FPS      = config.getint("jogo", "fps",      fallback=60)
TITULO   = config.get   ("jogo", "titulo",   fallback="Pesqueiro")

# ── Cores ────────────────────────────────────────────────────────────────────
BRANCO   = (255, 255, 255)
PRETO    = (0,   0,   0)
AZUL_CEU = (135, 206, 235)
AZUL_MAR = (30,  100, 160)
VERDE    = (34,  139, 34)
MARROM   = (101, 67,  33)

# ── Layout da tela ──────────────────────────────────────────────────────────
LINHA_AGUA = 370        # y onde a agua começa (pixels do topo)
DOCK_X     = 430        # x do dock
DOCK_Y     = LINHA_AGUA - 65   # = 305  (dock se apoia na beira da agua)

# ── Estados do jogo ──────────────────────────────────────────────────────────
ESTADO_MENU    = "menu"
ESTADO_JOGANDO = "jogando"
ESTADO_LOJA    = "loja"
ESTADO_FIM     = "fim"
ESTADO_PAUSA   = "pausa"
ESTADO_TUTORIAL = "tutorial"

# ── Estados do pescador ──────────────────────────────────────────────────────
PESC_IDLE     = "idle"
PESC_LANCANDO = "lancando"
PESC_PUXANDO  = "puxando"

# ── Estados do anzol ────────────────────────────────────────────────────────
ANZOL_IDLE     = "idle"      # nao lancado, invisivel
ANZOL_DESCENDO = "descendo"  # descendo na agua
ANZOL_NA_AGUA  = "na_agua"   # parado aguardando
ANZOL_SUBINDO  = "subindo"   # voltando para cima

# ── Estados do peixe ────────────────────────────────────────────────────────
PEIXE_NADANDO  = "nadando"   # nadando livremente
PEIXE_ATRAIDO  = "atraido"   # indo em direcao ao anzol
PEIXE_MORDENDO = "mordendo"  # tocando o anzol, esperando o pull
PEIXE_CAPTURADO = "capturado"  # fisgado, subindo com o anzol
PEIXE_FUGINDO  = "fugindo"   # escapou, afasta do anzol

# Ponta da vara do pescador (origem da linha)
# Calculado com base na posicao do pescador (DOCK_X+110, DOCK_Y+68) e escala 110x165
VARA_PONTA_X = DOCK_X + 148   # proximo ao topo direito do sprite do pescador
VARA_PONTA_Y = DOCK_Y - 80

LINHA_AGUA_PADRAO = LINHA_AGUA
BOAT_X = 250
BOAT_AGUA_OFFSET = 40


def load_image(subdir, name, scale=None):
    """Carrega imagem e converte para o formato da tela."""
    path = os.path.join(IMG_DIR, subdir, name)
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        return img
    except FileNotFoundError:
        # Placeholder colorido enquanto os assets nao estao prontos
        surf = pygame.Surface(scale if scale else (50, 50), pygame.SRCALPHA)
        surf.fill((200, 50, 200, 180))
        return surf


# ════════════════════════════════════════════════════════════════════════════
class Cenario:
    """Renderiza fundo, agua, dock (ou barco em alto-mar)."""

    def __init__(self):
        self.fundo_dock = load_image("cenario", "fundo.png", (LARGURA, LINHA_AGUA))
        self.fundo_mar  = load_image("cenario", "fundo_mar_aberto.png", (LARGURA, LINHA_AGUA))

        self.dock_img = load_image("cenario", "dock.png", (220, 110))
        self.dock_img.set_colorkey(BRANCO)

        self.barco_img = load_image("cenario", "barco.png", (320, 140))
        self.barco_img.set_colorkey(BRANCO)

    def draw(self, tela, agua_y, barco_comprado=False, barco_x=0, barco_y=0):
        agua_h = ALTURA - agua_y
        agua_img = load_image("cenario", "agua.png", (LARGURA, agua_h))

        if barco_comprado:
            tela.blit(self.fundo_mar, (0, 0))
            tela.blit(agua_img, (0, agua_y))
            tela.blit(self.barco_img, (barco_x, barco_y))
        else:
            tela.blit(self.fundo_dock, (0, 0))
            tela.blit(agua_img, (0, agua_y))
            tela.blit(self.dock_img, (DOCK_X, DOCK_Y))


# ════════════════════════════════════════════════════════════════════════════
class Pescador(pygame.sprite.Sprite):
    """Pescador com 3 estados visuais: idle, lancando, puxando."""

    ESCALA = (110, 165)

    def __init__(self):
        super().__init__()
        self.frames = {
            PESC_IDLE:     self._carregar("idle.png"),
            PESC_LANCANDO: self._carregar("lancando.png"),
            PESC_PUXANDO:  self._carregar("puxando.png"),
        }
        self.estado = PESC_IDLE
        self.image  = self.frames[self.estado]

        # Posiciona o pescador em pe na superficie plana do dock
        self.rect = self.image.get_rect()
        self.rect.midbottom = (DOCK_X + 110, DOCK_Y + 68)

    def _carregar(self, nome):
        img = load_image("pescador", nome, self.ESCALA)
        img.set_colorkey(BRANCO)
        return img

    def set_estado(self, novo_estado):
        if novo_estado != self.estado:
            self.estado = novo_estado
            self.image  = self.frames[novo_estado]

    def reposicionar(self, x, y):
        self.rect.midbottom = (x, y)

    def draw(self, tela):
        tela.blit(self.image, self.rect)


# ════════════════════════════════════════════════════════════════════════════
class Anzol(pygame.sprite.Sprite):
    """Anzol que desce e sobe na agua."""

    ESCALA    = (38, 55)
    PROF_MAX  = 120   # profundidade maxima padrao (pixels abaixo da agua)

    def __init__(self, vel=3, agua_y=LINHA_AGUA_PADRAO, vara_x=VARA_PONTA_X, vara_y=VARA_PONTA_Y):
        super().__init__()
        img = load_image("peixes", "anzol.png", self.ESCALA)
        img.set_colorkey(BRANCO)
        self.image = img
        self.rect  = self.image.get_rect()

        self.vel      = vel
        self.prof_max = self.PROF_MAX
        self.estado   = ANZOL_IDLE
        self.visivel  = False

        self.agua_y = agua_y
        self.vara_x = vara_x
        self.vara_y = vara_y
        self.rect.center = (self.vara_x, self.vara_y)

    # ── Acoes ────────────────────────────────────────────────────────────────
    def lancar(self):
        """Inicia a descida. So funciona se o anzol estiver idle."""
        if self.estado == ANZOL_IDLE:
            self.rect.center = (self.vara_x, self.vara_y)
            self.estado  = ANZOL_DESCENDO
            self.visivel = True

    def puxar(self):
        """Inicia a subida. So funciona se o anzol estiver parado na agua."""
        if self.estado == ANZOL_NA_AGUA:
            self.estado = ANZOL_SUBINDO

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.estado == ANZOL_DESCENDO:
            self.rect.y += self.vel
            if self.rect.centery >= self.agua_y + self.prof_max:
                self.estado = ANZOL_NA_AGUA

        elif self.estado == ANZOL_SUBINDO:
            self.rect.y -= self.vel
            # Ao sair da agua, some imediatamente (evita sobrepor a vara)
            if self.rect.centery <= self.agua_y:
                self.rect.center = (self.vara_x, self.vara_y)
                self.estado  = ANZOL_IDLE
                self.visivel = False

    @property
    def ponto_topo(self):
        """Ponto superior do anzol — onde a linha se conecta."""
        return self.rect.midtop

    def draw(self, tela):
        if self.visivel:
            tela.blit(self.image, self.rect)


# ════════════════════════════════════════════════════════════════════════════
class Linha:
    """Linha de pesca desenhada entre a ponta da vara e o anzol."""

    COR       = (200, 200, 200)  # nylon transparente simulado
    ESPESSURA = 1

    def draw(self, tela, origem, destino):
        pygame.draw.line(tela, self.COR, origem, destino, self.ESPESSURA)


# ════════════════════════════════════════════════════════════════════════════
class Peixe(pygame.sprite.Sprite):
    """Peixe que nada na area subaquatica e pode ser atraido pelo anzol."""

    RAIO_ATRACAO  = 90   # distancia para começar a ir ao anzol
    RAIO_MORDIDA  = 22   # distancia para considerar mordida
    TEMPO_FUGA    = 120  # frames que o peixe fica fugindo antes de sumir
    VEL_MULT      = 1.0  # multiplicador de velocidade conforme dificuldade

    def __init__(self, dados, agua_y=LINHA_AGUA_PADRAO):
        super().__init__()
        self.nome      = dados["nome"]
        self.valor     = dados["valor"]
        self.vel_base  = dados["velocidade"] * Peixe.VEL_MULT
        self.prof_min  = dados["profundidade_min"]
        self.prof_max  = dados["profundidade_max"]

        # Escala proporcional ao valor do peixe
        escala = (70 + self.valor // 3, 38 + self.valor // 5)
        img = load_image("peixes", dados["imagem"], escala)
        img.set_colorkey(BRANCO)
        self._img_dir  = img                              # nadando para direita
        self._img_esq  = pygame.transform.flip(img, True, False)  # para esquerda

        self.estado    = PEIXE_NADANDO
        self.dir       = random.choice([-1, 1])           # -1 esq, +1 dir
        self.vel       = self.vel_base * self.dir
        self._fuga_timer = 0
        self.capturado = False

        self.image = self._img_dir if self.dir > 0 else self._img_esq
        self.rect  = self.image.get_rect()

        # Posicao inicial: fora da tela pelo lado oposto a direcao
        y = agua_y + random.randint(self.prof_min, self.prof_max)
        y = min(y, ALTURA - 30)
        if self.dir > 0:   # vem da esquerda
            self.rect.midright = (0, y)
        else:              # vem da direita
            self.rect.midleft  = (LARGURA, y)

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, anzol, isca_ocupada=False):
        if self.estado == PEIXE_NADANDO:
            self.rect.x += self.vel
            self._checar_atracoes(anzol, isca_ocupada)
            self._checar_bordas()

        elif self.estado == PEIXE_ATRAIDO:
            # Move em direcao ao anzol
            if anzol.visivel and anzol.estado == ANZOL_NA_AGUA:
                dx = anzol.rect.centerx - self.rect.centerx
                dy = anzol.rect.centery - self.rect.centery
                dist = max(1, (dx**2 + dy**2) ** 0.5)
                self.rect.x += int(self.vel_base * 1.5 * dx / dist)
                self.rect.y += int(self.vel_base * 0.8 * dy / dist)
                self._atualizar_flip(dx)
                # Chegou na mordida?
                if dist <= self.RAIO_MORDIDA:
                    self.estado = PEIXE_MORDENDO
                    self.rect.center = anzol.rect.center
            else:
                # Anzol foi retirado, volta a nadar
                self.estado = PEIXE_NADANDO

        elif self.estado == PEIXE_MORDENDO:
            # Fica parado no anzol
            if anzol.visivel:
                self.rect.center = anzol.rect.center
            else:
                self.estado = PEIXE_FUGINDO

        elif self.estado == PEIXE_CAPTURADO:
            if anzol.visivel:
                self.rect.center = anzol.rect.center
            else:
                self.capturado = True

        elif self.estado == PEIXE_FUGINDO:
            self.rect.x += self.vel_base * 2 * self.dir
            self._fuga_timer += 1
            if self._fuga_timer >= self.TEMPO_FUGA or self._saiu_da_tela():
                self.kill()

    def _checar_atracoes(self, anzol, isca_ocupada):
        if not anzol.visivel or anzol.estado != ANZOL_NA_AGUA:
            return
        if isca_ocupada:
            return
        dx = anzol.rect.centerx - self.rect.centerx
        dy = anzol.rect.centery - self.rect.centery
        dist = (dx**2 + dy**2) ** 0.5
        if dist <= self.RAIO_ATRACAO:
            self.estado = PEIXE_ATRAIDO

    def _checar_bordas(self):
        if self.rect.left > LARGURA + 10 or self.rect.right < -10:
            self.kill()

    def _atualizar_flip(self, dx):
        nova_dir = 1 if dx > 0 else -1
        if nova_dir != self.dir:
            self.dir = nova_dir
            self.vel = self.vel_base * self.dir
            self.image = self._img_dir if self.dir > 0 else self._img_esq

    def _saiu_da_tela(self):
        return self.rect.left > LARGURA + 50 or self.rect.right < -50

    @property
    def esta_mordendo(self):
        return self.estado == PEIXE_MORDENDO


# ════════════════════════════════════════════════════════════════════════════
def carregar_tipos_peixe():
    """Le config.ini e retorna lista de dicts com dados de cada tipo de peixe."""
    tipos = []
    num = config.getint("peixes", "num", fallback=0)
    for i in range(num):
        sec = f"peixe{i}"
        tipos.append({
            "nome":            config.get(sec, "nome"),
            "valor":           config.getint(sec, "valor"),
            "velocidade":      config.getint(sec, "velocidade"),
            "raridade":        config.getint(sec, "raridade"),
            "profundidade_min": config.getint(sec, "profundidade_min"),
            "profundidade_max": config.getint(sec, "profundidade_max"),
            "imagem":          config.get(sec, "imagem"),
            "barco_exclusivo": config.getboolean(sec, "barco_exclusivo", fallback=False),
        })
    return tipos


def escolher_tipo_peixe(tipos, barco_comprado=False):
    """Escolhe um tipo aleatorio ponderado pela raridade."""
    disponiveis = [t for t in tipos if not t.get("barco_exclusivo") or barco_comprado]
    if not disponiveis:
        return random.choice(tipos)
    pesos = [t["raridade"] for t in disponiveis]
    return random.choices(disponiveis, weights=pesos, k=1)[0]


def carregar_upgrades():
    """Le config.ini e retorna lista de dicts com dados de cada upgrade."""
    upgs = []
    num = config.getint("upgrades", "num", fallback=0)
    for i in range(num):
        sec = f"upgrade{i}"
        upgs.append({
            "id":           config.get(sec, "id"),
            "nome":         config.get(sec, "nome"),
            "descricao":    config.get(sec, "descricao"),
            "efeito":       config.get(sec, "efeito"),
            "valor_base":   config.getint(sec, "valor_base"),
            "custo_base":   config.getint(sec, "custo_base"),
            "maximo_nivel": config.getint(sec, "maximo_nivel"),
        })
    return upgs


# ════════════════════════════════════════════════════════════════════════════
class TextoFlutuante(pygame.sprite.Sprite):
    """Texto que sobe e desaparece na tela (ex: '+10 moedas')."""

    VEL_SUBIDA = 1.2
    DURACAO    = 80   # frames ate sumir

    def __init__(self, texto, pos, cor=(255, 215, 0)):
        super().__init__()
        fonte = pygame.font.SysFont("Arial", 22, bold=True)
        self.image   = fonte.render(texto, True, cor)
        self.rect    = self.image.get_rect(center=pos)
        self._timer  = 0
        self._y      = float(self.rect.y)

    def update(self):
        self._timer += 1
        self._y     -= self.VEL_SUBIDA
        self.rect.y  = int(self._y)
        # Fade out na segunda metade
        alpha = max(0, 255 - int(255 * self._timer / self.DURACAO))
        self.image.set_alpha(alpha)
        if self._timer >= self.DURACAO:
            self.kill()


# ════════════════════════════════════════════════════════════════════════════
class ParticulaSplash(pygame.sprite.Sprite):
    """Gotícula de água que espirra quando o anzol sai sem peixe."""

    def __init__(self, x, y):
        super().__init__()
        size = random.randint(2, 5)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.image.fill((200, 220, 255, 180))
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = random.uniform(-2.5, 2.5)
        self.vy = random.uniform(-4.0, -1.5)
        self._timer = 0
        self._duracao = random.randint(25, 45)

    def update(self):
        self._timer += 1
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.vy += 0.15
        alpha = max(0, 255 - int(255 * self._timer / self._duracao))
        self.image.set_alpha(alpha)
        if self._timer >= self._duracao:
            self.kill()


# ════════════════════════════════════════════════════════════════════════════
class Jogo:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.tela   = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption(TITULO)
        self.clock  = pygame.time.Clock()
        self.estado = ESTADO_MENU
        self.rodando = True

        self.fonte_titulo  = pygame.font.SysFont("Arial", 48, bold=True)
        self.fonte_normal  = pygame.font.SysFont("Arial", 24)
        self.fonte_pequena = pygame.font.SysFont("Arial", 18)

        # Objetos de cena (display ja ativo, pode carregar imagens)
        self.cenario  = Cenario()
        self.pescador = Pescador()
        vel_linha = config.getint("jogador", "velocidade_linha", fallback=3)
        self.anzol = Anzol(vel=vel_linha)
        self.linha = Linha()

        # Peixes
        self.tipos_peixe     = carregar_tipos_peixe()
        self.grupo_peixes    = pygame.sprite.Group()
        self._spawn_timer    = 0
        self._spawn_intervalo = 120
        self._max_peixes      = 5

        self._cooldown_timer = 0
        self._pull_vazio     = False
        self.grupo_particulas = pygame.sprite.Group()

        # Pontuacao
        self.moedas            = config.getint("jogador", "moedas_iniciais", fallback=0)
        self.peixes_capturados = 0
        self.meta_moedas       = config.getint("jogo", "meta_moedas", fallback=1000)

        # Textos flutuantes e exclamacao
        self.grupo_textos  = pygame.sprite.Group()
        self._fonte_excl   = pygame.font.SysFont("Arial", 36, bold=True)
        self._fonte_hud    = pygame.font.SysFont("Arial", 20, bold=True)

        # HUD — icones
        self._hud_moeda  = load_image("hud", "moeda.png",      (28, 28))
        self._hud_peixe  = load_image("hud", "peixe_icone.png", (28, 28))
        self._hud_excl   = load_image("hud", "exclamacao.png",  (32, 48))
        # Superficie de fundo do HUD (semi-transparente)
        self._hud_bg = pygame.Surface((260, 96), pygame.SRCALPHA)
        self._hud_bg.fill((0, 0, 0, 120))

        # Upgrades
        self.upgrades       = carregar_upgrades()
        self.upgrades_nivel = {u["id"]: 0 for u in self.upgrades}
        self._loja_selecao  = 0
        self.barco_comprado = False

        # Carrega save (ja aplica efeitos dos upgrades salvos)
        self._carregar_save()

        self._reset_msg_timer = 0
        self._tutorial_pagina  = 0

    # ── Posicoes dinamicas (dock vs barco) ────────────────────────────────────
    @property
    def _agua_y(self):
        return LINHA_AGUA_PADRAO - BOAT_AGUA_OFFSET if self.barco_comprado else LINHA_AGUA_PADRAO

    @property
    def _vara_ponta(self):
        if self.barco_comprado:
            return (BOAT_X + 165, self._agua_y - 170)
        return (VARA_PONTA_X, VARA_PONTA_Y)

    @property
    def _excl_pos(self):
        if self.barco_comprado:
            return (BOAT_X + 120, self._agua_y - 210)
        return (DOCK_X + 98, DOCK_Y - 118)

    def _atualizar_layout(self):
        """Recalcula posicoes do pescador e anzol conforme o cenario atual."""
        if self.barco_comprado:
            px = BOAT_X + 120
            py = self._agua_y - 25
            vx = BOAT_X + 165
            vy = self._agua_y - 170
        else:
            px = DOCK_X + 110
            py = DOCK_Y + 68
            vx = VARA_PONTA_X
            vy = VARA_PONTA_Y
        self.pescador.reposicionar(px, py)
        self.anzol.vara_x = vx
        self.anzol.vara_y = vy
        self.anzol.agua_y = self._agua_y
        self.anzol.rect.center = (vx, vy)

    # ── Loop principal ───────────────────────────────────────────────────────
    def run(self):
        while self.rodando:
            dt = self.clock.tick(FPS)

            if self.estado == ESTADO_MENU:
                self._menu_eventos()
                self._menu_draw()

            elif self.estado == ESTADO_JOGANDO:
                self._jogo_eventos()
                self._jogo_update(dt)
                self._jogo_draw()

            elif self.estado == ESTADO_PAUSA:
                self._pausa_eventos()
                self._pausa_draw()

            elif self.estado == ESTADO_TUTORIAL:
                self._tutorial_eventos()
                self._tutorial_draw()

            elif self.estado == ESTADO_LOJA:
                self._loja_eventos()
                self._loja_draw()

            elif self.estado == ESTADO_FIM:
                self._fim_eventos()
                self._fim_draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ── MENU ─────────────────────────────────────────────────────────────────
    def _menu_eventos(self):
        if self._reset_msg_timer > 0:
            self._reset_msg_timer -= 1
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self.estado = ESTADO_JOGANDO
                if evento.key == pygame.K_s:
                    self.estado = ESTADO_LOJA
                if evento.key == pygame.K_t:
                    self._tutorial_pagina = 0
                    self.estado = ESTADO_TUTORIAL
                if evento.key == pygame.K_r:
                    self._resetar_progresso()
                    self._reset_msg_timer = 90
                if evento.key == pygame.K_ESCAPE:
                    self.rodando = False

    def _menu_draw(self):
        self.cenario.draw(self.tela, LINHA_AGUA_PADRAO)
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.tela.blit(overlay, (0, 0))
        titulo = self.fonte_titulo.render(TITULO, True, (255, 215, 0))
        instrucao = self.fonte_normal.render("ENTER  - Jogar", True, BRANCO)
        instrucao2 = self.fonte_normal.render("S      - Loja de upgrades", True, BRANCO)
        instrucao3 = self.fonte_normal.render("T      - Tutorial", True, BRANCO)
        instrucao4 = self.fonte_normal.render("R      - Resetar progresso", True, (255, 180, 180))
        instrucao5 = self.fonte_normal.render("ESC    - Sair", True, BRANCO)
        self.tela.blit(titulo,     titulo.get_rect(center=(LARGURA//2, ALTURA//3)))
        self.tela.blit(instrucao,  instrucao.get_rect(center=(LARGURA//2, ALTURA//2)))
        self.tela.blit(instrucao2, instrucao2.get_rect(center=(LARGURA//2, ALTURA//2 + 40)))
        self.tela.blit(instrucao3, instrucao3.get_rect(center=(LARGURA//2, ALTURA//2 + 80)))
        self.tela.blit(instrucao4, instrucao4.get_rect(center=(LARGURA//2, ALTURA//2 + 120)))
        self.tela.blit(instrucao5, instrucao5.get_rect(center=(LARGURA//2, ALTURA//2 + 160)))

        if self._reset_msg_timer > 0:
            alpha = min(255, self._reset_msg_timer * 2)
            msg = self.fonte_normal.render("Progresso resetado!", True, (255, 100, 100))
            msg.set_alpha(alpha)
            self.tela.blit(msg, msg.get_rect(center=(LARGURA//2, ALTURA - 40)))

    # ── JOGANDO ───────────────────────────────────────────────────────────────
    def _jogo_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self._salvar()
                    self.estado = ESTADO_MENU
                if evento.key == pygame.K_p:
                    self.estado = ESTADO_PAUSA
                if evento.key == pygame.K_s:
                    self.estado = ESTADO_LOJA
                if evento.key == pygame.K_SPACE:
                    if self.anzol.estado == ANZOL_IDLE:
                        if self._cooldown_timer > 0:
                            continue
                        self.anzol.lancar()
                        self.pescador.set_estado(PESC_LANCANDO)
                        self._pull_vazio = False
                    elif self.anzol.estado == ANZOL_NA_AGUA:
                        capturado = None
                        for p in self.grupo_peixes:
                            if p.esta_mordendo:
                                capturado = p
                                break
                        if capturado:
                            capturado.estado = PEIXE_CAPTURADO
                            self._pull_vazio = False
                        else:
                            self._pull_vazio = True
                        self.anzol.puxar()
                        self.pescador.set_estado(PESC_PUXANDO)

    def _jogo_update(self, dt):
        self.anzol.update(dt)

        if self._cooldown_timer > 0:
            self._cooldown_timer -= 1

        if self.anzol.estado == ANZOL_IDLE:
            self.pescador.set_estado(PESC_IDLE)
            if self._pull_vazio:
                self._pull_vazio = False
                self._cooldown_timer = 120
                self.grupo_textos.add(TextoFlutuante("Nada...",
                    (self._vara_ponta[0] + 20, self._agua_y - 14), (180, 200, 255)))
                for _ in range(12):
                    self.grupo_particulas.add(
                        ParticulaSplash(self._vara_ponta[0] + 20, self._agua_y))
        elif self.anzol.estado == ANZOL_DESCENDO:
            self.pescador.set_estado(PESC_LANCANDO)

        # Spawn de peixes
        self._spawn_timer += 1
        if self._spawn_timer >= self._spawn_intervalo:
            self._spawn_timer = 0
            if len(self.grupo_peixes) < self._max_peixes:
                tipo = escolher_tipo_peixe(self.tipos_peixe, self.barco_comprado)
                self.grupo_peixes.add(Peixe(tipo, self._agua_y))

        # Atualiza todos os peixes — apenas um peixe persegue o anzol por vez
        isca_ocupada = any(p.estado in (PEIXE_ATRAIDO, PEIXE_MORDENDO) for p in self.grupo_peixes)
        for peixe in self.grupo_peixes:
            peixe.update(self.anzol, isca_ocupada)
            if peixe.estado in (PEIXE_ATRAIDO, PEIXE_MORDENDO):
                isca_ocupada = True

        # Finaliza peixes que subiram com o anzol ate a superficie
        for peixe in list(self.grupo_peixes):
            if peixe.capturado:
                self._capturar_peixe(peixe)

        # Atualiza textos flutuantes
        self.grupo_textos.update()
        self.grupo_particulas.update()

        # Verifica meta: moedas + todos os upgrades no maximo
        if self.moedas >= self.meta_moedas and self._todos_upgrades_maximos():
            self._salvar()
            self.estado = ESTADO_FIM

    def _capturar_peixe(self, peixe):
        """Registra captura, adiciona moedas e cria texto flutuante."""
        self.moedas            += peixe.valor
        self.peixes_capturados += 1
        pos = (peixe.rect.centerx, peixe.rect.top - 10)
        self.grupo_textos.add(TextoFlutuante(f"+{peixe.valor} moedas", pos))
        peixe.kill()
        self._salvar()

    def _jogo_draw(self):
        agua_y = self._agua_y
        barco_x = BOAT_X if self.barco_comprado else 0
        barco_y = agua_y - 65 - 15 if self.barco_comprado else 0
        self.cenario.draw(self.tela, agua_y, self.barco_comprado, barco_x, barco_y)

        if self.anzol.visivel:
            self.linha.draw(self.tela, self._vara_ponta, self.anzol.ponto_topo)

        self.pescador.draw(self.tela)
        self.grupo_peixes.draw(self.tela)
        self.grupo_particulas.draw(self.tela)
        self.anzol.draw(self.tela)

        self.grupo_textos.draw(self.tela)

        if any(p.esta_mordendo for p in self.grupo_peixes):
            self.tela.blit(self._hud_excl, self._excl_pos)

        # HUD — fundo semi-transparente
        self.tela.blit(self._hud_bg, (6, 6))

        # HUD — linha 1: icone moeda + contador / meta
        self.tela.blit(self._hud_moeda, (12, 12))
        txt_moedas = self._fonte_hud.render(f"{self.moedas}  /  {self.meta_moedas}", True, (255, 215, 0))
        self.tela.blit(txt_moedas, (46, 16))

        # HUD — linha 2: icone peixe + contador
        self.tela.blit(self._hud_peixe, (12, 44))
        txt_peixes = self._fonte_hud.render(f"{self.peixes_capturados} peixes", True, (200, 235, 255))
        self.tela.blit(txt_peixes, (46, 48))

        # HUD — linha 3: upgrades completos
        upg_completos = sum(1 for u in self.upgrades if self.upgrades_nivel.get(u["id"], 0) >= u["maximo_nivel"])
        upg_total = len(self.upgrades)
        cor_upg = (180, 255, 180) if upg_completos >= upg_total else (180, 220, 180)
        txt_upg = self._fonte_hud.render(f"Upgrades: {upg_completos}/{upg_total}", True, cor_upg)
        self.tela.blit(txt_upg, (12, 76))

        # HUD — barra de progresso de moedas (abaixo do box)
        barra_x, barra_y, barra_w, barra_h = 6, 106, 260, 6
        progresso = min(self.moedas / max(self.meta_moedas, 1), 1.0)
        pygame.draw.rect(self.tela, (60, 60, 60),   (barra_x, barra_y, barra_w, barra_h), border_radius=3)
        pygame.draw.rect(self.tela, (255, 215, 0),  (barra_x, barra_y, int(barra_w * progresso), barra_h), border_radius=3)
        pygame.draw.rect(self.tela, (180, 180, 180),(barra_x, barra_y, barra_w, barra_h), 1, border_radius=3)

        # HUD — barra de progresso de upgrades
        barra_y2 = barra_y + barra_h + 4
        upg_progresso = upg_completos / max(upg_total, 1)
        pygame.draw.rect(self.tela, (60, 60, 60),   (barra_x, barra_y2, barra_w, barra_h), border_radius=3)
        pygame.draw.rect(self.tela, (100, 180, 255),(barra_x, barra_y2, int(barra_w * upg_progresso), barra_h), border_radius=3)
        pygame.draw.rect(self.tela, (180, 180, 180),(barra_x, barra_y2, barra_w, barra_h), 1, border_radius=3)

        # Instrucao de controle (rodape)
        if self._cooldown_timer > 0:
            dica = f"Aguarde... ({self._cooldown_timer // 10 + 1})"
            cor_dica = (255, 180, 100)
        elif any(p.esta_mordendo for p in self.grupo_peixes):
            dica = "ESPACO = capturar!"
            cor_dica = (220, 50, 50)
        else:
            dica = {ANZOL_IDLE: "ESPACO = lancar", ANZOL_DESCENDO: "descendo...",
                    ANZOL_NA_AGUA: "ESPACO = puxar", ANZOL_SUBINDO: "puxando..."}.get(self.anzol.estado, "")
            cor_dica = (240, 240, 240)
        rodape_bg = pygame.Surface((LARGURA, 24), pygame.SRCALPHA)
        rodape_bg.fill((0, 0, 0, 130))
        self.tela.blit(rodape_bg, (0, ALTURA - 26))
        nivel_dif = sum(self.upgrades_nivel.values())
        txt = self._fonte_hud.render(
            f"{dica}  |  Nv. {nivel_dif}  |  S = Loja  |  P = Pausa  |  ESC = Menu", True, cor_dica)
        self.tela.blit(txt, txt.get_rect(center=(LARGURA // 2, ALTURA - 14)))

    # ── TUTORIAL ─────────────────────────────────────────────────────────────
    def _tutorial_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_t):
                    self.estado = ESTADO_MENU
                elif evento.key == pygame.K_RIGHT:
                    self._tutorial_pagina = min(1, self._tutorial_pagina + 1)
                elif evento.key == pygame.K_LEFT:
                    self._tutorial_pagina = max(0, self._tutorial_pagina - 1)

    def _tutorial_draw(self):
        self.cenario.draw(self.tela, LINHA_AGUA_PADRAO)
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.tela.blit(overlay, (0, 0))

        titulo = self.fonte_titulo.render("Como Jogar", True, (255, 215, 0))
        self.tela.blit(titulo, titulo.get_rect(center=(LARGURA // 2, 50)))

        if self._tutorial_pagina == 0:
            self._tutorial_pagina_controles()
        else:
            self._tutorial_pagina_objetivo()

        # Indicador de pagina
        pg = self.fonte_pequena.render(
            f"<  {self._tutorial_pagina + 1}/2  >", True, (180, 180, 180))
        self.tela.blit(pg, pg.get_rect(center=(LARGURA // 2, ALTURA - 50)))

        # Rodape
        rodape = self.fonte_pequena.render(
            "← → = navegar  |  ESC ou T = voltar", True, (160, 160, 160))
        self.tela.blit(rodape, rodape.get_rect(center=(LARGURA // 2, ALTURA - 18)))

    def _tutorial_pagina_controles(self):
        f = self.fonte_normal
        p = self.fonte_pequena
        y = 100
        gap = 28

        sec = f.render("Controles", True, (100, 200, 255))
        self.tela.blit(sec, (80, y)); y += gap + 4

        for tecla, acao in [
            ("ESPACO", "Lancar o anzol / Puxar quando peixe morder"),
            ("S",      "Abrir a loja de upgrades"),
            ("P",      "Pausar o jogo"),
            ("ESC",    "Salvar e voltar ao menu"),
        ]:
            txt = p.render(f"  {tecla:<12} {acao}", True, BRANCO)
            self.tela.blit(txt, (80, y)); y += gap

        y += 10
        sec2 = f.render("Como pescar", True, (100, 200, 255))
        self.tela.blit(sec2, (80, y)); y += gap + 4

        passos = [
            "1. Pressione ESPACO para lancar o anzol na agua.",
            "2. Aguarde um peixe se aproximar do anzol.",
            "3. Quando aparecer \"!\" vermelho, o peixe mordeu!",
            "4. Pressione ESPACO novamente para fisgar e puxar.",
            "5. Peixe capturado = moedas no bolso!",
        ]
        for txt in passos:
            linha = p.render(txt, True, BRANCO)
            self.tela.blit(linha, (80, y)); y += gap

    def _tutorial_pagina_objetivo(self):
        f = self.fonte_normal
        p = self.fonte_pequena
        y = 100
        gap = 28

        sec = f.render("Upgrades (Loja)", True, (100, 200, 255))
        self.tela.blit(sec, (80, y)); y += gap + 4

        upgs = [
            ("Vara Melhor",     "Anzol desce mais fundo, alcanca peixes raros"),
            ("Isca Premium",    "Peixes sao atraidos de mais longe"),
            ("Carretilha Rapida","Linha desce e sobe mais rapido"),
            ("Anzol Grande",    "Maior area de captura"),
            ("Barco",           "Leva voce ao mar aberto com peixes exclusivos!"),
        ]
        for nome, desc in upgs:
            linha = p.render(f"  {nome:<20} {desc}", True, BRANCO)
            self.tela.blit(linha, (80, y)); y += gap

        y += 10
        sec2 = f.render("Objetivo", True, (100, 200, 255))
        self.tela.blit(sec2, (80, y)); y += gap + 4

        obj = [
            "Junte 1000 moedas E compre todos os 5 upgrades",
            "no nivel maximo para zerar o jogo!",
            "",
            "Dica: a cada upgrade comprado, o jogo fica",
            "mais dificil (peixes mais rapidos e numerosos).",
        ]
        for txt in obj:
            linha = p.render(txt, True, BRANCO)
            self.tela.blit(linha, (80, y)); y += gap

    # ── PAUSA ────────────────────────────────────────────────────────────────
    def _pausa_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_p:
                    self.estado = ESTADO_JOGANDO
                if evento.key == pygame.K_ESCAPE:
                    self._salvar()
                    self.estado = ESTADO_MENU

    def _pausa_draw(self):
        self._jogo_draw()
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.tela.blit(overlay, (0, 0))
        txt = self.fonte_titulo.render("PAUSADO", True, (255, 215, 0))
        sub = self.fonte_normal.render("P = continuar  |  ESC = Menu", True, BRANCO)
        self.tela.blit(txt, txt.get_rect(center=(LARGURA // 2, ALTURA // 2 - 20)))
        self.tela.blit(sub, sub.get_rect(center=(LARGURA // 2, ALTURA // 2 + 30)))

    # ── LOJA ─────────────────────────────────────────────────────────────────
    def _loja_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_s):
                    self.estado = ESTADO_JOGANDO
                elif evento.key == pygame.K_UP:
                    self._loja_selecao = (self._loja_selecao - 1) % len(self.upgrades)
                elif evento.key == pygame.K_DOWN:
                    self._loja_selecao = (self._loja_selecao + 1) % len(self.upgrades)
                elif evento.key == pygame.K_RETURN:
                    self._comprar_upgrade(self.upgrades[self._loja_selecao])

    def _comprar_upgrade(self, upg):
        """Tenta comprar o upgrade selecionado."""
        uid    = upg["id"]
        nivel  = self.upgrades_nivel[uid]
        maximo = upg["maximo_nivel"]
        if nivel >= maximo:
            return  # ja no maximo
        custo = upg["custo_base"] * (nivel + 1)
        if self.moedas < custo:
            return  # sem moedas
        self.moedas -= custo
        self.upgrades_nivel[uid] = nivel + 1
        self._aplicar_efeito(upg, nivel + 1)
        self._atualizar_dificuldade()
        # Texto flutuante de compra
        pos = (LARGURA // 2, ALTURA // 2)
        self.grupo_textos.add(TextoFlutuante(f"{upg['nome']} Nv.{nivel+1}!", pos, (100, 255, 100)))
        self._salvar()

    def _todos_upgrades_maximos(self):
        for upg in self.upgrades:
            if self.upgrades_nivel.get(upg["id"], 0) < upg["maximo_nivel"]:
                return False
        return True

    def _aplicar_efeito(self, upg, novo_nivel):
        """Aplica o efeito do upgrade ao jogo."""
        efeito = upg["efeito"]
        valor  = upg["valor_base"]
        if efeito == "profundidade":
            limite = ALTURA - self._agua_y - 20
            self.anzol.prof_max = min(self.anzol.prof_max + valor, limite)
        elif efeito == "velocidade_linha":
            self.anzol.vel += valor
        elif efeito == "chance_mordida":
            Peixe.RAIO_ATRACAO = min(Peixe.RAIO_ATRACAO + valor, 180)
        elif efeito == "tamanho_anzol":
            Peixe.RAIO_MORDIDA = min(Peixe.RAIO_MORDIDA + 8, 50)
        elif efeito == "cenario":
            if not self.barco_comprado:
                self.barco_comprado = True
        self._atualizar_layout()
        self._atualizar_dificuldade()

    def _atualizar_dificuldade(self):
        nivel_total = sum(self.upgrades_nivel.values())
        self._spawn_intervalo = max(40, 120 - nivel_total * 7)
        self._max_peixes      = min(9, 5 + nivel_total // 3)
        Peixe.VEL_MULT        = 1.0 + nivel_total * 0.05

    # ── Save / Load ──────────────────────────────────────────────────────────
    def _resetar_progresso(self):
        """Zera moedas, peixes, upgrades e apaga o save."""
        self.moedas            = 0
        self.peixes_capturados = 0
        self.upgrades_nivel    = {uid: 0 for uid in self.upgrades_nivel}
        self.barco_comprado    = False
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        self._reaplicar_upgrades()

    def _salvar(self):
        """Persiste progresso em save.ini."""
        save = configparser.ConfigParser()
        save["jogador"] = {
            "moedas":            str(self.moedas),
            "peixes_capturados": str(self.peixes_capturados),
        }
        save["upgrades"] = {uid: str(n) for uid, n in self.upgrades_nivel.items()}
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            save.write(f)

    def _carregar_save(self):
        """Restaura progresso de save.ini, se existir."""
        if not os.path.exists(SAVE_FILE):
            return
        save = configparser.ConfigParser()
        save.read(SAVE_FILE, encoding="utf-8")
        if "jogador" in save:
            self.moedas            = save.getint("jogador", "moedas",            fallback=0)
            self.peixes_capturados = save.getint("jogador", "peixes_capturados", fallback=0)
        if "upgrades" in save:
            for uid in self.upgrades_nivel:
                self.upgrades_nivel[uid] = save.getint("upgrades", uid, fallback=0)
        self._reaplicar_upgrades()

    def _reaplicar_upgrades(self):
        """Reseta variaveis de efeito e reaplica todos os niveis salvos."""
        Peixe.RAIO_ATRACAO = 90
        Peixe.RAIO_MORDIDA = 22
        self.anzol.prof_max = Anzol.PROF_MAX
        self.anzol.vel      = config.getint("jogador", "velocidade_linha", fallback=3)
        self.barco_comprado = False
        for upg in self.upgrades:
            for n in range(1, self.upgrades_nivel[upg["id"]] + 1):
                self._aplicar_efeito(upg, n)
        self._atualizar_layout()

    def _loja_draw(self):
        self.tela.fill((50, 30, 10))

        # Titulo
        titulo = self.fonte_titulo.render("Loja de Upgrades", True, (255, 215, 0))
        self.tela.blit(titulo, titulo.get_rect(center=(LARGURA // 2, 38)))

        # Moedas centralizadas
        moedas_txt = self.fonte_normal.render(f"Moedas disponíveis:  {self.moedas}", True, (255, 215, 0))
        self.tela.blit(moedas_txt, moedas_txt.get_rect(center=(LARGURA // 2, 74)))

        # Separador
        pygame.draw.line(self.tela, (120, 80, 30), (40, 90), (LARGURA - 40, 90), 1)

        # Itens — distribuição dinâmica
        margem_x = 40
        y0       = 98
        gap      = 8                                     # espaco entre itens
        n        = len(self.upgrades)
        linha_h  = (ALTURA - 30 - y0) // n              # ~94 px por item
        rect_h   = linha_h - gap

        for i, upg in enumerate(self.upgrades):
            uid    = upg["id"]
            nivel  = self.upgrades_nivel[uid]
            maximo = upg["maximo_nivel"]
            custo  = upg["custo_base"] * (nivel + 1)
            sel    = (i == self._loja_selecao)

            ry = y0 + i * linha_h
            rect_item = pygame.Rect(margem_x, ry, LARGURA - 2 * margem_x, rect_h)

            # Fundo
            cor_fundo = (110, 72, 28) if sel else (72, 46, 14)
            pygame.draw.rect(self.tela, cor_fundo, rect_item, border_radius=8)
            if sel:
                pygame.draw.rect(self.tela, (255, 215, 0), rect_item, 2, border_radius=8)

            # Linha 1 — Nome  [Nv. x/max]
            nivel_str = f"Nv. {nivel}/{maximo}"
            nome_surf = self.fonte_normal.render(f"{upg['nome']}  [{nivel_str}]", True, BRANCO)
            self.tela.blit(nome_surf, (rect_item.x + 14, rect_item.y + 8))

            # Linha 2 — Descricao
            desc_surf = self.fonte_pequena.render(upg["descricao"], True, (200, 200, 200))
            self.tela.blit(desc_surf, (rect_item.x + 14, rect_item.y + rect_h // 2 - 4))

            # Linha 3 — Status (alinhado a direita)
            if nivel >= maximo:
                status_txt = "JA MAXIMO"
                cor_status = (100, 255, 100)
            elif self.moedas >= custo:
                status_txt = f"ENTER = comprar  ({custo} moedas)"
                cor_status = (255, 215, 0)
            else:
                status_txt = f"Precisa  {custo} moedas"
                cor_status = (220, 80, 80)
            status_surf = self.fonte_normal.render(status_txt, True, cor_status)
            self.tela.blit(status_surf, (rect_item.right - status_surf.get_width() - 14,
                                         rect_item.bottom - status_surf.get_height() - 8))

        # Textos flutuantes sobre a loja
        self.grupo_textos.draw(self.tela)
        self.grupo_textos.update()

        # Rodape
        voltar = self.fonte_pequena.render(
            "↑↓ = navegar  |  ENTER = comprar  |  S ou ESC = voltar",
            True, (160, 160, 160))
        self.tela.blit(voltar, voltar.get_rect(center=(LARGURA // 2, ALTURA - 14)))

    # ── FIM ──────────────────────────────────────────────────────────────────
    def _fim_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self._resetar_progresso()
                    self.estado = ESTADO_JOGANDO
                if evento.key == pygame.K_ESCAPE:
                    self._resetar_progresso()
                    self.estado = ESTADO_MENU

    def _fim_draw(self):
        self.cenario.draw(self.tela, LINHA_AGUA_PADRAO)
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.tela.blit(overlay, (0, 0))
        msg = self.fonte_titulo.render("Parabens! Voce zerou o Pesqueiro!", True, (255, 215, 0))
        linha1 = self.fonte_normal.render(
            f"Moedas: {self.moedas}  |  Peixes: {self.peixes_capturados}  |  Upgrades: completos",
            True, (200, 235, 255))
        sub = self.fonte_normal.render("ENTER - Jogar de novo  |  ESC - Menu", True, BRANCO)
        self.tela.blit(msg, msg.get_rect(center=(LARGURA//2, ALTURA//2 - 50)))
        self.tela.blit(linha1, linha1.get_rect(center=(LARGURA//2, ALTURA//2)))
        self.tela.blit(sub, sub.get_rect(center=(LARGURA//2, ALTURA//2 + 40)))


# ── Iniciar ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Jogo().run()
