import copy

class Piece:
    EMPTY = 0
    BLUE_FRONT = 1
    RED_BACK = 2
    YELLOW_FRONT = 3
    YELLOW_BACK = 4

    @staticmethod
    def is_front(p):
        return p in (Piece.BLUE_FRONT, Piece.YELLOW_FRONT)

    @staticmethod
    def is_back(p):
        return p in (Piece.RED_BACK, Piece.YELLOW_BACK)

    @staticmethod
    def is_special(p):
        return p in (Piece.YELLOW_FRONT, Piece.YELLOW_BACK)

    @staticmethod
    def flip(p):
        if p == Piece.BLUE_FRONT:
            return Piece.RED_BACK
        elif p == Piece.RED_BACK:
            return Piece.BLUE_FRONT
        elif p == Piece.YELLOW_FRONT:
            return Piece.YELLOW_BACK
        elif p == Piece.YELLOW_BACK:
            return Piece.YELLOW_FRONT
        return p

class GameState:
    INITIAL = "INITIAL"
    PLAYING = "PLAYING"
    CHOOSING_LINE = "CHOOSING_LINE"
    FINISHED = "FINISHED"

class GameRules:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[Piece.EMPTY for _ in range(4)] for _ in range(4)]
        self.turn = 'player1' # player1 starts
        self.state = GameState.INITIAL
        self.score = {'player1': 0, 'player2': 0}
        self.special_captured = {'player1': 0, 'player2': 0}
        self.initial_pieces_placed = 0
        self.history = []
        self.pending_lines = []
        self.winner = None
        self.win_reason = ""
        self.last_move = None

    def get_state(self):
        return {
            'board': self.board,
            'turn': self.turn,
            'state': self.state,
            'score': self.score,
            'special_captured': self.special_captured,
            'pending_lines': self.pending_lines,
            'winner': self.winner,
            'win_reason': self.win_reason,
            'last_move': self.last_move
        }

    def save_state(self):
        self.history.append({
            'board': copy.deepcopy(self.board),
            'turn': self.turn,
            'state': self.state,
            'score': copy.deepcopy(self.score),
            'special_captured': copy.deepcopy(self.special_captured),
            'initial_pieces_placed': self.initial_pieces_placed,
            'pending_lines': copy.deepcopy(self.pending_lines),
            'last_move': self.last_move
        })

    def undo(self):
        if self.history:
            last = self.history.pop()
            self.board = last['board']
            self.turn = last['turn']
            self.state = last['state']
            self.score = last['score']
            self.special_captured = last['special_captured']
            self.initial_pieces_placed = last['initial_pieces_placed']
            self.pending_lines = last['pending_lines']
            self.last_move = last.get('last_move')
            self.winner = None
            self.win_reason = ""
            return True
        return False

    def make_move(self, x, y, face):
        if self.state not in (GameState.INITIAL, GameState.PLAYING):
            return False
        if self.board[x][y] != Piece.EMPTY:
            return False
            
        self.save_state()

        if self.state == GameState.INITIAL:
            # Player 1 places 2 yellow pieces
            if face == 'front':
                piece = Piece.YELLOW_FRONT
            else:
                piece = Piece.YELLOW_BACK
                
            self.board[x][y] = piece
            self.last_move = {'x': x, 'y': y}
            self.initial_pieces_placed += 1
            if self.initial_pieces_placed == 2:
                self.state = GameState.PLAYING
                self.turn = 'player2'
            # No flipping during initial
            return True

        elif self.state == GameState.PLAYING:
            if face == 'front':
                piece = Piece.BLUE_FRONT
            else:
                piece = Piece.RED_BACK
                
            self.board[x][y] = piece
            self.last_move = {'x': x, 'y': y}
            self.flip_neighbors(x, y)
            
            lines = self.find_lines()
            if len(lines) == 1:
                self.clear_line(lines[0])
                self.check_win()
                if self.state == GameState.PLAYING:
                    self.turn = 'player2' if self.turn == 'player1' else 'player1'
            elif len(lines) > 1:
                self.pending_lines = lines
                self.state = GameState.CHOOSING_LINE
            else:
                self.turn = 'player2' if self.turn == 'player1' else 'player1'
            return True
            
        return False

    def choose_line(self, line_index):
        if self.state != GameState.CHOOSING_LINE:
            return False
        if 0 <= line_index < len(self.pending_lines):
            line = self.pending_lines[line_index]
            self.clear_line(line)
            self.pending_lines = []
            self.check_win()
            if self.state != GameState.FINISHED:
                self.state = GameState.PLAYING
                self.turn = 'player2' if self.turn == 'player1' else 'player1'
            return True
        return False

    def flip_neighbors(self, x, y):
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 4 and 0 <= ny < 4:
                if self.board[nx][ny] != Piece.EMPTY:
                    self.board[nx][ny] = Piece.flip(self.board[nx][ny])

    def find_lines(self):
        lines = []
        # Check rows
        for i in range(4):
            line = [(i, j) for j in range(4)]
            if self.is_valid_line(line):
                lines.append(line)
        # Check cols
        for j in range(4):
            line = [(i, j) for i in range(4)]
            if self.is_valid_line(line):
                lines.append(line)
        # Diagonals
        diag1 = [(i, i) for i in range(4)]
        if self.is_valid_line(diag1):
            lines.append(diag1)
        diag2 = [(i, 3-i) for i in range(4)]
        if self.is_valid_line(diag2):
            lines.append(diag2)
            
        return lines

    def is_valid_line(self, coords):
        pieces = [self.board[x][y] for x, y in coords]
        if any(p == Piece.EMPTY for p in pieces):
            return False
        all_front = all(Piece.is_front(p) for p in pieces)
        all_back = all(Piece.is_back(p) for p in pieces)
        return all_front or all_back

    def clear_line(self, line):
        for x, y in line:
            p = self.board[x][y]
            if Piece.is_special(p):
                self.special_captured[self.turn] += 1
            self.board[x][y] = Piece.EMPTY
        self.score[self.turn] += 1

    def check_win(self):
        p1_spec = self.special_captured['player1']
        p2_spec = self.special_captured['player2']
        p1_score = self.score['player1']
        p2_score = self.score['player2']
        
        if p1_spec == 2:
            self.state = GameState.FINISHED
            self.winner = 'player1'
            self.win_reason = '收走2個特殊棋'
        elif p2_spec == 2:
            self.state = GameState.FINISHED
            self.winner = 'player2'
            self.win_reason = '收走2個特殊棋'
        elif p1_spec == 1 and p2_spec == 1:
            if p1_score >= p2_score + 2:
                self.state = GameState.FINISHED
                self.winner = 'player1'
                self.win_reason = '各收1個特殊棋，且分數相差2分以上'
            elif p2_score >= p1_score + 2:
                self.state = GameState.FINISHED
                self.winner = 'player2'
                self.win_reason = '各收1個特殊棋，且分數相差2分以上'
