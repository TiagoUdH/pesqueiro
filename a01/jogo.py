import pygame
import sys
import os
import configparser

# ── Diretorios ──────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.join(BASE_DIR, "..")
IMG_DIR     = os.path.join(ROOT_DIR, "imagens")
SND_DIR     = os.path.join(ROOT_DIR, "sons")
CONFIG_FILE = os.path.join(ROOT_DIR, "config.ini")

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

# ── Estados do pescador ──────────────────────────────────────────────────────
PESC_IDLE     = "idle"
PESC_LANCANDO = "lancando"
PESC_PUXANDO  = "puxando"

# ── Estados do anzol ────────────────────────────────────────────────────────
ANZOL_IDLE     = "idle"      # nao lancado, invisivel
ANZOL_DESCENDO = "descendo"  # descendo na agua
ANZOL_NA_AGUA  = "na_agua"   # parado aguardando
ANZOL_SUBINDO  = "subindo"   # voltando para cima

# Ponta da vara do pescador (origem da linha)
# Calculado com base na posicao do pescador (DOCK_X+110, DOCK_Y+68) e escala 110x165
VARA_PONTA_X = DOCK_X + 148   # proximo ao topo direito do sprite do pescador
VARA_PONTA_Y = DOCK_Y - 80


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
    """Renderiza fundo, agua e dock."""

    def __init__(self):
        # Fundo (ceu + terra): escalonado para cobrir a area acima da agua
        self.fundo = load_image("cenario", "fundo.png", (LARGURA, LINHA_AGUA))

        # Agua (area subaquatica): cobre do LINHA_AGUA ate o final da tela
        self.agua = load_image("cenario", "agua.png", (LARGURA, ALTURA - LINHA_AGUA))

        # Deck de madeira posicionado na beira da agua
        self.dock = load_image("cenario", "dock.png", (220, 110))
        self.dock.set_colorkey(BRANCO)  # remove fundo branco

    def draw(self, tela):
        tela.blit(self.fundo, (0, 0))
        tela.blit(self.agua,  (0, LINHA_AGUA))
        tela.blit(self.dock,  (DOCK_X, DOCK_Y))


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

    def draw(self, tela):
        tela.blit(self.image, self.rect)


