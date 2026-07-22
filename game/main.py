import queue
import threading
import pygame
from game.npc_client import generate_npc_response

WIDTH, HEIGHT = 960, 600
FPS = 60
PLAYER_SPEED = 4
INTERACT_RADIUS = 90

BG_COLOR = (13, 15, 26)
GRID_COLOR = (26, 30, 48)
PLAYER_COLOR = (56, 217, 255)
NPC_COLOR = (255, 66, 161)
TEXT_COLOR = (230, 235, 245)
DIM_TEXT_COLOR = (150, 158, 179)
PANEL_COLOR = (20, 22, 38)
PANEL_BORDER = (255, 66, 161)

NPC_NAME = 'john_doe'
NPC_PROMPT = 'Greet the player who just walked up to your stall in the Neon District market.'


class NpcInteraction:
    """Runs the Devinci NPC API call on a background thread so the game loop never blocks."""

    IDLE, LOADING, RESULT, ERROR = 'idle', 'loading', 'result', 'error'

    def __init__(self) -> None:
        self.state = self.IDLE
        self.text = ''
        self._results: queue.Queue = queue.Queue()

    def start(self) -> None:
        if self.state == self.LOADING:
            return
        self.state = self.LOADING
        self.text = ''
        threading.Thread(target=self._call_api, daemon=True).start()

    def _call_api(self) -> None:
        try:
            dialogue = generate_npc_response(NPC_NAME, NPC_PROMPT)
            self._results.put((self.RESULT, dialogue))
        except Exception as exc:
            self._results.put((self.ERROR, f'NPC did not respond: {exc}'))

    def poll(self) -> None:
        try:
            state, text = self._results.get_nowait()
        except queue.Empty:
            return
        self.state = state
        self.text = text

    def close(self) -> None:
        self.state = self.IDLE
        self.text = ''


def draw_background(screen: pygame.Surface) -> None:
    screen.fill(BG_COLOR)
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y))


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_dialogue_panel(screen: pygame.Surface, font: pygame.font.Font, title_font: pygame.font.Font,
                         interaction: NpcInteraction) -> None:
    panel_rect = pygame.Rect(40, HEIGHT - 200, WIDTH - 80, 160)
    pygame.draw.rect(screen, PANEL_COLOR, panel_rect, border_radius=10)
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, width=2, border_radius=10)

    title = title_font.render('Neon District Merchant', True, NPC_COLOR)
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 14))

    if interaction.state == NpcInteraction.LOADING:
        body = 'Contacting Devinci NPC service...'
        color = DIM_TEXT_COLOR
    elif interaction.state == NpcInteraction.ERROR:
        body = interaction.text
        color = (255, 120, 120)
    else:
        body = interaction.text or '...'
        color = TEXT_COLOR

    for i, line in enumerate(wrap_text(font, body, panel_rect.width - 40)):
        rendered = font.render(line, True, color)
        screen.blit(rendered, (panel_rect.x + 20, panel_rect.y + 50 + i * 24))

    hint = font.render('Press Enter to close', True, DIM_TEXT_COLOR)
    screen.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 28))


def main() -> None:
    pygame.init()
    pygame.display.set_caption('Neon District — NPC Encounter')
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont('consolas', 18)
    title_font = pygame.font.SysFont('consolas', 20, bold=True)

    player = pygame.Rect(WIDTH // 4, HEIGHT // 2, 32, 32)
    npc = pygame.Rect(WIDTH * 3 // 4, HEIGHT // 2, 36, 36)

    interaction = NpcInteraction()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if interaction.state == NpcInteraction.IDLE:
                    if pygame.Vector2(player.center).distance_to(npc.center) <= INTERACT_RADIUS:
                        interaction.start()
                else:
                    interaction.close()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        if interaction.state == NpcInteraction.IDLE:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            player.x = max(0, min(WIDTH - player.width, player.x + dx * PLAYER_SPEED))
            player.y = max(0, min(HEIGHT - player.height, player.y + dy * PLAYER_SPEED))

        interaction.poll()

        draw_background(screen)

        in_range = pygame.Vector2(player.center).distance_to(npc.center) <= INTERACT_RADIUS
        pygame.draw.circle(screen, GRID_COLOR, npc.center, INTERACT_RADIUS, width=1)
        pygame.draw.rect(screen, NPC_COLOR, npc, border_radius=6)
        pygame.draw.rect(screen, PLAYER_COLOR, player, border_radius=6)

        if interaction.state == NpcInteraction.IDLE and in_range:
            prompt = font.render('Press Enter to talk', True, TEXT_COLOR)
            screen.blit(prompt, (npc.centerx - prompt.get_width() // 2, npc.top - 28))

        if interaction.state != NpcInteraction.IDLE:
            draw_dialogue_panel(screen, font, title_font, interaction)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == '__main__':
    main()
