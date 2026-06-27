##############################################################
# 4x4 翻轉棋 AI 自我對弈訓練腳本 v2 (Google Colab 專用)
# 使用方式：在 Colab 新增一個 cell，貼上此程式碼即可執行
# 先在第一個 cell 執行：!pip install stable-baselines3 gymnasium numpy
##############################################################

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import copy
import random
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
import os
import time

# ==================== 棋子定義 ====================
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

# ==================== 完整遊戲邏輯引擎 ====================
class GameEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[Piece.EMPTY for _ in range(4)] for _ in range(4)]
        self.turn = 'player1'
        self.state = 'INITIAL'
        self.score = {'player1': 0, 'player2': 0}
        self.special_captured = {'player1': 0, 'player2': 0}
        self.initial_pieces_placed = 0
        self.winner = None

    def get_valid_moves(self):
        moves = []
        for i in range(4):
            for j in range(4):
                if self.board[i][j] == Piece.EMPTY:
                    moves.append((i, j, 'front'))
                    moves.append((i, j, 'back'))
        return moves

    def make_move(self, x, y, face):
        if self.state not in ('INITIAL', 'PLAYING'):
            return False
        if x < 0 or x >= 4 or y < 0 or y >= 4:
            return False
        if self.board[x][y] != Piece.EMPTY:
            return False

        if self.state == 'INITIAL':
            piece = Piece.YELLOW_FRONT if face == 'front' else Piece.YELLOW_BACK
            self.board[x][y] = piece
            self.initial_pieces_placed += 1
            if self.initial_pieces_placed == 2:
                self.state = 'PLAYING'
                self.turn = 'player2'
            return True

        elif self.state == 'PLAYING':
            piece = Piece.BLUE_FRONT if face == 'front' else Piece.RED_BACK
            self.board[x][y] = piece
            self.flip_neighbors(x, y)
            lines = self.find_lines()
            for line in lines:
                self.clear_line(line)
            self.check_win()
            if self.state == 'PLAYING':
                self.turn = 'player2' if self.turn == 'player1' else 'player1'
            return True
        return False

    def flip_neighbors(self, x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 4 and 0 <= ny < 4:
                if self.board[nx][ny] != Piece.EMPTY:
                    self.board[nx][ny] = Piece.flip(self.board[nx][ny])

    def find_lines(self):
        lines = []
        for i in range(4):
            line = [(i, j) for j in range(4)]
            if self._is_valid_line(line):
                lines.append(line)
        for j in range(4):
            line = [(i, j) for i in range(4)]
            if self._is_valid_line(line):
                lines.append(line)
        diag1 = [(i, i) for i in range(4)]
        if self._is_valid_line(diag1):
            lines.append(diag1)
        diag2 = [(i, 3 - i) for i in range(4)]
        if self._is_valid_line(diag2):
            lines.append(diag2)
        return lines

    def _is_valid_line(self, coords):
        pieces = [self.board[x][y] for x, y in coords]
        if any(p == Piece.EMPTY for p in pieces):
            return False
        return all(Piece.is_front(p) for p in pieces) or all(Piece.is_back(p) for p in pieces)

    def clear_line(self, line):
        for x, y in line:
            p = self.board[x][y]
            if Piece.is_special(p):
                self.special_captured[self.turn] += 1
            self.board[x][y] = Piece.EMPTY
        self.score[self.turn] += 1

    def check_win(self):
        p1s = self.special_captured['player1']
        p2s = self.special_captured['player2']
        p1 = self.score['player1']
        p2 = self.score['player2']
        if p1s == 2:
            self.state = 'FINISHED'
            self.winner = 'player1'
        elif p2s == 2:
            self.state = 'FINISHED'
            self.winner = 'player2'
        elif p1s == 1 and p2s == 1:
            if p1 >= p2 + 2:
                self.state = 'FINISHED'
                self.winner = 'player1'
            elif p2 >= p1 + 2:
                self.state = 'FINISHED'
                self.winner = 'player2'

    def board_as_array(self):
        return np.array(self.board, dtype=np.float32)

    def is_over(self):
        return self.state == 'FINISHED'


# ==================== 觀察值轉換 ====================
def board_to_obs(board):
    """將 4x4 棋盤轉為 5 通道 one-hot"""
    obs = np.zeros((5, 4, 4), dtype=np.float32)
    for i in range(4):
        for j in range(4):
            p = board[i][j]
            if p == Piece.EMPTY:
                obs[0, i, j] = 1.0
            elif p == Piece.BLUE_FRONT:
                obs[1, i, j] = 1.0
            elif p == Piece.RED_BACK:
                obs[2, i, j] = 1.0
            elif p == Piece.YELLOW_FRONT:
                obs[3, i, j] = 1.0
            elif p == Piece.YELLOW_BACK:
                obs[4, i, j] = 1.0
    return obs

def action_to_move(action):
    pos = action // 2
    x = pos // 4
    y = pos % 4
    face = 'front' if action % 2 == 0 else 'back'
    return x, y, face


# ==================== 自我對弈環境 ====================
class SelfPlayEnv(gym.Env):
    """
    AI vs AI 自我對弈環境。
    - 學生模型 (正在訓練的) 扮演 player2
    - 對手模型 (已訓練好的舊版本) 扮演 player1
    - 對手會定期從檔案更新
    """
    metadata = {"render_modes": []}

    def __init__(self, opponent_model_path=None):
        super().__init__()
        self.action_space = spaces.Discrete(32)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(5, 4, 4), dtype=np.float32
        )
        self.game = GameEngine()
        self.max_steps = 40
        self.steps = 0

        # 載入對手模型
        self.opponent_model = None
        if opponent_model_path and os.path.exists(opponent_model_path):
            try:
                self.opponent_model = PPO.load(opponent_model_path)
                print(f"✅ 對手模型已載入: {opponent_model_path}")
            except Exception as e:
                print(f"⚠️ 對手模型載入失敗: {e}，使用隨機對手")

    def reload_opponent(self, path):
        """熱更新對手模型"""
        if os.path.exists(path):
            try:
                self.opponent_model = PPO.load(path)
            except:
                pass

    def _opponent_move(self):
        """對手 (player1) 下棋"""
        if self.game.is_over() or self.game.turn != 'player1':
            return

        valid = self.game.get_valid_moves()
        if not valid:
            return

        if self.opponent_model is not None:
            # 用模型預測
            obs = board_to_obs(self.game.board)
            action, _ = self.opponent_model.predict(obs, deterministic=False)
            x, y, face = action_to_move(int(action))

            # 如果模型選了不合法的位置，隨機選
            if self.game.board[x][y] != Piece.EMPTY:
                move = random.choice(valid)
                x, y, face = move
        else:
            # 隨機對手
            move = random.choice(valid)
            x, y, face = move

        self.game.make_move(x, y, face)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game.reset()
        self.steps = 0

        # 開局：player1 隨機放 2 顆黃棋
        empty = [(i, j) for i in range(4) for j in range(4)]
        random.shuffle(empty)
        for k in range(2):
            x, y = empty[k]
            face = random.choice(['front', 'back'])
            self.game.make_move(x, y, face)

        return board_to_obs(self.game.board), {}

    def step(self, action):
        self.steps += 1
        reward = 0.0
        terminated = False
        truncated = False

        x, y, face = action_to_move(action)

        # 記錄落子前狀態
        old_score = self.game.score['player2']
        old_special = self.game.special_captured['player2']
        old_opp_score = self.game.score['player1']
        old_opp_special = self.game.special_captured['player1']

        # ===== AI (player2) 下棋 =====
        if self.game.board[x][y] != Piece.EMPTY or self.game.state != 'PLAYING':
            # 不合法動作：懲罰，隨機補一步
            reward = -3.0
            valid = self.game.get_valid_moves()
            if valid:
                mv = random.choice(valid)
                self.game.make_move(mv[0], mv[1], mv[2])
            else:
                terminated = True
                return board_to_obs(self.game.board), reward, terminated, truncated, {}
        else:
            self.game.make_move(x, y, face)

        # --- 每多下一步的時間壓力 ---
        reward -= 0.5

        # --- AI 收線獎勵 ---
        new_score = self.game.score['player2']
        new_special = self.game.special_captured['player2']
        if new_score > old_score:
            reward += 5.0
        if new_special > old_special:
            reward += 8.0

        # 檢查是否結束
        if self.game.is_over():
            if self.game.winner == 'player2':
                # 贏得越快獎勵越高
                speed_bonus = max(0, (self.max_steps - self.steps)) * 0.5
                reward += 25.0 + speed_bonus
            else:
                reward -= 25.0
            terminated = True
            return board_to_obs(self.game.board), reward, terminated, truncated, {}

        # ===== 對手 (player1) 下棋 =====
        self._opponent_move()

        # 對手收線懲罰
        new_opp_score = self.game.score['player1']
        new_opp_special = self.game.special_captured['player1']
        if new_opp_score > old_opp_score:
            reward -= 3.0
        if new_opp_special > old_opp_special:
            reward -= 6.0

        if self.game.is_over():
            if self.game.winner == 'player2':
                speed_bonus = max(0, (self.max_steps - self.steps)) * 0.5
                reward += 25.0 + speed_bonus
            else:
                reward -= 25.0
            terminated = True
            return board_to_obs(self.game.board), reward, terminated, truncated, {}

        # 超時截斷
        if self.steps >= self.max_steps:
            truncated = True
            score_diff = self.game.score['player2'] - self.game.score['player1']
            reward += score_diff * 2.0

        return board_to_obs(self.game.board), reward, terminated, truncated, {}