# ════════════════════════════════════════════════════════════════════════════
class Anzol(pygame.sprite.Sprite):
    """Anzol que desce e sobe na agua."""

    ESCALA    = (38, 55)
    PROF_MAX  = 200   # profundidade maxima padrao (pixels abaixo de LINHA_AGUA)

    def __init__(self, vel=3):
        super().__init__()
        img = load_image("peixes", "anzol.png", self.ESCALA)
        img.set_colorkey(BRANCO)
        self.image = img
        self.rect  = self.image.get_rect()

        self.vel      = vel
        self.prof_max = self.PROF_MAX
        self.estado   = ANZOL_IDLE
        self.visivel  = False

        self.rect.center = (VARA_PONTA_X, VARA_PONTA_Y)

    # ── Acoes ────────────────────────────────────────────────────────────────
    def lancar(self):
        """Inicia a descida. So funciona se o anzol estiver idle."""
        if self.estado == ANZOL_IDLE:
            self.rect.center = (VARA_PONTA_X, VARA_PONTA_Y)
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
            if self.rect.centery >= LINHA_AGUA + self.prof_max:
                self.estado = ANZOL_NA_AGUA

        elif self.estado == ANZOL_SUBINDO:
            self.rect.y -= self.vel
            # Ao sair da agua, some imediatamente (evita sobrepor a vara)
            if self.rect.centery <= LINHA_AGUA:
                self.rect.center = (VARA_PONTA_X, VARA_PONTA_Y)
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
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self.estado = ESTADO_JOGANDO
                if evento.key == pygame.K_ESCAPE:
                    self.rodando = False

    def _menu_draw(self):
        self.tela.fill(AZUL_CEU)
        titulo = self.fonte_titulo.render(TITULO, True, MARROM)
        instrucao = self.fonte_normal.render("ENTER  - Jogar", True, PRETO)
        instrucao2 = self.fonte_normal.render("S      - Loja de upgrades", True, PRETO)
        instrucao3 = self.fonte_normal.render("ESC    - Sair", True, PRETO)
        self.tela.blit(titulo,     titulo.get_rect(center=(LARGURA//2, ALTURA//3)))
        self.tela.blit(instrucao,  instrucao.get_rect(center=(LARGURA//2, ALTURA//2)))
        self.tela.blit(instrucao2, instrucao2.get_rect(center=(LARGURA//2, ALTURA//2 + 40)))
        self.tela.blit(instrucao3, instrucao3.get_rect(center=(LARGURA//2, ALTURA//2 + 80)))

    # ── JOGANDO ───────────────────────────────────────────────────────────────
    def _jogo_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.estado = ESTADO_MENU
                if evento.key == pygame.K_s:
                    self.estado = ESTADO_LOJA
                if evento.key == pygame.K_SPACE:
                    if self.anzol.estado == ANZOL_IDLE:
                        self.anzol.lancar()
                        self.pescador.set_estado(PESC_LANCANDO)
                    elif self.anzol.estado == ANZOL_NA_AGUA:
                        self.anzol.puxar()
                        self.pescador.set_estado(PESC_PUXANDO)

    def _jogo_update(self, dt):
        self.anzol.update(dt)
        # Quando anzol volta ao idle, pescador volta a descansar
        if self.anzol.estado == ANZOL_IDLE:
            self.pescador.set_estado(PESC_IDLE)
        # Quando anzol esta descendo, pescador fica na pose de lancando
        elif self.anzol.estado == ANZOL_DESCENDO:
            self.pescador.set_estado(PESC_LANCANDO)

    def _jogo_draw(self):
        # Cenario: fundo + agua + dock
        self.cenario.draw(self.tela)

        # Linha de pesca (desenhada antes do anzol para ficar atras)
        if self.anzol.visivel:
            self.linha.draw(self.tela, (VARA_PONTA_X, VARA_PONTA_Y), self.anzol.ponto_topo)

        # Pescador e anzol
        self.pescador.draw(self.tela)
        self.anzol.draw(self.tela)

        # Instrucoes temporarias (remover quando HUD estiver pronto)
        estado_txt = {
            ANZOL_IDLE:     "ESPACO = lancar",
            ANZOL_DESCENDO: "linha descendo...",
            ANZOL_NA_AGUA:  "ESPACO = puxar!",
            ANZOL_SUBINDO:  "puxando...",
        }.get(self.anzol.estado, "")
        txt = self.fonte_pequena.render(f"{estado_txt}  |  S = Loja  |  ESC = Menu", True, PRETO)
        self.tela.blit(txt, (10, 10))

    # ── LOJA ─────────────────────────────────────────────────────────────────
    def _loja_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_s):
                    self.estado = ESTADO_JOGANDO

    def _loja_draw(self):
        self.tela.fill(MARROM)
        titulo = self.fonte_titulo.render("Loja de Upgrades", True, BRANCO)
        voltar = self.fonte_normal.render("ESC ou S - Voltar ao jogo", True, BRANCO)
        self.tela.blit(titulo, titulo.get_rect(center=(LARGURA//2, 60)))
        self.tela.blit(voltar, voltar.get_rect(center=(LARGURA//2, ALTURA - 40)))

    # ── FIM ──────────────────────────────────────────────────────────────────
    def _fim_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self.estado = ESTADO_MENU
                if evento.key == pygame.K_ESCAPE:
                    self.rodando = False

    def _fim_draw(self):
        self.tela.fill(PRETO)
        msg = self.fonte_titulo.render("Voce e o melhor pescador!", True, (255, 215, 0))
        sub = self.fonte_normal.render("ENTER - Menu  |  ESC - Sair", True, BRANCO)
        self.tela.blit(msg, msg.get_rect(center=(LARGURA//2, ALTURA//2 - 30)))
        self.tela.blit(sub, sub.get_rect(center=(LARGURA//2, ALTURA//2 + 30)))


# ── Iniciar ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Jogo().run()