# ==================== 勝率評估回呼 + 自動更新對手 ====================
class SelfPlayCallback(BaseCallback):
    """
    1. 定期評估勝率（跟隨機 + 跟對手模型各測一輪）
    2. 保存歷史最佳模型
    3. 每隔 update_opponent_freq 步，將當前最佳模型設為新的對手
    """
    def __init__(self, eval_freq=10000, n_eval_games=200,
                 best_model_path='./logs/best_model/',
                 update_opponent_freq=50000,
                 verbose=1):
        super().__init__(verbose)
        self.eval_freq = eval_freq
        self.n_eval_games = n_eval_games
        self.best_model_path = best_model_path
        self.update_opponent_freq = update_opponent_freq
        self.best_win_rate = 0.0
        self.history = []

    def _on_step(self):
        # --- 定期評估 ---
        if self.n_calls % self.eval_freq == 0:
            wr_random = self._evaluate(opponent='random')
            wr_self = self._evaluate(opponent='self')
            self.history.append((self.n_calls, wr_random, wr_self))

            if self.verbose:
                print(f"\n📊 [步數 {self.n_calls:>8,}] "
                      f"vs 隨機: {wr_random:.1%} | vs 舊模型: {wr_self:.1%} | "
                      f"歷史最佳 vs 隨機: {self.best_win_rate:.1%}")

            if wr_random > self.best_win_rate:
                self.best_win_rate = wr_random
                os.makedirs(self.best_model_path, exist_ok=True)
                path = os.path.join(self.best_model_path, 'best_model')
                self.model.save(path)
                if self.verbose:
                    print(f"🏆 新最佳！vs 隨機勝率 {wr_random:.1%}，已保存")

        # --- 定期更新對手 ---
        if self.n_calls % self.update_opponent_freq == 0:
            best_path = os.path.join(self.best_model_path, 'best_model.zip')
            if os.path.exists(best_path):
                env = self.training_env.envs[0]
                while hasattr(env, 'env'):
                    env = env.env
                env.reload_opponent(best_path)
                if self.verbose:
                    print(f"🔄 [步數 {self.n_calls:>8,}] 對手已更新為最新最佳模型")

        return True

    def _evaluate(self, opponent='random'):
        wins = 0
        if opponent == 'random':
            env = SelfPlayEnv(opponent_model_path=None)
        else:
            best_path = os.path.join(self.best_model_path, 'best_model.zip')
            env = SelfPlayEnv(opponent_model_path=best_path if os.path.exists(best_path) else None)

        for _ in range(self.n_eval_games):
            obs, _ = env.reset()
            done = False
            steps = 0
            while not done and steps < 50:
                action, _ = self.model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                steps += 1
            if env.game.winner == 'player2':
                wins += 1
        return wins / self.n_eval_games


# ==================== 主程式 ====================
if __name__ == "__main__":
    print("=" * 65)
    print("  4x4 翻轉棋 AI 自我對弈訓練系統 v2")
    print("  AI (player2) vs 舊版 AI (player1)")
    print("  每步 -0.5 時間壓力 | 快速結束額外獎勵")
    print("=" * 65)

    # ===== 設定：是否從已訓練的模型繼續訓練 =====
    PRETRAINED_PATH = "ppo_flipgame_final.zip"   # 改成您的模型路徑
    CONTINUE_TRAINING = os.path.exists(PRETRAINED_PATH)

    # 建立自我對弈環境（對手 = 已訓練好的模型）
    opponent_path = PRETRAINED_PATH if CONTINUE_TRAINING else None
    env = SelfPlayEnv(opponent_model_path=opponent_path)

    # 建立回呼
    callback = SelfPlayCallback(
        eval_freq=10000,
        n_eval_games=200,
        best_model_path='./logs/best_model/',
        update_opponent_freq=50000,   # 每 5 萬步把對手換成最新最佳
        verbose=1
    )

    # 建立或載入模型
    if CONTINUE_TRAINING:
        print(f"\n📦 從已訓練模型繼續: {PRETRAINED_PATH}")
        model = PPO.load(
            PRETRAINED_PATH,
            env=env,
            learning_rate=1e-4,        # 微調用較低學習率
            ent_coef=0.02,             # 稍高探索，避免困在局部最優
        )
    else:
        print("\n🆕 從零開始訓練")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=256,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.02,
            policy_kwargs=dict(
                net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128])
            )
        )

    # ===== 開始訓練 =====
    TOTAL_TIMESTEPS = 1_000_000

    print(f"\n🚀 開始訓練 {TOTAL_TIMESTEPS:,} 步")
    print(f"   每 {callback.eval_freq:,} 步評估 (vs 隨機 + vs 舊模型)")
    print(f"   每 {callback.update_opponent_freq:,} 步更新對手為最新最佳模型\n")

    start_time = time.time()
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=callback)
    elapsed = time.time() - start_time

    # 保存最終模型
    model.save("ppo_flipgame_final_v2")

    print("\n" + "=" * 65)
    print(f"✅ 訓練完成！耗時 {elapsed/60:.1f} 分鐘")
    print(f"   最終模型: ppo_flipgame_final_v2.zip")
    print(f"   最佳模型: ./logs/best_model/best_model.zip")
    print(f"   最佳 vs 隨機勝率: {callback.best_win_rate:.1%}")
    print("=" * 65)

    # 勝率變化表
    print("\n📈 勝率變化紀錄:")
    print(f"  {'步數':>10}  {'vs 隨機':>8}  {'vs 舊模型':>10}  圖表")
    print(f"  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*25}")
    for step, wr, ws in callback.history:
        bar_r = "█" * int(wr * 25)
        bar_s = "▓" * int(ws * 25)
        print(f"  {step:>10,}  {wr:>7.1%}  {ws:>9.1%}  {bar_r}")
